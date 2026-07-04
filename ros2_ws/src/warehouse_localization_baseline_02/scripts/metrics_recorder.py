#!/usr/bin/env python3
"""
metrics_recorder.py  (M3/M4)
AMCL 추정(/amcl_pose)과 진짜 위치(/ground_truth)를 비교해 per-timestep 지표를 CSV로 기록한다.
로컬라이제이션 방식(AMCL baseline / EKF / 반사판)에 무관하게 재사용 (지표 파이프라인 = M4).

기록 열: t, gt_x, gt_y, gt_yaw, est_x, est_y, est_yaw,
         pos_err(m), yaw_err(deg), cov_trace, cov_major(1sigma major, m), visible_beams
종료(Ctrl+C) 시 요약(ATE=RMS pos_err, 최대오차, 평균 공분산) 출력.

실행: ros2 run warehouse_localization_baseline_02 metrics_recorder.py \
        --ros-args -p out_csv:=<경로> -p rate:=10.0
"""
import math
import csv
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan


def yaw_from_q(q):
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


class MetricsRecorder(Node):
    def __init__(self):
        super().__init__('metrics_recorder')
        self.declare_parameter('out_csv', '/tmp/amcl_metrics.csv')
        self.declare_parameter('rate', 10.0)
        self.out_csv = self.get_parameter('out_csv').value
        rate = self.get_parameter('rate').value

        self.est = None       # (x,y,yaw, cov6x6)
        self.gt = None        # (x,y,yaw)
        self.beams = None
        self.rows = []
        self.t0 = None

        self.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', self.on_amcl, 10)
        self.create_subscription(Odometry, '/ground_truth', self.on_gt, 10)
        self.create_subscription(LaserScan, '/scan', self.on_scan, qos_profile_sensor_data)
        self.create_timer(1.0 / rate, self.sample)
        self.create_timer(3.0, self.progress)
        self.get_logger().info(f'metrics_recorder 시작 → {self.out_csv} ({rate}Hz). Ctrl+C 로 저장/요약.')

    def on_amcl(self, m):
        p = m.pose.pose
        self.est = (p.position.x, p.position.y, yaw_from_q(p.orientation),
                    np.array(m.pose.covariance).reshape(6, 6))

    def on_gt(self, m):
        p = m.pose.pose
        self.gt = (p.position.x, p.position.y, yaw_from_q(p.orientation))

    def on_scan(self, m):
        self.beams = int(sum(1 for v in m.ranges if math.isfinite(v) and v > 0))

    def sample(self):
        if self.est is None or self.gt is None:
            return
        now = self.get_clock().now().nanoseconds * 1e-9
        if self.t0 is None:
            self.t0 = now
        t = now - self.t0
        ex, ey, eyaw, cov = self.est
        gx, gy, gyaw = self.gt
        pos_err = math.hypot(ex - gx, ey - gy)
        yaw_err = math.degrees(abs(math.atan2(math.sin(eyaw - gyaw), math.cos(eyaw - gyaw))))
        xx, xy, yy = cov[0, 0], cov[0, 1], cov[1, 1]
        trace = xx + yy
        # 위치 공분산 타원 장축(1-sigma)
        term = math.sqrt(max(0.0, ((xx - yy) / 2.0) ** 2 + xy * xy))
        major = math.sqrt(max(0.0, (xx + yy) / 2.0 + term))
        self.rows.append([t, gx, gy, gyaw, ex, ey, eyaw, pos_err, yaw_err,
                          trace, major, self.beams if self.beams is not None else -1])

    def progress(self):
        if not self.rows:
            self.get_logger().info('대기 중 (/amcl_pose·/ground_truth 수신 전)')
            return
        last = self.rows[-1]
        self.get_logger().info(
            f'샘플 {len(self.rows)} | pos_err={last[7]:.2f}m | cov_major={last[10]:.2f}m | 가시빔={last[11]}')

    def save(self):
        if not self.rows:
            self.get_logger().warn('기록된 샘플 없음 — CSV 미저장')
            return
        header = ['t', 'gt_x', 'gt_y', 'gt_yaw', 'est_x', 'est_y', 'est_yaw',
                  'pos_err', 'yaw_err_deg', 'cov_trace', 'cov_major', 'visible_beams']
        with open(self.out_csv, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(self.rows)
        arr = np.array([r[7] for r in self.rows])
        ate = math.sqrt(float(np.mean(arr ** 2)))
        self.get_logger().info(
            f'저장: {self.out_csv} ({len(self.rows)}행) | ATE(RMS)={ate:.3f}m '
            f'| 최대오차={arr.max():.3f}m | 평균 cov_major={np.mean([r[10] for r in self.rows]):.3f}m')


def main():
    rclpy.init()
    node = MetricsRecorder()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.save()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
