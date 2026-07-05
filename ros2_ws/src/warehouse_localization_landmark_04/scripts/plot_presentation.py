#!/usr/bin/env python3
"""
plot_presentation.py  (발표용 개별 이미지)
시나리오 × 단계별로 '한 이미지에 한 플롯'. stages_CX(3패널)를 낱장으로 분리하고 글자를 키운다.
→ C{1..5} × {Baseline, +EKF, +Landmark} = 15장, <out_dir>(기본 presentation/)에 저장.

각 이미지: 맵 위 GT(초록) vs 추정(빨강), 큰 제목/축/ATE.
사용: python3 plot_presentation.py <baseline_dir> <ekf_dir> <landmark_dir> <map.pgm> <map.yaml> <out_dir>
"""
import sys
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

PILLARS = [(-20, -20), (0, -20), (20, -20), (-20, 0), (20, 0), (-20, 20), (0, 20), (20, 20)]
RACKS = [(16, 0, 1, 2), (-16, 0, 1, 2), (0, 16, 2, 1), (0, -16, 2, 1)]
SCEN = {
    'C1': ('C1  diagonal crossing', (-24, -24), (24, 24)),
    'C2': ('C2  offset slice',      (-24, 8),   (24, -8)),
    'C3': ('C3  closed loop',       (-22, -22), (-22, -22)),
    'C4': ('C4  stop at core',      (-24, 0),   (0, 0)),
    'C5': ('C5  zig-zag',           (24, -24),  (-18, 18)),
}
# (단계 라벨, 폴더키, csv접미사, 파일태그)
STAGES = [('Baseline (AMCL)', 'base', 'baseline', 'baseline'),
          ('+EKF (noise fused)', 'ekf', 'ekf', 'ekf'),
          ('+Landmark (reflectors)', 'lm', 'landmark', 'landmark')]


def read_map(pgm, ymap):
    f = open(pgm, 'rb')
    assert f.readline().strip() == b'P5'
    w, h = map(int, f.readline().split())
    f.readline()
    img = np.frombuffer(f.read(), dtype=np.uint8).reshape(h, w)
    res, ox, oy = 0.05, -32.0, -32.0
    for line in open(ymap):
        if line.startswith('resolution:'):
            res = float(line.split(':')[1])
        if line.startswith('origin:'):
            v = line.split('[')[1].split(']')[0].split(',')
            ox, oy = float(v[0]), float(v[1])
    return img, [ox, ox + w * res, oy, oy + h * res]


def load_run(path):
    gx, gy, ex, ey, pe = [], [], [], [], []
    try:
        for r in csv.DictReader(open(path)):
            gx.append(float(r['gt_x'])); gy.append(float(r['gt_y']))
            ex.append(float(r['est_x'])); ey.append(float(r['est_y']))
            pe.append(float(r['pos_err']))
    except FileNotFoundError:
        return None
    return (np.array(gx), np.array(gy), np.array(ex), np.array(ey), np.array(pe))


def draw_env(ax, img, extent):
    ax.imshow(img, cmap='gray', origin='lower', extent=extent, alpha=0.45, zorder=0)
    for (px, py) in PILLARS:
        ax.add_patch(plt.Circle((px, py), 0.7, color='dimgray', zorder=2))
    for (rx, ry, rw, rh) in RACKS:
        ax.add_patch(Rectangle((rx - rw / 2, ry - rh / 2), rw, rh,
                               color='darkorange', alpha=0.85, zorder=2))
    ax.set_aspect('equal'); ax.set_xlim(-33, 33); ax.set_ylim(-33, 33)


def main():
    base, ekf, lm, pgm, ymap, out = sys.argv[1:7]
    img, extent = read_map(pgm, ymap)
    dirs = {'base': base, 'ekf': ekf, 'lm': lm}
    n = 0
    for sid, (label, start, goal) in SCEN.items():
        for stg_label, dk, suf, tag in STAGES:
            fig, ax = plt.subplots(figsize=(9, 9.4))
            draw_env(ax, img, extent)
            d = load_run(f'{dirs[dk]}/{sid}_{suf}.csv')
            ate_txt = ''
            if d is not None:
                gx, gy, ex, ey, pe = d
                ax.plot(gx, gy, color='limegreen', lw=3.4, zorder=3, label='ground truth')
                ax.plot(ex, ey, color='red', lw=2.2, ls='--', zorder=4, label='estimate')
                ate_txt = f'ATE = {np.sqrt(np.mean(pe**2)):.2f} m    max = {pe.max():.1f} m'
            ax.scatter(*start, c='limegreen', s=260, marker='o', ec='k', lw=1.5, zorder=6, label='start')
            ax.scatter(*goal, c='red', s=460, marker='*', ec='k', lw=1.5, zorder=6, label='goal')
            ax.set_title(f'{label}\n{stg_label}', fontsize=21, fontweight='bold', pad=10)
            if ate_txt:
                ax.text(0.975, 0.975, ate_txt, transform=ax.transAxes, ha='right', va='top',
                        fontsize=16, fontweight='bold', zorder=7,
                        bbox=dict(boxstyle='round', fc='white', ec='0.5', alpha=0.92))
            ax.set_xlabel('x (m)', fontsize=17)
            ax.set_ylabel('y (m)', fontsize=17)
            ax.tick_params(labelsize=14)
            ax.grid(alpha=0.25)
            ax.legend(fontsize=14, loc='upper left', framealpha=0.9)
            fig.tight_layout()
            p = f'{out}/{sid}_{tag}.png'
            fig.savefig(p, dpi=125); plt.close(fig)
            n += 1
            print(f'저장: {p}')
    print(f'== 총 {n}장 ==')


if __name__ == '__main__':
    main()
