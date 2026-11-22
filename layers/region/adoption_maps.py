"""
연도별 설탕세 도입 지도 4장 (A, 11/22): 2014・2017・2019・2023년까지
실행: python layers/region/adoption_maps.py   (make_layer.py 다음. 처음 실행 때 인터넷 필요)
설명 문서: docs/layers/region.md '도입 지도'

- 나라 면을 도입 시기 색으로 칠함 (한 색 계열, 이른 시기 연함 → 늦은 시기 진함). 미도입 = 그 해까지 안 함 (연회색)
- 둘 다 도입한 육상 국경 쌍은 두 나라 대표점(countries.json latlng)을 잇는 얇은 선 (시간 네트워크).
  경도 차 40도가 넘는 긴 국경선(러시아 등)은 점선으로 흐리게 → 큰 나라 하나가 '연결 중심'처럼 보이지 않게
- 면이 작은 섬나라(지도에서 안 보임)는 대표점에 같은 색 점을 더 찍음
- 지도: Natural Earth 1:50m 나라 경계 (퍼블릭 도메인). cartopy가 처음 실행 때 받아서 캐시에 둠 (저장소에 안 넣음)
  나라 코드는 ADM0_A3 (ISO_A3는 프랑스・노르웨이가 -99). 남수단만 SDS → SSD
- 투영: Robinson. 남극 뺌
- 검정 없음. nodes.csv와 countries.json만 읽음 → 결과 CSV 변화 없음
결과: figures/stage3_도입지도_2014.png, _2017.png, _2019.png, _2023.png
"""
import json
import sys
import warnings
from pathlib import Path

import cartopy.crs as ccrs
import cartopy.io.shapereader as shpreader
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
warnings.filterwarnings("ignore", category=UserWarning)

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "src"))
from common import load_nodes  # noqa: E402

FIG = ROOT / "figures"
have = {f.name for f in font_manager.fontManager.ttflist}
plt.rcParams["font.family"] = next((f for f in ["Malgun Gothic", "AppleGothic", "NanumGothic"] if f in have), "sans-serif")
plt.rcParams["axes.unicode_minus"] = False

INK, INK2, MUTED, SURF = "#0b0b0b", "#52514e", "#898781", "#fcfcfb"
NONE_FILL, EDGE = "#e6e5e0", "#fcfcfb"
PERIODS = [   # (이름, 시작, 끝, 색: 파랑 한 계열, 이른 시기 연함 → 늦은 시기 진함)
    ("1990년 전", -np.inf, 1989, "#b7d3f6"),
    ("1990~2013", 1990, 2013, "#6da7ec"),
    ("2014~2016", 2014, 2016, "#2a78d6"),
    ("2017~2019", 2017, 2019, "#1c5cab"),
    ("2020~2023", 2020, 2023, "#0d366b"),
]
SNAPS = [2014, 2017, 2019, 2023]
LONG = 40          # 이 경도 차보다 긴 국경선은 점선
SMALL = 2.0        # 면적(도²)이 이보다 작으면 점을 더 찍음
NE_FIX = {"SDS": "SSD"}


def period_color(y):
    for _, lo, hi, col in PERIODS:
        if lo <= y <= hi:
            return col
    return None


nodes = load_nodes()
yr = nodes.year_imp
ana = nodes[nodes.in_analysis == 1]
n_before = int(((nodes.adopter == 1) & (nodes.in_analysis == 0)).sum())
C = {x["cca3"]: x for x in json.load(open(ROOT / "data" / "raw" / "countries.json", encoding="utf-8"))}
lat = pd.Series({c: C[c]["latlng"][0] for c in nodes.index})
lon = pd.Series({c: C[c]["latlng"][1] for c in nodes.index})
border = sorted({tuple(sorted((a, b))) for a in nodes.index for b in C[a].get("borders", []) if b in nodes.index})

reader = shpreader.Reader(shpreader.natural_earth(resolution="50m", category="cultural", name="admin_0_countries"))
shapes = {}
for rec in reader.records():
    code = NE_FIX.get(rec.attributes["ADM0_A3"], rec.attributes["ADM0_A3"])
    if code == "ATA":
        continue
    shapes.setdefault(code, []).append(rec.geometry)
missing = sorted(set(nodes.index[nodes.adopter == 1]) - set(shapes))
assert not missing, f"Natural Earth에 없는 도입국: {missing}"
area = {c: sum(g.area for g in gs) for c, gs in shapes.items()}

PC = ccrs.PlateCarree()
ROB = ccrs.Robinson()
Y_LO = ROB.transform_point(0, -57, PC)[1]
Y_HI = ROB.transform_point(0, 84, PC)[1]
for t in SNAPS:
    done = yr <= t
    fig = plt.figure(figsize=(13, 7.2), facecolor=SURF)
    ax = fig.add_axes([0.01, 0.13, 0.98, 0.73], projection=ROB)
    ax.set_facecolor(SURF)
    ax.spines["geo"].set_visible(False)
    ax.set_global()
    ax.set_ylim(Y_LO, Y_HI)            # 남극・북극 바다 잘라냄 (위도 -57 ~ 84)

    # 나라 면
    for code, gs in shapes.items():
        col = period_color(yr[code]) if code in nodes.index and done[code] else NONE_FILL
        ax.add_geometries(gs, crs=PC, facecolor=col, edgecolor=EDGE, linewidth=0.3, zorder=1)

    # 둘 다 도입한 국경 쌍
    n_both = 0
    for a, b in border:
        if not (done[a] and done[b]):
            continue
        n_both += 1
        long_line = abs(lon[a] - lon[b]) > LONG
        ax.plot([lon[a], lon[b]], [lat[a], lat[b]], transform=ccrs.Geodetic(), zorder=3,
                color=INK2 if not long_line else MUTED, lw=0.7 if not long_line else 0.6,
                ls="-" if not long_line else (0, (2, 2)), alpha=0.9 if not long_line else 0.6)

    # 작은 나라 점 (면이 안 보이는 섬나라 등)
    small = [c for c in nodes.index if done[c] and (c not in area or area[c] < SMALL)]
    for c in small:
        ax.scatter(lon[c], lat[c], s=16, color=period_color(yr[c]), edgecolor=SURF, lw=0.5, transform=PC, zorder=4)

    n_ana = int((ana.year_imp <= t).sum())
    fig.text(0.015, 0.955, f"{t}년까지 설탕세를 도입한 나라: 1990년 이후 {n_ana}개국 (+1990년 전 {n_before}개국)",
             fontsize=15, fontweight="bold", color=INK, va="top")
    fig.text(0.015, 0.905, f"색 = 도입 시기 (진할수록 늦게 도입)  ·  선 = 둘 다 도입한 육상 국경 쌍 {n_both}개",
             fontsize=11, color=INK2, va="top")

    handles = [Patch(facecolor=col, edgecolor="none", label=name) for name, lo, _, col in PERIODS if lo <= t]
    handles += [Patch(facecolor=NONE_FILL, edgecolor="none", label=f"{t}년까지 안 함"),
                Line2D([], [], color=INK2, lw=1, label="국경, 둘 다 도입"),
                Line2D([], [], color=MUTED, lw=1, ls=(0, (2, 2)), label=f"긴 국경선 (경도 차 {LONG}도 넘음)")]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.055), ncol=len(handles),
               frameon=False, fontsize=9.5, handlelength=1.6, columnspacing=1.4)
    fig.text(0.015, 0.012,
             "폐지한 나라도 도입 색 그대로 칠함 (덴마크 2014, 노르웨이 2021, 이스라엘 2023 폐지).  "
             "'국경 쌍' = 두 나라 다 도입한 육상 국경 쌍 수 (도입국 수와 다른 숫자).  선은 '연결'이지 '영향'이 아님\n"
             "자료: World Bank Global SSB Tax Database (2023년 8월판) + 폐지·누락 보충 (data/raw/manual_adoptions.csv).  "
             "국경·대표점: countries.json.  지도: Natural Earth 1:50m",
             fontsize=8, color=MUTED, va="bottom", linespacing=1.5)
    out = FIG / f"stage3_도입지도_{t}.png"
    fig.savefig(out, dpi=200, facecolor=SURF)
    plt.close(fig)
    print(f"{t}년: 1990년 이후 도입 {n_ana}개국, 국경 쌍 {n_both}개, 작은 나라 점 {len(small)}개 → {out.relative_to(ROOT)}")
