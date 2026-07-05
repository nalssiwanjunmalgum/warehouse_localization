#!/usr/bin/env python3
"""
noise_injector.py  (M5 / ④ 노이즈 주입)

깨끗한 바퀴 오도메트리(/odom, diff_drive 플러그인)를 읽어 **현실적인 드리프트를 주입**한다.
시뮬 오도메트리는 거의 완벽(슬립 0)해서, 이걸 오염시켜야 추측항법이 실제로 어긋나고
그래야 EKF(오도+IMU)의 '완화' 효과와 랜드마크(M6)의 필요성이 성립한다.  (설계: docs/M5_EKF.md)

핵심: AMCL 모션모델은 /odom '토픽'이 아니라 odom→base_footprint 'TF'를 읽는다.
      따라서 노이즈는 TF 에 실려야 한다.
  - 구성 N (EKF 없음): 이 노드가 /odom_noisy + odom→base_footprint TF 를 둘 다 발행.
  - 구성 E (EKF):      이 노드는 /odom_noisy 토픽만 발행(publish_tf:=false), TF 는 EKF 가 발행.

노이즈 모델(설계 §2): 깨끗한 속도(v, ω)에 오차를 실어 재적분.
  v' = v·(1+k_v)          + N(0, σ_v·|v|)
  ω' = ω·(1+k_ω) + b_ω    + N(0, σ_ω·|ω| + σ_ω0)     (b_ω 는 이동 중에만 = 헤딩이 서서히 틀어지는 킬러)
  θ += ω'·dt ; x += v'·cosθ·dt ; y += v'·sinθ·dt

실행:
  ros2 run warehouse_localization_ekf_03 noise_injector.py --ros-args \
    -p publish_tf:=true -p seed:=0 -p b_w:=0.01
"""
import math
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped, Quaternion
from tf2_ros import TransformBroadcaster


def yaw_to_q(yaw):
    q = Quaternion()
    q.z = math.sin(yaw / 2.0)
    q.w = math.cos(yaw / 2.0)
    return q


class NoiseInjector(Node):
    def __init__(self):
        super().__init__('noise_injector')
        # --- 노이즈 파라미터 (재빌드 없이 튜닝 가능) ---
        self.declare_parameter('in_topic', '/odom')          # 깨끗한 바퀴 오도(diff_drive)
        self.declare_parameter('out_topic', '/odom_noisy')   # 오염된 오도(EKF/기록 입력)
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_footprint')
        self.declare_parameter('publish_tf', True)           # N: true, E(EKF): false
        self.declare_parameter('seed', 0)                    # 재현성(⑥)
        self.declare_parameter('k_v', 0.02)                  # 병진 스케일 바이어스
        self.declare_parameter('sigma_v', 0.02)              # 병진 랜덤(속도 비례)
        self.declare_parameter('k_w', 0.03)                  # 회전 스케일 바이어스
        self.declare_parameter('b_w', 0.01)                  # 회전 상수 바이어스(rad/s, 이동 중) ★킬러
        self.declare_parameter('sigma_w', 0.02)              # 회전 랜덤(속도 비례)
        self.declare_parameter('sigma_w0', 0.005)            # 회전 랜덤(상수항)

        g = self.get_parameter
        self.out_topic = g('out_topic').value
        self.odom_frame = g('odom_frame').value
        self.base_frame = g('base_frame').value
        self.publish_tf = bool(g('publish_tf').value)
        self.k_v = float(g('k_v').value); self.sigma_v = float(g('sigma_v').value)
        self.k_w = float(g('k_w').value); self.b_w = float(g('b_w').value)
        self.sigma_w = float(g('sigma_w').value); self.sigma_w0 = float(g('sigma_w0').value)
        self.rng = np.random.RandomState(int(g('seed').value))

        # 오염된 누적 포즈(odom 프레임, 시작=원점 → 깨끗한 오도와 동일 출발)
        self.x = 0.0; self.y = 0.0; self.th = 0.0
        self.last_stamp = None

        self.pub = self.create_publisher(Odometry, self.out_topic, 20)
        self.br = TransformBroadcaster(self) if self.publish_tf else None
        self.create_subscription(Odometry, g('in_topic').value, self.on_odom, 20)
        self.get_logger().info(
            f'noise_injector 시작: publish_tf={self.publish_tf} '
            f'k_v={self.k_v} k_w={self.k_w} b_w={self.b_w} σ_v={self.sigma_v} σ_w={self.sigma_w}')

    def on_odom(self, m):
        # 메시지 스탬프로 dt (sim time). 첫 콜백은 dt 확립만.
        stamp = m.header.stamp
        t = stamp.sec + stamp.nanosec * 1e-9
        if self.last_stamp is None:
            self.last_stamp = t
            return
        dt = t - self.last_stamp
        self.last_stamp = t
        if dt <= 0.0 or dt > 1.0:      # 시계 점프/역행 방어
            return

        v = m.twist.twist.linear.x     # 바디 전진속도(깨끗)
        w = m.twist.twist.angular.z    # 요레이트(깨끗)
        moving = (abs(v) > 1e-3) or (abs(w) > 1e-3)

        v_n = v * (1.0 + self.k_v) + self.rng.normal(0.0, self.sigma_v * abs(v))
        w_n = (w * (1.0 + self.k_w)
               + (self.b_w if moving else 0.0)
               + self.rng.normal(0.0, self.sigma_w * abs(w) + self.sigma_w0))

        # 적분(간단 오일러). θ 먼저 갱신 후 전진 → 헤딩 바이어스가 경로를 휘게 함.
        self.th = math.atan2(math.sin(self.th + w_n * dt), math.cos(self.th + w_n * dt))
        self.x += v_n * math.cos(self.th) * dt
        self.y += v_n * math.sin(self.th) * dt

        self.publish(stamp, v_n, w_n)

    def publish(self, stamp, v_n, w_n):
        o = Odometry()
        o.header.stamp = stamp
        o.header.frame_id = self.odom_frame
        o.child_frame_id = self.base_frame
        o.pose.pose.position.x = self.x
        o.pose.pose.position.y = self.y
        o.pose.pose.orientation = yaw_to_q(self.th)
        o.twist.twist.linear.x = v_n
        o.twist.twist.angular.z = w_n
        # 공분산: EKF 는 twist(vx, vyaw)를 융합 → twist 대각을 의미있게. pose 는 드리프트라 크게.
        pc = [0.0] * 36
        pc[0] = pc[7] = 0.2; pc[14] = 1e6; pc[21] = 1e6; pc[28] = 1e6; pc[35] = 0.3
        o.pose.covariance = pc
        tc = [0.0] * 36
        tc[0] = max(1e-4, (self.sigma_v * 0.5) ** 2 + 1e-3)   # vx var
        tc[7] = 1e6; tc[14] = 1e6; tc[21] = 1e6; tc[28] = 1e6
        tc[35] = max(1e-4, (self.sigma_w * 0.5) ** 2 + 1e-3)  # vyaw var
        o.twist.covariance = tc
        self.pub.publish(o)

        if self.br is not None:
            tf = TransformStamped()
            tf.header.stamp = stamp
            tf.header.frame_id = self.odom_frame
            tf.child_frame_id = self.base_frame
            tf.transform.translation.x = self.x
            tf.transform.translation.y = self.y
            tf.transform.rotation = yaw_to_q(self.th)
            self.br.sendTransform(tf)


def main():
    rclpy.init()
    node = NoiseInjector()
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
