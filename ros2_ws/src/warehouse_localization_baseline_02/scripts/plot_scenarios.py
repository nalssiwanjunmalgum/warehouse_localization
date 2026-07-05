#!/usr/bin/env python3
"""
plot_scenarios.py
맵(점유격자) 배경 위에 C1~C5 시나리오를 그려 문서 임베드용 그림 2종을 만든다.
  1) scenarios_overview.png — 무대+경로: 실제 GT 경로 + 출발(●)/끝(★)
  2) failure_overview.png   — 비교: GT(초록) vs 추정(빨강) 경로, 맵 위에 겹침
공통: 기둥(회색 원, 20m격자), 랙(주황), featureless core(빨간 점선원).

방식 무관 재사용: CSV 접미사·추정 라벨을 인자로 → baseline/ekf/landmark 모두 사용.
실행: python3 plot_scenarios.py <results_dir> <map.pgm> <map.yaml> [suffix=baseline] [est_label=AMCL] [tag=M3 Baseline]
  예) EKF:      ... <outputs/ekf> <map.pgm> <map.yaml> ekf "노이즈+EKF" "M5 EKF"
      Landmark: ... <outputs/landmark> <map.pgm> <map.yaml> landmark "Landmark" "M6 Landmark"
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
RACKS = [(16, 0, 1, 2), (-16, 0, 1, 2), (0, 16, 2, 1), (0, -16, 2, 1)]

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
    return img, [ox, ox + w * res, oy, oy + h * res]


def load_run(csv_path):
    gx, gy, ex, ey, pe = [], [], [], [], []
    for r in csv.DictReader(open(csv_path)):
        gx.append(float(r['gt_x'])); gy.append(float(r['gt_y']))
        ex.append(float(r['est_x'])); ey.append(float(r['est_y']))
        pe.append(float(r['pos_err']))
    return (np.array(gx), np.array(gy), np.array(ex), np.array(ey), np.array(pe))


def draw_env(ax, img, extent):
    ax.imshow(img, cmap='gray', origin='lower', extent=extent, alpha=0.5, zorder=0)
    for (px, py) in PILLARS:
        ax.add_patch(plt.Circle((px, py), 0.6, color='dimgray', zorder=2))
    for (rx, ry, rw, rh) in RACKS:
        ax.add_patch(Rectangle((rx - rw / 2, ry - rh / 2), rw, rh,
                               color='darkorange', alpha=0.8, zorder=2))
    ax.set_aspect('equal')


def make_fig(img, extent, results, show_amcl, out, title, suffix='baseline', est_label='AMCL'):
    fig, axes = plt.subplots(2, 3, figsize=(16, 12))
    fig.suptitle(title, fontsize=13, y=0.985)
    axes = axes.ravel()
    for k, (sid, (label, start, goal)) in enumerate(SCEN.items()):
        ax = axes[k]
        draw_env(ax, img, extent)
        sub = ''
        try:
            gx, gy, ex, ey, pe = load_run(f'{results}/{sid}_{suffix}.csv')
            if show_amcl:
                ax.plot(gx, gy, color='limegreen', lw=2.2, zorder=3, label='ground truth')
                ax.plot(ex, ey, color='red', lw=1.4, ls='--', zorder=4, label=f'{est_label} est')
                sub = f'   ATE={np.sqrt(np.mean(pe**2)):.2f}m  max={pe.max():.1f}m'
            else:
                ax.plot(gx, gy, color='tab:blue', lw=1.8, zorder=3, label='GT path')
        except FileNotFoundError:
            pass
        ax.scatter(*start, c='limegreen', s=110, marker='o', ec='k', zorder=6)
        ax.scatter(*goal, c='red', s=200, marker='*', ec='k', zorder=6)
        ax.set_title(f'{label}{sub}\nstart {start} → goal {goal}', fontsize=10)
        ax.set_xlabel('x (m)'); ax.set_ylabel('y (m)'); ax.grid(alpha=0.2)
        if show_amcl:
            # GT+AMCL 둘 다 보이게 여유 범위 (AMCL 폭주 포함), 정사각
            lo, hi = -33, 33
            ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
        else:
            ax.set_xlim(-31, 31); ax.set_ylim(-31, 31)

    ax = axes[5]; ax.axis('off')
    if show_amcl:
        ax.plot([], [], color='limegreen', lw=2.2, label='ground truth (real)')
        ax.plot([], [], color='red', ls='--', lw=1.4, label=f'{est_label} estimate')
    else:
        ax.plot([], [], color='tab:blue', lw=1.8, label='ground-truth path')
    ax.scatter([], [], c='limegreen', s=110, marker='o', ec='k', label='start (init pose)')
    ax.scatter([], [], c='red', s=200, marker='*', ec='k', label='goal')
    ax.scatter([], [], c='dimgray', s=80, label='pillar (20m grid)')
    ax.scatter([], [], c='darkorange', s=80, marker='s', label='rack')
    ax.legend(loc='center', fontsize=12, frameon=True)

    # 윗줄/아랫줄 사이 간격을 넉넉히 → 아래 패널 2줄 제목이 위 패널 축라벨과 안 겹침
    fig.subplots_adjust(left=0.05, right=0.98, top=0.91, bottom=0.06,
                        hspace=0.42, wspace=0.28)
    fig.savefig(out, dpi=120)
    print(f'저장: {out}')


def main():
    results, pgm, yaml = sys.argv[1], sys.argv[2], sys.argv[3]
    suffix = sys.argv[4] if len(sys.argv) > 4 else 'baseline'
    est_label = sys.argv[5] if len(sys.argv) > 5 else 'AMCL'
    tag = sys.argv[6] if len(sys.argv) > 6 else 'M3 Baseline'
    img, extent = read_map(pgm, yaml)
    make_fig(img, extent, results, False, f'{results}/scenarios_overview.png',
             f'{tag} scenarios — map + ground-truth path (● start, ★ goal)', suffix, est_label)
    make_fig(img, extent, results, True, f'{results}/failure_overview.png',
             f'{tag} — ground truth (green) vs {est_label} estimate (red) on map', suffix, est_label)


if __name__ == '__main__':
    main()
