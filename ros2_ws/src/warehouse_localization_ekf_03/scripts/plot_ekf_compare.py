#!/usr/bin/env python3
"""
plot_ekf_compare.py  (M5)
3단계(=현재까지 2단계) 비교 시각화: baseline(무노이즈) vs N(노이즈만) vs E(노이즈+EKF).
같은 시나리오(C1~C5)에서 EKF 가 드리프트를 얼마나 완화하는지 한눈에.

입력: baseline 요약 = <BASE_DIR>/Cx_baseline.summary.json
      N/E 요약     = <EKF_DIR>/Cx_noise.summary.json, Cx_ekf.summary.json
      per-step CSV = 같은 폴더의 *.csv (곡선용)

출력:
  <EKF_DIR>/ekf_compare_bars.png   — 시나리오별 ATE·drift_rate 그룹 막대(baseline/N/E)
  <EKF_DIR>/ekf_compare_curves.png — 시나리오별 pos_err(t) 곡선(N 빨강 vs E 초록)

사용: python3 plot_ekf_compare.py <BASE_DIR> <EKF_DIR>
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
COL = {'baseline': '#888888', 'noise': '#d62728', 'ekf': '#2ca02c'}
LAB = {'baseline': 'Baseline (no noise)', 'noise': 'N: noise only', 'ekf': 'E: noise+EKF'}


def load_summary(path):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


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


def bars(base_dir, ekf_dir, out):
    # 각 시나리오별 ATE, drift_rate 수집
    ate = {k: [] for k in ('baseline', 'noise', 'ekf')}
    drift = {k: [] for k in ('baseline', 'noise', 'ekf')}
    paths = {
        'baseline': lambda s: os.path.join(base_dir, f'{s}_baseline.summary.json'),
        'noise': lambda s: os.path.join(ekf_dir, f'{s}_noise.summary.json'),
        'ekf': lambda s: os.path.join(ekf_dir, f'{s}_ekf.summary.json'),
    }
    for s in SCENS:
        for k in ('baseline', 'noise', 'ekf'):
            d = load_summary(paths[k](s))
            ate[k].append(d['ATE_rms_m'] if d else np.nan)
            drift[k].append(d['drift_rate_m_per_s'] if d else np.nan)

    x = np.arange(len(SCENS)); w = 0.26
    fig, axs = plt.subplots(2, 1, figsize=(11, 8))
    for ax, data, ylab, title in (
        (axs[0], ate, 'ATE (RMS, m)', 'ATE per scenario (lower = better)'),
        (axs[1], drift, 'drift_rate (m/s)', 'Drift rate per scenario'),
    ):
        for i, k in enumerate(('baseline', 'noise', 'ekf')):
            ax.bar(x + (i - 1) * w, data[k], w, label=LAB[k], color=COL[k])
        ax.set_xticks(x); ax.set_xticklabels(SCENS)
        ax.set_ylabel(ylab); ax.set_title(title)
        ax.grid(axis='y', alpha=0.3); ax.legend(fontsize=8)
    fig.suptitle('M5: EKF mitigation (Baseline vs Noise-only vs Noise+EKF)', fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(out, dpi=110); plt.close(fig)
    print(f'saved {out}')


def curves(ekf_dir, out):
    fig, axs = plt.subplots(1, len(SCENS), figsize=(19, 3.6), sharey=True)
    for ax, s in zip(axs, SCENS):
        tn, en = load_csv(os.path.join(ekf_dir, f'{s}_noise.csv'))
        te, ee = load_csv(os.path.join(ekf_dir, f'{s}_ekf.csv'))
        if tn is not None:
            ax.plot(tn, en, color=COL['noise'], lw=1.3, label='N: noise only')
        if te is not None:
            ax.plot(te, ee, color=COL['ekf'], lw=1.3, label='E: +EKF')
        ax.set_title(s); ax.set_xlabel('t (s)'); ax.grid(alpha=0.3)
    axs[0].set_ylabel('position error (m)')
    axs[0].legend(fontsize=8, loc='upper left')
    fig.suptitle('M5: position error vs time — same noise, EKF(green) vs Noise-only(red)', fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(out, dpi=110); plt.close(fig)
    print(f'saved {out}')


def main():
    base_dir = sys.argv[1] if len(sys.argv) > 1 else '/home/ubuntu/ros2_ws/outputs/baseline'
    ekf_dir = sys.argv[2] if len(sys.argv) > 2 else '/home/ubuntu/ros2_ws/outputs/ekf'
    bars(base_dir, ekf_dir, os.path.join(ekf_dir, 'ekf_compare_bars.png'))
    curves(ekf_dir, os.path.join(ekf_dir, 'ekf_compare_curves.png'))


if __name__ == '__main__':
    main()
