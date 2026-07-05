#!/usr/bin/env python3
"""
map_builder.py  (P2 맵 전략)
2D 라이다 스캔을 로봇의 '진짜 위치'(/ground_truth)에 누적해 점유 격자 지도(occupancy grid)를
생성한다. 추정 위치가 아닌 ground-truth 를 쓰므로 드리프트가 없는 정확한 기준 지도가 나온다.
(개활지에서 SLAM이 뒤틀리는 문제를 회피 — 시뮬레이션의 ground-truth 강점 활용)

원리(빔 단위 ray-casting):
  - 각 빔: 로봇→끝점 사이 셀 = free(관측된 빈 공간), 끝점 셀(유효 반사) = occupied
  - 무반사(inf) 빔: max range 까지 free
  - 여러 스캔 누적 후, hit/(hit+miss) 로 점유 판정

실행:
  ros2 run warehouse_localization_sim_01 map_builder.py --ros-args -p out_dir:=<경로>
  (로봇을 특징 근처로 주행시키며 누적 → Ctrl+C 시 pgm+yaml 저장)
"""
import os
import math
import signal
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry

RES = 0.05                 # m/cell
XMIN, YMIN, XMAX, YMAX = -32.0, -32.0, 32.0, 32.0
OCC_THRESH = 0.25          # hit 비율 이상이면 occupied


def yaw_from_q(q):
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


class MapBuilder(Node):
    def __init__(self):
        super().__init__('map_builder')
        self.declare_parameter('out_dir', os.path.expanduser('~/ros2_ws'))
        self.declare_parameter('name', 'warehouse_map')
        self.out_dir = self.get_parameter('out_dir').value
        self.name = self.get_parameter('name').value

        self.W = int(round((XMAX - XMIN) / RES))
        self.H = int(round((YMAX - YMIN) / RES))
        self.hit = np.zeros((self.H, self.W), dtype=np.uint32)
        self.miss = np.zeros((self.H, self.W), dtype=np.uint32)
        self.pose = None
        self.n_scans = 0

        self.create_subscription(Odometry, '/ground_truth', self.on_gt, 10)
        self.create_subscription(LaserScan, '/scan', self.on_scan, qos_profile_sensor_data)
        self.create_timer(3.0, self.progress)
        self.get_logger().info(
            f'map_builder 시작: 격자 {self.W}x{self.H} @ {RES}m. 로봇을 주행시키며 누적. Ctrl+C 로 저장.')

    def on_gt(self, m):
        p = m.pose.pose.position
        self.pose = (p.x, p.y, yaw_from_q(m.pose.pose.orientation))

    def on_scan(self, msg):
        if self.pose is None:
            return
        rx, ry, ryaw = self.pose
        n = len(msg.ranges)
        if n == 0:
            return
        ranges = np.asarray(msg.ranges, dtype=np.float64)
        rmax = msg.range_max
        angles = ryaw + msg.angle_min + np.arange(n) * msg.angle_increment
        finite = np.isfinite(ranges) & (ranges > msg.range_min) & (ranges < rmax)
        end_r = np.where(finite, ranges, rmax)      # free ray 끝 거리

        # free 공간: 각 빔을 따라 샘플(끝점 제외) → miss
        S = int(rmax / RES) + 1
        fracs = np.linspace(0.0, 1.0, S, endpoint=False)          # (S,)
        rr = end_r[:, None] * fracs[None, :]                      # (N,S)
        xs = rx + rr * np.cos(angles)[:, None]
        ys = ry + rr * np.sin(angles)[:, None]
        ci = ((xs - XMIN) / RES).astype(np.int32).ravel()
        cj = ((ys - YMIN) / RES).astype(np.int32).ravel()
        v = (ci >= 0) & (ci < self.W) & (cj >= 0) & (cj < self.H)
        np.add.at(self.miss, (cj[v], ci[v]), 1)

        # occupied: 유효 반사 빔의 끝점 셀 → hit
        if finite.any():
            hx = rx + ranges[finite] * np.cos(angles[finite])
            hy = ry + ranges[finite] * np.sin(angles[finite])
            hi = ((hx - XMIN) / RES).astype(np.int32)
            hj = ((hy - YMIN) / RES).astype(np.int32)
            hv = (hi >= 0) & (hi < self.W) & (hj >= 0) & (hj < self.H)
            np.add.at(self.hit, (hj[hv], hi[hv]), 1)

        self.n_scans += 1

    def progress(self):
        observed = int(((self.hit + self.miss) > 0).sum())
        occ = int((self.hit > 0).sum())
        self.get_logger().info(f'누적 스캔 {self.n_scans} | 관측 셀 {observed} | occupied 후보 {occ}')

    def save(self):
        total = self.hit + self.miss
        observed = total > 0
        with np.errstate(divide='ignore', invalid='ignore'):
            ratio = np.where(observed, self.hit / np.maximum(total, 1), 0.0)
        img = np.full((self.H, self.W), 128, dtype=np.uint8)      # unknown=중간회색
        img[observed & (ratio < OCC_THRESH)] = 254                # free=흰색
        img[observed & (ratio >= OCC_THRESH)] = 0                 # occupied=검정
        img = np.flipud(img)                                      # pgm: 위=+y

        os.makedirs(self.out_dir, exist_ok=True)
        pgm = os.path.join(self.out_dir, self.name + '.pgm')
        yaml = os.path.join(self.out_dir, self.name + '.yaml')
        with open(pgm, 'wb') as f:
            f.write(bytearray(f'P5\n{self.W} {self.H}\n255\n', 'ascii'))
            f.write(img.tobytes())
        with open(yaml, 'w') as f:
            f.write(f'image: {self.name}.pgm\n')
            f.write(f'mode: trinary\nresolution: {RES}\n')
            f.write(f'origin: [{XMIN}, {YMIN}, 0.0]\n')
            f.write('negate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.25\n')
        occ = int((img == 0).sum())
        self.get_logger().info(f'저장 완료: {pgm} ({self.W}x{self.H}, occupied 셀 {occ}), {yaml}')


def main():
    rclpy.init()
    node = MapBuilder()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.save()                       # Ctrl+C 시에도 지도 저장 보장
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
