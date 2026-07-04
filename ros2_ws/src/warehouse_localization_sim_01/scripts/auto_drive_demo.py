#!/usr/bin/env python3
"""
auto_drive_demo.py  (M2)
개활 창고에서 로봇을 '중앙 개활지 <-> 특징(랙/기둥) 근처'로 자동 순회시키는 데모 노드.
RViz 로 /scan(빨간 점)을 보면, 중앙에선 스캔이 비고 특징 근처에선 다시 찍히는 걸 반복 관찰할 수 있다.

안정성 설계 (지난 실패 교훈):
  1) 부드러운 비례 제어 (bang-bang X) → 제자리 회전/진동 방지
  2) LiDAR 전방 안전 감지 → 오도메트리가 틀어져도 벽에 충돌하지 않음
  3) 도달 판정 후 잠깐 정지 → 스캔 상태를 눈으로 확인할 여유

주의: 이 waffle의 diff_drive는 odom을 스폰 world 좌표에서 시작해 적산한다(기본 ENCODER).
즉 odom.position ≈ world 좌표(초기 -24,-24)이므로, 웨이포인트를 world 좌표 그대로 목표로 쓴다.
실행:  ros2 run warehouse_localization_sim_01 auto_drive_demo.py
종료:  Ctrl+C (로봇 정지 후 종료)
"""
import math
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist

# odom ≈ world 이므로 웨이포인트는 world 좌표 그대로 사용.
# 기둥(±20 격자)을 직선으로 관통하지 않도록 경로 설계. 스폰=(-24,-24).
WORLD_WAYPOINTS = [
    (-10.0, -24.0),  # 남쪽 통로로 동진(기둥 열 y=-20에서 4m 남쪽) — 스폰 옆 기둥 회피
    (0.0, 0.0),      # featureless core: 스캔 비어야 함
    (12.0, 0.0),     # 동쪽 랙(16,0)/기둥(20,0) 근처: 스캔 다시 찍힘
    (0.0, 0.0),      # 다시 중앙
]

V_MAX = 0.6           # 최대 전진속도 (m/s)
W_MAX = 1.0           # 최대 회전속도 (rad/s)
REACH_DIST = 1.5      # 웨이포인트 도달 판정 거리
SAFE_FRONT = 0.9      # 전방 이보다 가까우면 안전 회피 (기둥 지름 0.4m라 여유 충분)


def yaw_from_q(q):
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


class AutoDrive(Node):
    def __init__(self):
        super().__init__('auto_drive_demo')
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.create_subscription(Odometry, '/odom', self.on_odom, 10)
        self.create_subscription(LaserScan, '/scan', self.on_scan, qos_profile_sensor_data)
        self.pose = None
        self.front_min = math.inf
        self.beams = 0
        self.wp = 0
        self.pause_ticks = 0
        # odom ≈ world → 웨이포인트를 그대로 목표로 사용
        self.targets = list(WORLD_WAYPOINTS)
        self.create_timer(0.1, self.loop)
        self.create_timer(2.0, self.report)
        self.get_logger().info('auto_drive_demo 시작 — 중앙<->특징 순회. Ctrl+C 로 종료.')

    def on_odom(self, m):
        p = m.pose.pose.position
        self.pose = (p.x, p.y, yaw_from_q(m.pose.pose.orientation))

    def on_scan(self, m):
        n = len(m.ranges)
        if n == 0 or m.angle_increment == 0:
            return
        self.beams = sum(1 for v in m.ranges if math.isfinite(v) and v > 0)
        # 전방 ±25° 섹터 최근접 거리 (스캔 0번=정면)
        half = max(1, int((25.0 * math.pi / 180.0) / m.angle_increment))
        idxs = list(range(0, half)) + list(range(n - half, n))
        fr = [m.ranges[i] for i in idxs if math.isfinite(m.ranges[i]) and m.ranges[i] > 0]
        self.front_min = min(fr) if fr else math.inf

    def report(self):
        if self.pose is None:
            return
        wx, wy = self.pose[0], self.pose[1]   # odom ≈ world
        tgt = WORLD_WAYPOINTS[self.wp]
        state = '중앙(스캔 비어야 정상)' if tgt == (0.0, 0.0) else '특징 근처(스캔 찍힘)'
        self.get_logger().info(
            f'world=({wx:+5.1f},{wy:+5.1f}) 목표={tgt}{state} | 스캔 유효빔={self.beams} | 전방={self.front_min:.1f}m')

    def loop(self):
        if self.pose is None:
            return
        cmd = Twist()

        # 도달 후 잠깐 정지 (스캔 관찰용, 약 2초)
        if self.pause_ticks > 0:
            self.pause_ticks -= 1
            self.pub.publish(cmd)
            return

        tx, ty = self.targets[self.wp]
        x, y, yaw = self.pose
        dx, dy = tx - x, ty - y
        dist = math.hypot(dx, dy)
        desired = math.atan2(dy, dx)
        err = math.atan2(math.sin(desired - yaw), math.cos(desired - yaw))

        # 안전: 전방 장애물 → 목표 방향쪽으로 돌아 회피 (제자리 맴돌기 방지, 오도메트리 무관)
        if self.front_min < SAFE_FRONT:
            cmd.angular.z = 0.7 if err >= 0 else -0.7
            self.pub.publish(cmd)
            return

        if dist < REACH_DIST:
            self.wp = (self.wp + 1) % len(self.targets)   # 다음 웨이포인트 (순환)
            self.pause_ticks = 20                          # ~2초 정지
            self.pub.publish(Twist())
            return

        cmd.angular.z = clamp(1.2 * err, -W_MAX, W_MAX)     # 부드러운 비례 회전
        cmd.linear.x = V_MAX * max(0.0, math.cos(err))      # 정렬됐을 때만 전진
        self.pub.publish(cmd)


def main():
    rclpy.init()
    node = AutoDrive()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.pub.publish(Twist())   # 정지
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
