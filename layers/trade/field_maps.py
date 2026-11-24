"""
분야별 연결 지도 (D, 11/24): 2단계 6개 분야마다 작은 지도 한 장 (2 × 3)
실행: python layers/trade/field_maps.py   (2~5, analysis/stage2.py, analysis/validation/conditional_continent.py 다음.
      처음 실행 때 인터넷 필요 = cartopy가 Natural Earth 지도를 받음)
결과: figures/stage3_분야별_연결지도.png
설명: docs/layers/trade.md '분야별 연결 지도'

- 선 = 같은 그룹인 '둘 다 도입한' 나라 쌍 (analysis/stage2_pairs.csv, both_adopters = 1). 1단계가 비교하는 쌍과 같음
  → 분야별 선 수가 각 계층 result_*.csv ALL 줄 n_pairs와 같은지 확인 (다르면 멈춤)
- 6개 분야 전부 그림 (11/24 팀 결정, 서영): 묶인 분야만 고르지 않고 칸마다 p와 판정을 적음
- 칸마다 p 두 개를 나란히 (11/22 팀 결정): 전체 섞기 = 각 계층 result_*.csv ALL p,
  대륙 안 섞기 = analysis/validation/conditional_summary.csv (version all) p_continent. 대륙은 대륙 안 섞기가 정의상 안 됨
- 판정 = ×6 보정 후 p로 (11/22 팀 결정, key_message.md: 보정 전 p는 판정에 안 씀. 1단계도 2단계와 같은 6개 분야라 ×6).
  둘 다 0.05 미만 '남음', 하나만 '약한 힌트', 둘 다 아니면 '남지 않음'. 칸에 보정 전 → 보정 후 p를 같이 적음
- 대륙은 대륙 안 섞기가 없어서 두 섞기 비교가 안 됨 → 전체 섞기만으로 '뚜렷함'(< 0.01)・'약함'(0.01~0.05)・'차이 없음' (11/24 서영)
- 화살표 없음. 선은 '같은 그룹'이지 '영향'이 아님
- 지도는 서영 layers/region/adoption_maps.py와 같게: Robinson, Natural Earth 1:50m, 대표점 countries.json latlng
- 분야 색은 layers/trade/example_figure.py와 같음 (대륙・지역기구・언어・식민・소득・무역 순서 고정)
- 검정 새로 안 함. 기존 CSV만 읽음 → 결과 CSV 변화 없음
"""
import json
import sys
import warnings
from pathlib import Path

import cartopy.crs as ccrs
import cartopy.io.shapereader as shpreader
import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
warnings.filterwarnings("ignore", category=UserWarning)

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "src"))
from common import load_nodes, use_font  # noqa: E402

L = ROOT / "layers"
OUT = ROOT / "figures" / "stage3_분야별_연결지도.png"

# 판정에 쓰는 p: 6개 분야 Bonferroni (p × 6, 최대 1). 11/22 팀 결정 (11/24 서영 확인)
CORRECTION = 6

FIELDS = ["continent", "igo", "language", "colony", "income", "trade"]     # stage2.py MAIN 순서
FIELD_KO = dict(continent="대륙", igo="지역기구", language="언어", colony="식민", income="소득", trade="무역 (k = 5)")
FIELD_COL = dict(continent="#2a78d6", igo="#eb6834", language="#1baf7a",
                 colony="#eda100", income="#e87ba4", trade="#008300")
RESULT = dict(continent="region/result_continent.csv", igo="region/result_igo.csv",
              language="language/result_language.csv", colony="language/result_colony.csv",
              income="income/result_income.csv", trade="trade/result_trade.csv")
COND = dict(igo="igo", language="language", colony="colony", income="income", trade="trade")   # conditional_summary.csv layer 이름
INK, INK2, MUTED, SURF, LAND, LAND_EDGE = "#1a1a1a", "#52514e", "#898781", "#fcfcfb", "#ecebe6", "#ffffff"
NE_FIX = {"SDS": "SSD"}


def fmt(p):
    return "–" if p is None else f"{p:.3f}"


def adj(p):
    return None if p is None else min(1.0, p * CORRECTION)


def judge(p_basic, p_cont):
    if p_cont is None:                       # 대륙: 대륙 안 섞기 없음 → 전체 섞기만으로 (11/24 서영)
        q = adj(p_basic)
        word = "뚜렷함" if q < 0.01 else "약함" if q < 0.05 else "차이 없음"
        return f"전체 섞기 {word} (대륙 안 섞기는 해당 없음)"
    n = sum(adj(p) < 0.05 for p in (p_basic, p_cont))
    return {2: "남음", 1: "약한 힌트", 0: "남지 않음"}[n]


# ---------- 데이터 ----------
nodes = load_nodes()
C = {x["cca3"]: x for x in json.load(open(ROOT / "data" / "raw" / "countries.json", encoding="utf-8"))}
lat = {c: C[c]["latlng"][0] for c in nodes.index}
lon = {c: C[c]["latlng"][1] for c in nodes.index}

sp = pd.read_csv(ROOT / "analysis" / "stage2_pairs.csv")
sp = sp[sp.both_adopters == 1]
cond = pd.read_csv(ROOT / "analysis" / "validation" / "conditional_summary.csv")
cond = cond[cond.version == "all"].set_index("layer")

info = {}
for f in FIELDS:
    res = pd.read_csv(L / RESULT[f]).set_index("group").loc["ALL"]
    pairs = sp[sp[f] == 1][["src", "dst"]]
    assert len(pairs) == int(res.n_pairs), f"{f}: 선 {len(pairs)}개 ≠ result n_pairs {int(res.n_pairs)}"
    p_cont = float(cond.loc[COND[f], "p_continent"]) if f in COND else None
    if f in COND:
        assert abs(float(cond.loc[COND[f], "p_basic"]) - float(res.p)) < 1e-3, f"{f}: 전체 섞기 p가 두 CSV에서 다름"
    info[f] = dict(pairs=pairs, n=len(pairs), p_basic=float(res.p), p_cont=p_cont,
                   real=float(res.mean_gap_real), fake=float(res.mean_gap_fake_avg),
                   judge=judge(float(res.p), p_cont))
    print(f"{f:9s} 쌍 {len(pairs):5d}  실제 {res.mean_gap_real:.2f}년 vs 가짜 {res.mean_gap_fake_avg:.2f}년  "
          f"p 전체 {fmt(float(res.p))} / 대륙 안 {fmt(p_cont)}  → {info[f]['judge']}")

reader = shpreader.Reader(shpreader.natural_earth(resolution="50m", category="cultural", name="admin_0_countries"))
land = [rec.geometry for rec in reader.records() if NE_FIX.get(rec.attributes["ADM0_A3"], rec.attributes["ADM0_A3"]) != "ATA"]

# ---------- 그림 ----------
use_font()
PC, ROB = ccrs.PlateCarree(), ccrs.Robinson()
Y_LO = ROB.transform_point(0, -57, PC)[1]
Y_HI = ROB.transform_point(0, 84, PC)[1]
fig = plt.figure(figsize=(16, 9.6), facecolor=SURF)

W, H = 0.325, 0.28
for k, f in enumerate(FIELDS):
    r, c = divmod(k, 3)
    x0, y0 = 0.012 + c * (W + 0.006), 0.525 - r * (H + 0.125)
    ax = fig.add_axes([x0, y0, W, H], projection=ROB)
    ax.set_facecolor(SURF)
    ax.spines["geo"].set_visible(False)
    ax.set_global()
    ax.set_ylim(Y_LO, Y_HI)
    ax.add_geometries(land, crs=PC, facecolor=LAND, edgecolor=LAND_EDGE, linewidth=0.25, zorder=1)

    d = info[f]
    alpha = max(0.06, min(0.75, 12 / d["n"] ** 0.75))     # 선이 많을수록 얇고 투명하게 (서영 11/24)
    lw = 0.45 if d["n"] > 300 else 0.9
    for a, b in zip(d["pairs"].src, d["pairs"].dst):
        ax.plot([lon[a], lon[b]], [lat[a], lat[b]], transform=ccrs.Geodetic(), color=FIELD_COL[f],
                lw=lw, alpha=alpha, solid_capstyle="round", zorder=2)
    ends = sorted(set(d["pairs"].src) | set(d["pairs"].dst))
    ax.scatter([lon[e] for e in ends], [lat[e] for e in ends], s=5, color=INK2, lw=0, transform=PC, zorder=3)

    # 칸 제목 + 판정 / 쌍 수・연도 차이 / p 두 개
    tx = x0 + 0.006
    fig.patches.append(matplotlib.patches.Rectangle((x0, y0 + H + 0.078), 0.0035, 0.024,
                                                    transform=fig.transFigure, color=FIELD_COL[f]))   # 색 = 분야
    fig.text(tx, y0 + H + 0.076, FIELD_KO[f], fontsize=13.5, fontweight="bold", color=INK, va="bottom")
    jt = d["judge"]
    fig.text(x0 + W - 0.006, y0 + H + 0.078, jt, fontsize=10.5, fontweight="bold", color=INK, ha="right",
             va="bottom", bbox=dict(boxstyle="round,pad=0.3", fc="#f1f0ec", ec="none"))
    fig.text(tx, y0 + H + 0.047,
             f"둘 다 도입한 쌍 {d['n']:,}개 · 연결된 도입국 {len(ends)}개 · 평균 연도 차이 실제 {d['real']:.2f}년 vs 가짜 {d['fake']:.2f}년",
             fontsize=9.3, color=INK2, va="bottom")
    pc = ("대륙 안 섞기 해당 없음" if d["p_cont"] is None
          else f"대륙 안 섞기 {fmt(d['p_cont'])} → {fmt(adj(d['p_cont']))}")
    fig.text(tx, y0 + H + 0.020, f"p (보정 전 → ×{CORRECTION} 보정 후)  전체 섞기 {fmt(d['p_basic'])} → {fmt(adj(d['p_basic']))}  ·  {pc}",
             fontsize=9.3, color=INK2, va="bottom")

fig.text(0.012, 0.975, "분야별 연결 지도: 같은 그룹인 '둘 다 도입한' 나라 쌍", fontsize=17, fontweight="bold",
         color=INK, va="top")
fig.text(0.012, 0.938, "p = 같은 그룹끼리 도입 시기가 우연(가짜 세계 1,000개)보다 가까웠나.  "
         f"판정 (×{CORRECTION} 보정 후 p): 두 섞기 다 0.05 미만 '남음', 하나만 '약한 힌트' (11/22 팀 규칙)",
         fontsize=10.5, color=INK2, va="top")
fig.text(0.012, 0.012,
         "선은 '같은 그룹'이라는 뜻이지 '영향'・'따라 함'이 아님 (화살표 없음).  무역: 연도 불확실한 19개국을 빼면 효과가 사라짐 "
         "(docs/analysis/exclude_checked.md).  선이 많은 분야는 얇고 투명하게 그림\n"
         "자료: 연결 analysis/stage2_pairs.csv, 전체 섞기 p 각 계층 result_*.csv, 대륙 안 섞기 p "
         "analysis/validation/conditional_summary.csv.  대표점 countries.json.  지도 Natural Earth 1:50m",
         fontsize=8.5, color=MUTED, va="bottom", linespacing=1.5)
OUT.parent.mkdir(exist_ok=True)
fig.savefig(OUT, dpi=200, facecolor=SURF)
print("저장:", OUT.relative_to(ROOT))
