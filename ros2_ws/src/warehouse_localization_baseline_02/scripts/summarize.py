#!/usr/bin/env python3
"""
summarize.py  (M4)
metrics_recorder CSV → per-run 요약 수치(JSON) 산출. 시나리오별 핵심 값 포함.
정의는 docs/CAPTURE_SPEC.md 참조.

실행: python3 summarize.py <metrics.csv> [--scenario C1] [--out summary.json]
"""
import sys
import csv
import json
import math
import argparse
import numpy as np

RECONV_HI = 1.0    # cov_major 이 값 초과 = 발산 시작
RECONV_LO = 0.3    # 이 값 미만으로 복귀 = 재수렴


def load(path):
    with open(path) as f:
        r = csv.DictReader(f)
        cols = {k: [] for k in r.fieldnames}
        for row in r:
            for k, v in row.items():
                cols[k].append(float(v))
    return {k: np.array(v) for k, v in cols.items()}


def rpe(gx, gy, gyaw, ex, ey, eyaw, d):
    """SE2 상대 포즈 오차(구간 d)의 RMS 병진 오차."""
    n = len(gx)
    if n <= d:
        return None
    errs = []
    for i in range(n - d):
        j = i + d
        # 상대 이동을 각 시작 프레임 기준으로
        cg, sg = math.cos(-gyaw[i]), math.sin(-gyaw[i])
        rgx = cg * (gx[j] - gx[i]) - sg * (gy[j] - gy[i])
        rgy = sg * (gx[j] - gx[i]) + cg * (gy[j] - gy[i])
        ce, se = math.cos(-eyaw[i]), math.sin(-eyaw[i])
        rex = ce * (ex[j] - ex[i]) - se * (ey[j] - ey[i])
        rey = se * (ex[j] - ex[i]) + ce * (ey[j] - ey[i])
        errs.append(math.hypot(rex - rgx, rey - rgy))
    return float(math.sqrt(np.mean(np.array(errs) ** 2)))


def reconv_events(t, cov):
    """cov 가 HI 초과 후 LO 미만 복귀까지 걸린 시간 목록."""
    events = []
    diverged_at = None
    for i in range(len(cov)):
        if diverged_at is None and cov[i] > RECONV_HI:
            diverged_at = t[i]
        elif diverged_at is not None and cov[i] < RECONV_LO:
            events.append(round(t[i] - diverged_at, 2))
            diverged_at = None
    return events


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csv')
    ap.add_argument('--scenario', default='')
    ap.add_argument('--out', default='')
    a = ap.parse_args()
    d = load(a.csv)
    t, pe, cov = d['t'], d['pos_err'], d['cov_major']

    # 개활 구간(가시빔 하위 30%)에서의 오차 증가 기울기
    vb = d['visible_beams']
    open_mask = vb <= np.percentile(vb, 30)
    drift_rate = None
    if open_mask.sum() >= 2:
        drift_rate = float(np.polyfit(t[open_mask], pe[open_mask], 1)[0])  # m/s

    dt = t[1] - t[0] if len(t) > 1 else 0.1
    d_idx = max(1, int(round(1.0 / dt)))    # ~1초 구간

    s = {
        'scenario': a.scenario,
        'n_samples': int(len(t)),
        'duration_s': round(float(t[-1]), 2),
        'ATE_rms_m': round(float(math.sqrt(np.mean(pe ** 2))), 4),
        'max_err_m': round(float(pe.max()), 4),
        'mean_err_m': round(float(pe.mean()), 4),
        'final_err_m': round(float(pe[-1]), 4),
        'max_cov_major_m': round(float(cov.max()), 4),
        'mean_cov_major_m': round(float(cov.mean()), 4),
        'RPE_1s_rms_m': (round(rpe(d['gt_x'], d['gt_y'], d['gt_yaw'],
                                   d['est_x'], d['est_y'], d['est_yaw'], d_idx), 4)),
        'drift_rate_m_per_s': (round(drift_rate, 4) if drift_rate is not None else None),
        # C3: 시작 대비 추정 변위 (폐루프면 이상적 0)
        'loop_disp_m': round(float(math.hypot(d['est_x'][-1] - d['est_x'][0],
                                              d['est_y'][-1] - d['est_y'][0])), 4),
        # C5: 재수렴 이벤트 시간들
        'reconv_events_s': reconv_events(t, cov),
    }
    print(json.dumps(s, ensure_ascii=False, indent=2))
    out = a.out or (a.csv.rsplit('.', 1)[0] + '.summary.json')
    with open(out, 'w') as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
    print(f'저장: {out}')


if __name__ == '__main__':
    main()
