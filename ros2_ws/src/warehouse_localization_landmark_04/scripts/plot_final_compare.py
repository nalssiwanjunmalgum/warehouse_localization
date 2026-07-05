#!/usr/bin/env python3
"""
plot_final_compare.py  (M7 종합 비교)
3단계(+노이즈 대조) 비교: Baseline(AMCL) / N(노이즈) / E(노이즈+EKF) / Landmark(반사판).
개활 창고 localization 이 단계별로 어떻게 개선되는지 한 장으로.

입력: outputs/baseline/Cx_baseline.*  outputs/ekf/Cx_{noise,ekf}.*  outputs/landmark/Cx_landmark.*
출력: outputs/landmark/final_compare_bars.png   (ATE 로그축 + cov_major)
      outputs/landmark/final_compare_curves.png (시점별 위치오차)

사용: python3 plot_final_compare.py <baseline_dir> <ekf_dir> <landmark_dir>
"""
import os
import sys
import json
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SCENS = ['C1', 'C2', 'C3', 'C4', 'C5']
CFG = [  # key, label, color, dir_key, suffix
    ('baseline', 'Baseline (AMCL)', '#888888'),
    ('noise', 'N: noise only', '#d62728'),
    ('ekf', 'E: noise+EKF', '#2ca02c'),
    ('landmark', 'Landmark (M6)', '#1f77b4'),
]


def load_sum(path):
    return json.load(open(path)) if os.path.exists(path) else None


def load_csv(path):
    if not os.path.exists(path):
        return None, None
    t, e = [], []
    with open(path) as f:
        for row in csv.DictReader(f):
            try:
                t.append(float(row['t'])); e.append(float(row['pos_err']))
            except (ValueError, KeyError):
                pass
    return (np.array(t), np.array(e)) if t else (None, None)


def path_for(key, base, ekf, lm, s, ext):
    if key == 'baseline':
        return os.path.join(base, f'{s}_baseline.{ext}')
    if key in ('noise', 'ekf'):
        return os.path.join(ekf, f'{s}_{key}.{ext}')
    return os.path.join(lm, f'{s}_landmark.{ext}')


def bars(base, ekf, lm, out):
    ate = {k: [] for k, _, _ in CFG}
    cov = {k: [] for k, _, _ in CFG}
    for s in SCENS:
        for k, _, _ in CFG:
            d = load_sum(path_for(k, base, ekf, lm, s, 'summary.json'))
            ate[k].append(d['ATE_rms_m'] if d else np.nan)
            cov[k].append(d['mean_cov_major_m'] if d else np.nan)
    x = np.arange(len(SCENS)); w = 0.2
    fig, axs = plt.subplots(2, 1, figsize=(12, 8.5))
    for i, (k, lab, col) in enumerate(CFG):
        axs[0].bar(x + (i - 1.5) * w, ate[k], w, label=lab, color=col)
        axs[1].bar(x + (i - 1.5) * w, cov[k], w, label=lab, color=col)
    axs[0].set_yscale('log')
    axs[0].set_ylabel('ATE (RMS, m) - log scale')
    axs[0].set_title('Absolute Trajectory Error - Landmark: tens of m -> ~0.2m (solved)')
    axs[1].set_ylabel('mean cov_major (m)')
    axs[1].set_title('Estimate confidence (covariance) - Landmark stays low via reflector fixes')
    for ax in axs:
        ax.set_xticks(x); ax.set_xticklabels(SCENS)
        ax.grid(axis='y', alpha=0.3); ax.legend(fontsize=8, ncol=4)
    fig.suptitle('M7: warehouse localization, 3 stages (Baseline -> +EKF -> +Landmark)', fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(out, dpi=110); plt.close(fig)
    print(f'saved {out}')


def curves(base, ekf, lm, out):
    fig, axs = plt.subplots(1, len(SCENS), figsize=(19, 3.8), sharey=True)
    show = [('baseline', 'Baseline', '#888888'), ('ekf', '+EKF', '#2ca02c'),
            ('landmark', 'Landmark', '#1f77b4')]
    for ax, s in zip(axs, SCENS):
        for k, lab, col in show:
            t, e = load_csv(path_for(k, base, ekf, lm, s, 'csv'))
            if t is not None:
                ax.plot(t, e, color=col, lw=1.2, label=lab)
        ax.set_title(s); ax.set_xlabel('t (s)'); ax.grid(alpha=0.3)
        ax.set_yscale('symlog', linthresh=1.0)
    axs[0].set_ylabel('position error (m, symlog)')
    axs[0].legend(fontsize=8, loc='center right')
    fig.suptitle('M7: position error vs time - Landmark(blue) flat ~0.2m, Baseline/EKF blow up to tens of m', fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(out, dpi=110); plt.close(fig)
    print(f'saved {out}')


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else '/home/ubuntu/ros2_ws/outputs/baseline'
    ekf = sys.argv[2] if len(sys.argv) > 2 else '/home/ubuntu/ros2_ws/outputs/ekf'
    lm = sys.argv[3] if len(sys.argv) > 3 else '/home/ubuntu/ros2_ws/outputs/landmark'
    bars(base, ekf, lm, os.path.join(lm, 'final_compare_bars.png'))
    curves(base, ekf, lm, os.path.join(lm, 'final_compare_curves.png'))


if __name__ == '__main__':
    main()
