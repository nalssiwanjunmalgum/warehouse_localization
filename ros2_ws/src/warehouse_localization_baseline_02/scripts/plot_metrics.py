#!/usr/bin/env python3
"""
plot_metrics.py  (M4)
metrics_recorder 가 만든 CSV 를 읽어 M3 baseline 시각화 플롯을 생성한다.
  1) 위치오차 vs 시간 (+ 가시 특징 수 겹쳐서)
  2) AMCL 공분산(장축) vs 시간
  3) 궤적 오버레이 (top-down): ground-truth vs AMCL 추정
요약(ATE, 최대오차, 평균 공분산)을 제목에 표기.

실행: python3 plot_metrics.py <metrics.csv> [out.png]
(matplotlib 필요. Agg 백엔드로 파일 저장 — GUI 불필요)
"""
import sys
import csv
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def load(path):
    with open(path) as f:
        r = csv.DictReader(f)
        cols = {k: [] for k in r.fieldnames}
        for row in r:
            for k, v in row.items():
                cols[k].append(float(v))
    return {k: np.array(v) for k, v in cols.items()}


def main():
    if len(sys.argv) < 2:
        print('usage: plot_metrics.py <metrics.csv> [out.png]')
        sys.exit(1)
    csv_path = sys.argv[1]
    out_png = sys.argv[2] if len(sys.argv) > 2 else csv_path.rsplit('.', 1)[0] + '.png'
    d = load(csv_path)

    t, pos_err = d['t'], d['pos_err']
    ate = math.sqrt(float(np.mean(pos_err ** 2)))
    maxe = float(pos_err.max())
    mean_major = float(np.mean(d['cov_major']))

    fig, ax = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle(f'M3 Baseline (AMCL) — ATE(RMS)={ate:.3f}m  max={maxe:.3f}m  '
                 f'mean cov_major={mean_major:.3f}m', fontsize=13)

    # 1) 위치오차 + 가시 특징 수
    ax0 = ax[0]
    ax0.plot(t, pos_err, color='tab:red', label='position error (m)')
    ax0.set_xlabel('t (s)'); ax0.set_ylabel('position error (m)', color='tab:red')
    ax0.tick_params(axis='y', labelcolor='tab:red')
    ax0.set_title('Position error vs time')
    axb = ax0.twinx()
    axb.plot(t, d['visible_beams'], color='tab:blue', alpha=0.4, label='visible beams')
    axb.set_ylabel('visible LiDAR beams', color='tab:blue')
    axb.tick_params(axis='y', labelcolor='tab:blue')

    # 2) 공분산 장축
    ax[1].plot(t, d['cov_major'], color='tab:purple')
    ax[1].set_xlabel('t (s)'); ax[1].set_ylabel('AMCL cov major axis (m, 1σ)')
    ax[1].set_title('Uncertainty (covariance) vs time')

    # 3) 궤적 오버레이
    ax[2].plot(d['gt_x'], d['gt_y'], color='tab:green', lw=2, label='ground truth')
    ax[2].plot(d['est_x'], d['est_y'], color='tab:red', lw=1.5, ls='--', label='AMCL est')
    ax[2].scatter([d['gt_x'][0]], [d['gt_y'][0]], c='k', marker='o', s=40, label='start')
    ax[2].set_aspect('equal'); ax[2].set_xlabel('x (m)'); ax[2].set_ylabel('y (m)')
    ax[2].set_title('Trajectory (top-down)'); ax[2].legend(); ax[2].grid(alpha=0.3)

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(out_png, dpi=120)
    print(f'저장: {out_png} | ATE={ate:.3f}m max={maxe:.3f}m mean_cov_major={mean_major:.3f}m')


if __name__ == '__main__':
    main()
