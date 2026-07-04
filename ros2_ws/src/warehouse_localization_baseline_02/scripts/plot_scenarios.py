#!/usr/bin/env python3
"""
plot_scenarios.py
맵(점유격자)을 배경으로, C1~C5 시나리오의 '실제 GT 경로 + 출발/끝점 + 기둥/랙'을 그려
가독성 좋은 시나리오 개요 그림을 만든다. (문서 임베드용)

실행: python3 plot_scenarios.py <results_dir> <map.pgm> <map.yaml> [out.png]
"""
import sys
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

PILLARS = [(-20, -20), (0, -20), (20, -20), (-20, 0), (20, 0),
           (-20, 20), (0, 20), (20, 20)]
RACKS = [(16, 0, 1, 2), (-16, 0, 1, 2), (0, 16, 2, 1), (0, -16, 2, 1)]  # x,y,w,h

# id: (label, start, goal)
SCEN = {
    'C1': ('C1  diagonal crossing', (-24, -24), (24, 24)),
    'C2': ('C2  offset slice',      (-24, 8),   (24, -8)),
    'C3': ('C3  closed loop',       (-22, -22), (-22, -22)),
    'C4': ('C4  stop at core',      (-24, 0),   (0, 0)),
    'C5': ('C5  zig-zag',           (24, -24),  (-18, 18)),
}


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
    extent = [ox, ox + w * res, oy, oy + h * res]
    return img, extent


def gt_path(csv_path):
    xs, ys = [], []
    for r in csv.DictReader(open(csv_path)):
        xs.append(float(r['gt_x'])); ys.append(float(r['gt_y']))
    return xs, ys


def draw_env(ax, img, extent):
    ax.imshow(img, cmap='gray', origin='lower', extent=extent, alpha=0.55, zorder=0)
    for (px, py) in PILLARS:
        ax.add_patch(plt.Circle((px, py), 0.6, color='dimgray', zorder=2))
    for (rx, ry, rw, rh) in RACKS:
        ax.add_patch(Rectangle((rx - rw / 2, ry - rh / 2), rw, rh,
                               color='darkorange', alpha=0.8, zorder=2))
    ax.add_patch(plt.Circle((0, 0), 4, fill=False, ls='--', ec='crimson', lw=1.2, zorder=2))
    ax.set_xlim(-31, 31); ax.set_ylim(-31, 31); ax.set_aspect('equal')


def main():
    results, pgm, yaml = sys.argv[1], sys.argv[2], sys.argv[3]
    out = sys.argv[4] if len(sys.argv) > 4 else results.rstrip('/') + '/scenarios_overview.png'
    img, extent = read_map(pgm, yaml)

    fig, axes = plt.subplots(2, 3, figsize=(16, 11))
    fig.suptitle('M3 Baseline scenarios — map + ground-truth path (● start, ★ goal)\n'
                 '● pillars (20m grid)  ▮ racks  ⌀ featureless core (r=4m)', fontsize=13)
    axes = axes.ravel()
    for k, (sid, (label, start, goal)) in enumerate(SCEN.items()):
        ax = axes[k]
        draw_env(ax, img, extent)
        try:
            xs, ys = gt_path(f'{results}/{sid}_baseline.csv')
            ax.plot(xs, ys, color='tab:blue', lw=1.8, zorder=3, label='GT path')
        except FileNotFoundError:
            pass
        ax.scatter(*start, c='limegreen', s=110, marker='o', ec='k', zorder=5)
        ax.scatter(*goal, c='red', s=200, marker='*', ec='k', zorder=5)
        ax.set_title(f'{label}\nstart {start} → goal {goal}', fontsize=10)
        ax.set_xlabel('x (m)'); ax.set_ylabel('y (m)'); ax.grid(alpha=0.2)

    # 6번째 칸: 범례/설명
    ax = axes[5]; ax.axis('off')
    ax.scatter([], [], c='limegreen', s=110, marker='o', ec='k', label='start (init pose)')
    ax.scatter([], [], c='red', s=200, marker='*', ec='k', label='goal')
    ax.plot([], [], color='tab:blue', lw=1.8, label='ground-truth path')
    ax.scatter([], [], c='dimgray', s=80, label='pillar (20m grid)')
    ax.scatter([], [], c='darkorange', s=80, marker='s', label='rack')
    ax.plot([], [], ls='--', color='crimson', label='featureless core (r≈4m)')
    ax.legend(loc='center', fontsize=12, frameon=True)

    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(out, dpi=120)
    print(f'저장: {out}')


if __name__ == '__main__':
    main()
