#!/usr/bin/env python3
"""
clean_map.py  (P2 후처리)
map_builder 로 만든 점유격자의 '부챗살/미관측' 얼룩을 정리한다.
벽·기둥(점유)을 장벽으로 두고, 실내에서 관측된 free 와 이어진 unknown 셀을 free 로 채운다.
→ 깔끔한 통짜 free 실내 + 벽/기둥/랙만 검게. 점유 셀은 안 건드려 AMCL 결과에 영향 없음.

원리: free 영역을 '점유가 아닌 셀'로만 반복 팽창(numpy) → 실내 전체가 free 로 채워짐.
      벽 밖(연결 안 됨)은 unknown 유지.

실행: python3 clean_map.py <in.pgm> <out.pgm>
값 규약: occupied=0(검정), free=254(흰색), unknown=128(회색)
"""
import sys
import numpy as np


def read_pgm(path):
    f = open(path, 'rb')
    assert f.readline().strip() == b'P5'
    w, h = map(int, f.readline().split())
    f.readline()
    return np.frombuffer(f.read(), dtype=np.uint8).reshape(h, w).copy()


def write_pgm(path, img):
    h, w = img.shape
    with open(path, 'wb') as f:
        f.write(bytearray(f'P5\n{w} {h}\n255\n', 'ascii'))
        f.write(img.tobytes())


def main():
    inp, outp = sys.argv[1], sys.argv[2]
    img = read_pgm(inp)
    occupied = (img == 0)
    allowed = ~occupied                 # free 로 채워질 수 있는 셀(점유 제외)
    reach = (img == 254) & allowed      # 시작: 관측된 free

    it = 0
    while it < 2000:
        it += 1
        new = reach.copy()
        new[1:, :]  |= reach[:-1, :] & allowed[1:, :]
        new[:-1, :] |= reach[1:, :]  & allowed[:-1, :]
        new[:, 1:]  |= reach[:, :-1] & allowed[:, 1:]
        new[:, :-1] |= reach[:, 1:]  & allowed[:, :-1]
        if new.sum() == reach.sum():
            break
        reach = new

    out = np.full(img.shape, 128, dtype=np.uint8)   # 기본 unknown
    out[reach] = 254                                # 실내 free (부챗살·미관측 채움)
    out[occupied] = 0                               # 벽/기둥/랙 유지
    write_pgm(outp, out)

    n = img.size
    print(f'{it} iters | free {int(reach.sum())} ({100*reach.sum()/n:.0f}%) '
          f'| occupied {int(occupied.sum())} | unknown(벽밖) {int((out==128).sum())}')
    print(f'저장: {outp}')


if __name__ == '__main__':
    main()
