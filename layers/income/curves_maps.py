"""
3단계 발표용 그림 3종: 전체 확산 곡선, 그룹별 확산 곡선, 연도별 도입 지도 스냅샷 4장 (C, 11/22)
실행: python layers/income/curves_maps.py   (2~5 다 끝난 뒤, 몇 초)
설명: docs/layers/income.md '3단계 그림'

그림 1  figures/stage3_전체_확산곡선.png
  nodes.csv in_analysis = 1 (1990~2023 도입 114개국) 연도별 누적 도입 수
  멕시코 2014년, WHO 권고 2016년 10월 표시, 2017~2019년 띠
그림 2  figures/stage3_그룹별_확산곡선.png
  서현의 layers/language/supplementary/curve_arabic_spanish.csv・_summary.csv 그대로 (새로 계산 안 함)
  분모 = 그룹 전체 나라 수 (미도입 포함, common.group_curve)
그림 3  figures/stage3_도입지도_스냅샷.png
  2014・2017・2019・2023년까지 도입한 나라. 점 = 나라 (countries.json 위도・경도), 선 = 육상 국경 (countries.json borders)
  둘 다 도입한 국경 쌍은 진한 선 → '연결된 나라가 같이 도입했나'를 보는 시간 네트워크
  지도 라이브러리(geopandas 등)를 안 쓰려고 점 지도로 그림 (requirements.txt 안 바꿈)

- 미도입 = '그 해까지 안 함'. 지도의 화살표・선은 '영향'이 아님
- 1990년 전 도입 7개국(BRA, DNK, FJI, MHL, NIU, NOR, STP)은 곡선에서 빠지고(분석 대상 밖) 지도에선 따로 표시
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / "figures"
INK, MUTED, GRID, BAND, ACCENT = "#1d1d1f", "#6e6e73", "#e8e8ed", "#ececf1", "#2a6fdb"

have = {f.name for f in font_manager.fontManager.ttflist}
plt.rcParams["font.family"] = next((f for f in ["Malgun Gothic", "AppleGothic", "NanumGothic"] if f in have), "DejaVu Sans")
plt.rcParams.update({"axes.unicode_minus": False, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#86868b", "xtick.color": MUTED, "ytick.color": MUTED, "font.size": 10})

nodes = pd.read_csv(ROOT / "data" / "processed" / "nodes.csv").set_index("iso3")
ana = nodes[nodes.in_analysis == 1]
SRC = "자료: World Bank Global SSB Tax Database (2023년 8월판) + 폐지·누락 보충 (data/raw/manual_adoptions.csv)"

# ---------- 그림 1. 전체 확산 곡선 ----------
yrs = np.arange(1990, 2024)
cum = np.array([(ana.year_imp <= t).sum() for t in yrs])
n1719 = int(ana.year_imp.between(2017, 2019).sum())
mex = int(nodes.loc["MEX", "year_imp"])
fig, ax = plt.subplots(figsize=(8.5, 4.4))
ax.axvspan(2016.5, 2019.5, color=BAND, lw=0)
ax.step(yrs, cum, where="post", color=INK, lw=2)
ax.axvline(mex, color=ACCENT, lw=1, ls="--")
ax.text(mex - 0.3, 98, f"멕시코 {mex}년", ha="right", va="top", color=ACCENT, fontsize=9)
ax.axvline(2016.75, color=ACCENT, lw=1, ls="--")
ax.text(2016.95, 118, "WHO 권고 2016년 10월", ha="left", va="top", color=ACCENT, fontsize=9)
ax.text(2019.7, 30, f"← 2017~2019년\n    3년 동안 {n1719}개국", ha="left", color=INK, fontsize=9.5)
ax.annotate(f"{cum[-1]}개국", (2023, cum[-1]), xytext=(5, -4), textcoords="offset points", ha="left", va="center", color=INK, fontsize=9.5)
ax.set_title(f"설탕세 확산 곡선: 2017~2019년 3년 동안 {n1719}개국이 도입", loc="left", fontsize=12.5, fontweight="bold", color=INK)
ax.set_xlabel("연도")
ax.set_ylabel("누적 도입 국가 수 (개국)")
ax.set_ylim(0, 120)
ax.set_xlim(1990, 2025.8)
ax.grid(axis="y", color=GRID, lw=0.8)
ax.set_axisbelow(True)
fig.text(0.01, 0.01, f"{SRC}. 1990~2023년 도입 {len(ana)}개국 (1990년 전 도입 7개국 제외)", fontsize=7.5, color=MUTED)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "stage3_전체_확산곡선.png", dpi=200)
plt.close(fig)
print(f"그림 1: 1990~2023 {len(ana)}개국, 2017~19 {n1719}개국, 2014 누적 {cum[yrs == 2014][0]}")

# ---------- 그림 2. 그룹별 확산 곡선 (서현 계산 그대로) ----------
sup = ROOT / "layers" / "language" / "supplementary"
cur = pd.read_csv(sup / "curve_arabic_spanish.csv")
summ = pd.read_csv(sup / "curve_arabic_spanish_summary.csv").set_index("group")
fig, ax = plt.subplots(figsize=(8.5, 4.4))
STYLE = {"Arabic": ACCENT, "Spanish": "#8e8e93"}
for g, col in STYLE.items():
    s, c = summ.loc[g], cur[cur.group == g]
    ax.step(c.year, c.cum_pct, where="post", color=col, lw=2.2,
            label=f"{s.label}: {s.members}개국 중 {s.adopters_by_2023}개국 도입 (가운데 50% {s.iqr_years:g}년 안)")
a, s = summ.loc["Arabic"], summ.loc["Spanish"]
ax.annotate(f"{a.label}: 중앙 {a.median_year:.0f}년\n가운데 50%가 {a.iqr_years:g}년 안에 도입 (급격)",
            (2016.6, 11), xytext=(2003, 14), color=INK, fontsize=9, va="center",
            arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
ax.annotate(f"{s.label}: {s.first_year}년부터\n가운데 50%가 {s.iqr_years:g}년에 걸쳐 도입 (점진)",
            (1997, 21), xytext=(1991.5, 58), color=INK, fontsize=9, va="center",
            arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
ax.set_title("같은 언어권이라도 퍼진 모양이 다르다", loc="left", fontsize=12.5, fontweight="bold", color=INK)
ax.set_xlabel("연도")
ax.set_ylabel("그룹 안 누적 도입 비율 (%, 분모 = 그룹 전체)")
ax.set_ylim(0, 105)
ax.set_xlim(1990, 2024)
ax.grid(axis="y", color=GRID, lw=0.8)
ax.set_axisbelow(True)
ax.legend(frameon=False, loc="upper left", fontsize=8.5)
fig.text(0.01, 0.01, f"{SRC}. 언어 그룹 계산: 서현 (curve_arabic_spanish.csv)", fontsize=7.5, color=MUTED)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "stage3_그룹별_확산곡선.png", dpi=200)
plt.close(fig)
print(f"그림 2: 아랍어권 {a.adopters_by_2023}/{a.members} (IQR {a.iqr_years}), 스페인어권 {s.adopters_by_2023}/{s.members} (IQR {s.iqr_years})")

# ---------- 그림 3. 도입 지도 스냅샷 4장 ----------
C = {x["cca3"]: x for x in json.load(open(ROOT / "data" / "raw" / "countries.json", encoding="utf-8"))}
codes = list(nodes.index)
lat = pd.Series({c: C[c]["latlng"][0] for c in codes})
lon = pd.Series({c: C[c]["latlng"][1] for c in codes})
border = sorted({tuple(sorted((a, b))) for a in codes for b in C[a].get("borders", []) if b in nodes.index})
yr = nodes.year_imp
PERIODS = [   # (이름, 시작, 끝, 색)
    ("1990년 전", -np.inf, 1989, "#3a3a3c"),
    ("1990~2013", 1990, 2013, "#7fa7e6"),
    ("2014~2016", 2014, 2016, "#2a6fdb"),
    ("2017~2019", 2017, 2019, "#e0752d"),
    ("2020~2023", 2020, 2023, "#b8336a"),
]


def color_of(y):
    for _, lo, hi, col in PERIODS:
        if lo <= y <= hi:
            return col
    return None


SNAPS = [2014, 2017, 2019, 2023]
fig, axes = plt.subplots(2, 2, figsize=(15, 6.6))
for ax, t in zip(axes.flat, SNAPS):
    done = yr <= t
    for a, b in border:
        both = done[a] and done[b]
        ax.plot([lon[a], lon[b]], [lat[a], lat[b]], color="#4a4a4a" if both else "#d8d8dc",
                lw=0.9 if both else 0.5, zorder=1 if not both else 2)
    no = ~done
    ax.scatter(lon[no], lat[no], s=14, facecolor="white", edgecolor="#b0b0b5", lw=0.7, zorder=3)
    for name, lo, hi, col in PERIODS:
        m = done & yr.between(lo, hi)
        ax.scatter(lon[m], lat[m], s=26, color=col, edgecolor="white", lw=0.4, zorder=4)
    n_ana = int((ana.year_imp <= t).sum())
    n_both = sum(done[a] and done[b] for a, b in border)
    ax.set_title(f"{t}년까지: 1990년 이후 도입 {n_ana}개국 (+1990년 전 7개국)  ·  둘 다 도입한 국경 쌍 {n_both}개",
                 loc="left", fontsize=11, color=INK)
    ax.set_xlim(-180, 180)
    ax.set_ylim(-50, 72)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
handles = [Line2D([], [], ls="", marker="o", ms=7, color=col, label=f"{name} 도입") for name, _, _, col in PERIODS]
handles += [Line2D([], [], ls="", marker="o", ms=6, markerfacecolor="white", markeredgecolor="#b0b0b5", label="그 해까지 미도입"),
            Line2D([], [], color="#4a4a4a", lw=1, label="국경, 둘 다 도입"),
            Line2D([], [], color="#d8d8dc", lw=1, label="국경, 하나 이상 미도입")]
fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.035), ncol=8, frameon=False, fontsize=9)
fig.suptitle("연도별 설탕세 도입 지도: 점 = 나라 (위도·경도), 선 = 육상 국경", x=0.01, ha="left",
             fontsize=13.5, fontweight="bold", color=INK)
fig.text(0.01, 0.005, f"{SRC}. 국경·위치: countries.json. 선은 '연결'이지 '영향'이 아님. 미도입 = 그 해까지 안 함",
         fontsize=8, color=MUTED)
fig.tight_layout(rect=(0, 0.08, 1, 0.94), h_pad=0.5)
fig.savefig(FIG / "stage3_도입지도_스냅샷.png", dpi=180)
plt.close(fig)
print("그림 3: " + ", ".join(f"{t}년 {int((ana.year_imp <= t).sum())}개국" for t in SNAPS))
print("저장: figures/stage3_전체_확산곡선.png, stage3_그룹별_확산곡선.png, stage3_도입지도_스냅샷.png")
