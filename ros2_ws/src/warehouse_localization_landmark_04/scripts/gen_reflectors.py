#!/usr/bin/env python3
"""
gen_reflectors.py  (M6.1)
반사판 오버레이 월드 + 랜드마크 좌표 DB(yaml)를 생성한다. (설계·좌표 근거: docs/P3_SENSOR_LANDMARK.md)

- 베이스 월드(warehouse_open.world)를 읽어 **반사판 16개(가는 폴)** 를 추가한 새 월드를 쓴다.
  → 베이스 월드/occupancy 맵은 불변(공정 비교). 반사판은 M6 전용 오버레이 월드에만.
- landmarks.yaml (id,x,y) 를 쓴다 → landmark_localizer 가 참조하는 "내 방식의 지도".

사용(소스 트리에서 1회):
  python3 gen_reflectors.py <base_world> <out_world> <out_yaml>
  기본값은 컨테이너 소스 경로.
"""
import sys

# P3 설계 확정 좌표 (map 프레임, m). 불규칙 배치(고유 성좌) — 근거: docs/P3_SENSOR_LANDMARK §3
REFLECTORS = [
    (0, -14.67, -13.67), (1, -16.34, -4.93), (2, -12.49, 7.54), (3, -17.40, 13.13),
    (4, -7.87, -15.38), (5, -8.01, -5.28), (6, -4.05, 3.58), (7, -3.87, 15.58),
    (8, 1.95, -14.62), (9, 3.46, -5.54), (10, 3.61, 6.24), (11, 4.62, 12.80),
    (12, 15.29, -13.21), (13, 13.76, -6.78), (14, 14.28, 7.79), (15, 18.05, 16.10),
]
RADIUS = 0.08     # 가는 폴 (기둥 0.2 보다 얇음 → 폭으로 구별)
LENGTH = 1.2      # z 0~1.2, LiDAR 평면(z≈0.18) 가로지름
ZC = 0.60


def reflector_model():
    lines = ['    <model name="reflectors">', '      <static>true</static>',
             '      <link name="reflectors_link">',
             '        <!-- M6 반사판: 가는 폴(r0.08). 검출=기하(폭), 식별=성좌. occupancy 맵엔 없음. -->']
    for (i, x, y) in REFLECTORS:
        g = f'<geometry><cylinder><radius>{RADIUS}</radius><length>{LENGTH}</length></cylinder></geometry>'
        pose = f'<pose>{x} {y} {ZC} 0 0 0</pose>'
        lines.append(f'        <collision name="c_R{i:02d}">{pose}{g}</collision>')
        lines.append(f'        <visual name="v_R{i:02d}">{pose}{g}'
                     '<material><script><uri>file://media/materials/scripts/gazebo.material</uri>'
                     '<name>Gazebo/Yellow</name></script></material></visual>')
    lines += ['      </link>', '    </model>']
    return '\n'.join(lines)


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else \
        '/home/ubuntu/ros2_ws/src/warehouse_localization_sim_01/worlds/warehouse/warehouse_open.world'
    out_world = sys.argv[2] if len(sys.argv) > 2 else \
        '/home/ubuntu/ros2_ws/src/warehouse_localization_sim_01/worlds/warehouse/warehouse_reflectors.world'
    out_yaml = sys.argv[3] if len(sys.argv) > 3 else \
        '/home/ubuntu/ros2_ws/src/warehouse_localization_landmark_04/config/landmarks.yaml'

    with open(base) as f:
        w = f.read()
    if '</world>' not in w:
        raise SystemExit('base world 에 </world> 없음')
    w2 = w.replace('  </world>', reflector_model() + '\n\n  </world>', 1)
    with open(out_world, 'w') as f:
        f.write(w2)
    print(f'월드 작성: {out_world}  (반사판 {len(REFLECTORS)}개 추가)')

    y = ['# M6 랜드마크 좌표 DB — 물리 반사판(warehouse_reflectors.world)과 일치.',
         '# occupancy 격자(AMCL 지도)와 별개. landmark_localizer 가 성좌매칭·삼각측량에 사용.',
         'frame_id: map', f'reflector_radius: {RADIUS}', 'landmarks:']
    for (i, x, yy) in REFLECTORS:
        y.append(f'  - {{id: {i}, x: {x}, y: {yy}}}')
    with open(out_yaml, 'w') as f:
        f.write('\n'.join(y) + '\n')
    print(f'DB 작성: {out_yaml}')


if __name__ == '__main__':
    main()
