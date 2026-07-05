#!/usr/bin/env python3
"""
landmark_localizer.py  (M6.2 + M6.3)
반사판(가는 폴)을 CPU LiDAR 로 기하 검출하고, 알려진 좌표(landmarks.yaml)에 성좌매칭 후
삼각측량(2D Procrustes)으로 **절대 pose 를 확정**, map→odom 을 보정한다.
개활지 perceptual aliasing 을 제거하는 '해결' 단계. (설계: docs/P3_SENSOR_LANDMARK.md)

파이프라인(설계 §5):
  /scan ─▶ [검출] 연속 리턴 클러스터 → 지름(각폭×거리) 필터 → 반사판 후보 (base 좌표)
        ─▶ [식별] 현재 추정 pose 로 후보를 map 으로 투영 → landmarks NN 매칭(게이팅)
        ─▶ [보정] ≥3 매칭 → Procrustes 로 절대 pose(x,y,θ), 잔차 검증 → map→odom 갱신
  보정 사이 구간은 EKF(odom→base) 추측항법으로 pose 를 이어감(map→odom 유지).

출력: /landmark_pose (PoseWithCovarianceStamped, est) + TF map→odom.
지표 기록기는 est_topic:=/landmark_pose 로 이 pose 를 GT 와 비교.

실행:
  ros2 run warehouse_localization_landmark_04 landmark_localizer.py --ros-args \
    -p landmarks_yaml:=<경로> -p init_x:=-24 -p init_y:=-24 -p init_yaw:=1.571
"""
import math
import numpy as np
import yaml
import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import PoseWithCovarianceStamped, TransformStamped, Quaternion
from tf2_ros import Buffer, TransformListener, TransformBroadcaster
from tf2_ros import LookupException, ExtrapolationException, ConnectivityException


def yaw_to_q(yaw):
    q = Quaternion(); q.z = math.sin(yaw / 2.0); q.w = math.cos(yaw / 2.0); return q


def wrap(a):
    return math.atan2(math.sin(a), math.cos(a))


class LandmarkLocalizer(Node):
    def __init__(self):
        super().__init__('landmark_localizer')
        p = self.declare_parameter
        p('landmarks_yaml', '')
        p('scan_topic', '/scan')
        p('out_topic', '/landmark_pose')
        p('odom_frame', 'odom')
        p('base_frame', 'base_footprint')
        p('map_frame', 'map')
        p('init_x', 0.0); p('init_y', 0.0); p('init_yaw', 0.0)
        p('gate', 2.0)              # 연관 게이트(m): 후보-랜드마크 최대 거리
        p('min_fix', 3)            # 절대보정 최소 매칭 수
        p('max_diam', 0.30)        # 반사판 최대 지름(m): 기둥(0.4)·랙 배제
        p('gap', 0.3)              # 클러스터 분리 임계(인접 빔 거리차, m)
        p('max_residual', 0.40)    # Procrustes 잔차 RMS 허용(m): 오연관 거부
        p('reflector_radius', 0.08)

        g = self.get_parameter
        ly = g('landmarks_yaml').value
        with open(ly) as f:
            db = yaml.safe_load(f)
        self.MAP = np.array([[l['x'], l['y']] for l in db['landmarks']], dtype=float)
        self.get_logger().info(f'랜드마크 {len(self.MAP)}개 로드: {ly}')

        self.scan_topic = g('scan_topic').value
        self.odom_frame = g('odom_frame').value
        self.base_frame = g('base_frame').value
        self.map_frame = g('map_frame').value
        self.gate = float(g('gate').value)
        self.min_fix = int(g('min_fix').value)
        self.max_diam = float(g('max_diam').value)
        self.gap = float(g('gap').value)
        self.max_res = float(g('max_residual').value)
        self.rr = float(g('reflector_radius').value)

        # 추정 pose (map→base). 시작은 알려진 초기 pose 에서 부트스트랩.
        self.x = float(g('init_x').value); self.y = float(g('init_y').value)
        self.th = float(g('init_yaw').value)
        # map→odom (유지용). 초기엔 항등에 가깝게 두되, 첫 TF 수신 시 정합.
        self.mo = None            # (x,y,th) of map->odom, None 이면 미확립
        self.since_fix = 0.0      # 마지막 절대보정 이후 경과(s) — cov 로 표현
        self.last_stamp = None
        self.n_fix = 0; self.n_cycle = 0

        self.tfbuf = Buffer(); self.tfl = TransformListener(self.tfbuf, self)
        self.br = TransformBroadcaster(self)
        self.pub = self.create_publisher(PoseWithCovarianceStamped, g('out_topic').value, 10)
        self.create_subscription(LaserScan, self.scan_topic, self.on_scan, qos_profile_sensor_data)
        self.create_timer(3.0, self.progress)

    # ---- odom→base 조회 (EKF 발행) ----
    def lookup_odom_base(self, stamp):
        try:
            t = self.tfbuf.lookup_transform(self.odom_frame, self.base_frame, stamp,
                                            timeout=rclpy.duration.Duration(seconds=0.05))
        except (LookupException, ExtrapolationException, ConnectivityException):
            try:
                t = self.tfbuf.lookup_transform(self.odom_frame, self.base_frame,
                                                rclpy.time.Time())  # 최신
            except (LookupException, ExtrapolationException, ConnectivityException):
                return None
        q = t.transform.rotation
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
        return (t.transform.translation.x, t.transform.translation.y, yaw)

    @staticmethod
    def compose(a, b):  # T_a ∘ T_b  (each = x,y,th)
        ax, ay, ath = a; bx, by, bth = b
        c, s = math.cos(ath), math.sin(ath)
        return (ax + c * bx - s * by, ay + s * bx + c * by, wrap(ath + bth))

    @staticmethod
    def inv(a):
        ax, ay, ath = a; c, s = math.cos(ath), math.sin(ath)
        return (-(c * ax + s * ay), -(-s * ax + c * ay), -ath)

    # ---- 검출: /scan → 반사판 후보 (base 좌표 리스트) ----
    def detect(self, m):
        rng = m.ranges; n = len(rng); amin = m.angle_min; inc = m.angle_increment
        rmax = min(m.range_max, 11.9)
        cand = []
        i = 0
        while i < n:
            if not (math.isfinite(rng[i]) and m.range_min < rng[i] < rmax):
                i += 1; continue
            j = i
            while j + 1 < n and math.isfinite(rng[j + 1]) and m.range_min < rng[j + 1] < rmax \
                    and abs(rng[j + 1] - rng[j]) < self.gap:
                j += 1
            # 클러스터 [i..j]
            beams = list(range(i, j + 1))
            rs = [rng[k] for k in beams]
            rmean = float(np.mean(rs)); rmin = float(np.min(rs))
            width_rad = (len(beams)) * inc
            diam = 2.0 * rmean * math.sin(width_rad / 2.0)
            if diam <= self.max_diam:               # 얇음 = 반사판(기둥·랙·벽 배제)
                cbeam = (i + j) / 2.0
                bearing = amin + cbeam * inc
                r = rmin + self.rr                   # 근접면 → 폴 중심 보정
                cand.append((r * math.cos(bearing), r * math.sin(bearing)))
            i = j + 1
        return cand

    # ---- 식별 + 삼각측량 ----
    def solve(self, cand, prior):
        # prior = (x,y,th) map→base 예측. 후보를 map 으로 투영 → NN 매칭.
        px, py, pth = prior; c, s = math.cos(pth), math.sin(pth)
        src = []; dst = []; used = set()
        for (bx, by) in cand:
            mx = px + c * bx - s * by; my = py + s * bx + c * by
            d = np.hypot(self.MAP[:, 0] - mx, self.MAP[:, 1] - my)
            k = int(np.argmin(d))
            if d[k] <= self.gate and k not in used:
                used.add(k); src.append((bx, by)); dst.append(self.MAP[k])
        if len(src) < self.min_fix:
            return None
        src = np.array(src); dst = np.array(dst)
        mu_s = src.mean(0); mu_d = dst.mean(0)
        sp = src - mu_s; dp = dst - mu_d
        a = float((sp[:, 0] * dp[:, 0] + sp[:, 1] * dp[:, 1]).sum())
        b = float((sp[:, 0] * dp[:, 1] - sp[:, 1] * dp[:, 0]).sum())
        if abs(a) < 1e-9 and abs(b) < 1e-9:
            return None
        th = math.atan2(b, a)
        c2, s2 = math.cos(th), math.sin(th)
        tx = mu_d[0] - (c2 * mu_s[0] - s2 * mu_s[1])
        ty = mu_d[1] - (s2 * mu_s[0] + c2 * mu_s[1])
        # 잔차
        pred = np.column_stack([c2 * src[:, 0] - s2 * src[:, 1] + tx,
                                s2 * src[:, 0] + c2 * src[:, 1] + ty])
        res = float(np.sqrt(np.mean(np.sum((pred - dst) ** 2, axis=1))))
        return (tx, ty, wrap(th), res, len(src))

    def on_scan(self, m):
        self.n_cycle += 1
        stamp = m.header.stamp
        t = stamp.sec + stamp.nanosec * 1e-9
        dt = 0.0 if self.last_stamp is None else max(0.0, t - self.last_stamp)
        self.last_stamp = t
        self.since_fix += dt

        ob = self.lookup_odom_base(stamp)
        if ob is None:
            return  # EKF TF 아직 → 대기
        if self.mo is None:
            # map→odom = map_base(init) ∘ (odom_base)^-1
            self.mo = self.compose((self.x, self.y, self.th), self.inv(ob))

        # 예측 pose(prior) = map_odom(held) ∘ odom_base(now)
        prior = self.compose(self.mo, ob)

        cand = self.detect(m)
        fixed = False
        sol = self.solve(cand, prior) if len(cand) >= self.min_fix else None
        if sol is not None:
            tx, ty, th, res, nmatch = sol
            if res <= self.max_res:
                self.x, self.y, self.th = tx, ty, th
                self.mo = self.compose((tx, ty, th), self.inv(ob))  # 절대보정 → map→odom 갱신
                self.since_fix = 0.0; self.n_fix += 1; fixed = True
        if not fixed:
            # 보정 실패 → 추측항법(held map→odom)로 pose 이어감
            self.x, self.y, self.th = prior

        self.publish(stamp)

    def publish(self, stamp):
        # map→odom TF
        mx, my, mth = self.mo
        tf = TransformStamped()
        tf.header.stamp = stamp; tf.header.frame_id = self.map_frame
        tf.child_frame_id = self.odom_frame
        tf.transform.translation.x = mx; tf.transform.translation.y = my
        tf.transform.rotation = yaw_to_q(mth)
        self.br.sendTransform(tf)
        # /landmark_pose (est = map→base)
        pc = PoseWithCovarianceStamped()
        pc.header.stamp = stamp; pc.header.frame_id = self.map_frame
        pc.pose.pose.position.x = self.x; pc.pose.pose.position.y = self.y
        pc.pose.pose.orientation = yaw_to_q(self.th)
        # 확신도: 최근 보정이면 작게(~5cm), 보정 없이 오래면 커짐(추측항법 불확실성).
        # 상한(15m)으로 비현실적 폭주 방지 — baseline 최대 공분산(~25m)과 비교 가능한 스케일.
        sigma = min(0.05 + 0.3 * self.since_fix, 15.0)
        var = sigma * sigma
        cov = [0.0] * 36
        cov[0] = var; cov[7] = var
        cov[35] = min(0.02 + 0.05 * self.since_fix, 1.0) ** 2
        pc.pose.covariance = cov
        self.pub.publish(pc)

    def progress(self):
        if self.n_cycle == 0:
            self.get_logger().info('대기 중 (/scan·odom TF 수신 전)')
            return
        self.get_logger().info(
            f'pose=({self.x:.2f},{self.y:.2f},{math.degrees(self.th):.0f}°) '
            f'fix={self.n_fix}/{self.n_cycle} since_fix={self.since_fix:.1f}s')


def main():
    rclpy.init()
    node = LandmarkLocalizer()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
