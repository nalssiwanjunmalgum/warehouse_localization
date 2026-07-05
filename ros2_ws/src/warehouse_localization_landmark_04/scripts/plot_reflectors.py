#!/usr/bin/env python3
"""
plot_reflectors.py  (P3/M6 반사판 배치 시각화)
landmarks.yaml 의 반사판 16개 위치를 맵 위에 그린다.
  왼쪽: 배치도 — 반사판(파랑, id 표시) + 기둥(회색) + 랙(주황)
  오른쪽: 커버리지 히트맵 — 각 지점에서 12m 내 보이는 반사판 수(≥3 등고선). 왜 이렇게 흩뿌렸나.

사용: python3 plot_reflectors.py <landmarks.yaml> <map.pgm> <map.yaml> <out.png>
"""
import sys
import yaml
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

PILLARS = [(-20, -20), (0, -20), (20, -20), (-20, 0), (20, 0), (-20, 20), (0, 20), (20, 20)]
RACKS = [(16, 0, 1, 2), (-16, 0, 1, 2), (0, 16, 2, 1), (0, -16, 2, 1)]
LIDAR = 12.0


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


def draw_env(ax, img, extent):
    ax.imshow(img, cmap='gray', origin='lower', extent=extent, alpha=0.45, zorder=0)
    for (px, py) in PILLARS:
        ax.add_patch(plt.Circle((px, py), 0.6, color='dimgray', zorder=2))
    for (rx, ry, rw, rh) in RACKS:
        ax.add_patch(Rectangle((rx - rw / 2, ry - rh / 2), rw, rh,
                               color='darkorange', alpha=0.8, zorder=2))
    ax.set_aspect('equal'); ax.set_xlim(-31, 31); ax.set_ylim(-31, 31)
    ax.set_xlabel('x (m)'); ax.set_ylabel('y (m)')


def main():
    lyaml, pgm, ymap, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    db = yaml.safe_load(open(lyaml))
    R = np.array([[l['x'], l['y']] for l in db['landmarks']])
    ids = [l['id'] for l in db['landmarks']]
    img, extent = read_map(pgm, ymap)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 7.2))

    # --- 왼쪽: 배치도 ---
    draw_env(a1, img, extent)
    a1.scatter(R[:, 0], R[:, 1], s=130, c='royalblue', marker='^', ec='k', zorder=5)
    for (x, y), i in zip(R, ids):
        a1.text(x + 0.7, y + 0.7, f'R{i:02d}', fontsize=8, color='navy', zorder=6)
    # 예시 12m 가시 반경 (core 기준)
    a1.add_patch(plt.Circle((0, 0), LIDAR, fill=False, ls=':', ec='royalblue', lw=1.2, zorder=3))
    a1.scatter([], [], s=130, c='royalblue', marker='^', ec='k', label='reflector (16)')
    a1.scatter([], [], s=80, c='dimgray', label='pillar (20m grid)')
    a1.scatter([], [], s=80, c='darkorange', marker='s', label='rack')
    a1.plot([], [], ls=':', color='royalblue', label='12m LiDAR range @ core')
    a1.legend(loc='upper right', fontsize=8)
    a1.set_title(f'Reflector layout — {len(R)} poles, irregular (unique constellations)')

    # --- 오른쪽: 커버리지 히트맵 (12m 내 반사판 수) ---
    draw_env(a2, img, extent)
    g = np.arange(-30, 30.1, 0.5)
    GX, GY = np.meshgrid(g, g)
    cnt = np.zeros_like(GX)
    for (rx, ry) in R:
        cnt += (np.hypot(GX - rx, GY - ry) <= LIDAR).astype(int)
    im = a2.pcolormesh(GX, GY, cnt, cmap='YlGn', alpha=0.6, zorder=1, shading='auto', vmin=0, vmax=cnt.max())
    a2.contour(GX, GY, cnt, levels=[2.5], colors='crimson', linewidths=1.6, zorder=3)
    a2.scatter(R[:, 0], R[:, 1], s=60, c='royalblue', marker='^', ec='k', zorder=5)
    cb = fig.colorbar(im, ax=a2, fraction=0.046, pad=0.04)
    cb.set_label('# reflectors within 12m')
    a2.set_title('Coverage — red line = ≥3 reflectors visible (triangulation OK)')

    fig.suptitle('Warehouse reflectors: scattered layout & LiDAR coverage (P3 design)', fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(out, dpi=120)
    print(f'저장: {out}')


if __name__ == '__main__':
    main()
