#!/usr/bin/env python3
"""
plot_per_scenario.py  (M7 시나리오별 3단계 비교)
시나리오 하나당 이미지 하나. 각 이미지에 3단계(Baseline│EKF│Landmark)를 나란히 그려
맵 위 GT(초록) vs 추정(빨강) 로 "문제→완화→해결" 진행을 시나리오 단위로 본다.

출력: <out_dir>/stages_C1.png … stages_C5.png
사용: python3 plot_per_scenario.py <baseline_dir> <ekf_dir> <landmark_dir> <map.pgm> <map.yaml> <out_dir>
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
# (제목, 폴더키, csv접미사) — 진행 순서
STAGES = [('Baseline (AMCL)', 'base', 'baseline'),
          ('+EKF (noise fused)', 'ekf', 'ekf'),
          ('+Landmark (reflectors)', 'lm', 'landmark')]


def read_map(pgm, yaml):
    f = open(pgm, 'rb')
    assert f.readline().strip() == b'P5'
    w, h = map(int, f.readline().split())
    f.readline()
    img = np.frombuffer(f.read(), dtype=np.uint8).reshape(h, w)
    res, ox, oy = 0.05, -32.0, -32.0
    for line in open(yaml):
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
    ax.imshow(img, cmap='gray', origin='lower', extent=extent, alpha=0.5, zorder=0)
    for (px, py) in PILLARS:
        ax.add_patch(plt.Circle((px, py), 0.6, color='dimgray', zorder=2))
    for (rx, ry, rw, rh) in RACKS:
        ax.add_patch(Rectangle((rx - rw / 2, ry - rh / 2), rw, rh,
                               color='darkorange', alpha=0.8, zorder=2))
    ax.set_aspect('equal'); ax.set_xlim(-33, 33); ax.set_ylim(-33, 33)


def main():
    base, ekf, lm, pgm, yaml, out = sys.argv[1:7]
    img, extent = read_map(pgm, yaml)
    dirs = {'base': base, 'ekf': ekf, 'lm': lm}
    for sid, (label, start, goal) in SCEN.items():
        fig, axes = plt.subplots(1, 3, figsize=(16, 5.6))
        fig.suptitle(f'{label}   —   start {start} → goal {goal}   '
                     '(green = ground truth, red = estimate)', fontsize=13)
        for ax, (stg_title, dk, suf) in zip(axes, STAGES):
            draw_env(ax, img, extent)
            d = load_run(f'{dirs[dk]}/{sid}_{suf}.csv')
            sub = ''
            if d is not None:
                gx, gy, ex, ey, pe = d
                ax.plot(gx, gy, color='limegreen', lw=2.4, zorder=3)
                ax.plot(ex, ey, color='red', lw=1.5, ls='--', zorder=4)
                sub = f'\nATE={np.sqrt(np.mean(pe**2)):.2f} m   max={pe.max():.1f} m'
            ax.scatter(*start, c='limegreen', s=90, marker='o', ec='k', zorder=6)
            ax.scatter(*goal, c='red', s=170, marker='*', ec='k', zorder=6)
            ax.set_title(f'{stg_title}{sub}', fontsize=11)
            ax.set_xlabel('x (m)'); ax.set_ylabel('y (m)'); ax.grid(alpha=0.2)
        fig.tight_layout(rect=[0, 0, 1, 0.93])
        p = f'{out}/stages_{sid}.png'
        fig.savefig(p, dpi=120); plt.close(fig)
        print(f'저장: {p}')


if __name__ == '__main__':
    main()
