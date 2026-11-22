"""
3단계 발표용 그림 2종: 전체 확산 곡선, 그룹별 확산 곡선 (C, 11/22)
실행: python layers/income/curves_maps.py   (2~5 다 끝난 뒤, 몇 초)
설명: docs/layers/income.md '3단계 그림'

그림 1  figures/stage3_전체_확산곡선.png
  nodes.csv in_analysis = 1 (1990~2023 도입 114개국) 연도별 누적 도입 수
  멕시코 2014년, WHO 권고 2016년 10월 표시, 2017~2019년 띠
그림 2  figures/stage3_그룹별_확산곡선.png
  서현의 layers/language/supplementary/curve_arabic_spanish.csv・_summary.csv 그대로 (새로 계산 안 함)
  분모 = 그룹 전체 나라 수 (미도입 포함, common.group_curve)
(도입 지도 스냅샷은 서영 layers/region/adoption_maps.py로 대체, 11/22 #28)

- 미도입 = '그 해까지 안 함'. 지도의 화살표・선은 '영향'이 아님
- 1990년 전 도입 7개국(BRA, DNK, FJI, MHL, NIU, NOR, STP)은 곡선에서 빠짐(분석 대상 밖)
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / "figures"
INK, MUTED, GRID, BAND, ACCENT = "#1d1d1f", "#6e6e73", "#e8e8ed", "#ececf1", "#2a6fdb"

# 글꼴: Pretendard (OFL, layers/income/fonts/). 설치 안 해도 저장소 파일로 똑같이 그려짐
for _f in (ROOT / "layers" / "income" / "fonts").glob("Pretendard-*.otf"):
    font_manager.fontManager.addfont(str(_f))
plt.rcParams["font.family"] = "Pretendard"
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
ax.text(2016.95, 118, "WHO 권고\n2016년 10월", ha="left", va="top", color=ACCENT, fontsize=9)
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
            label=f"{s.label}: {s.members}개국 중 {s.adopters_by_2023}개국 도입 (가운데 50%가 도입하는 데 {s.iqr_years:g}년)")
a, s = summ.loc["Arabic"], summ.loc["Spanish"]
ax.annotate(f"{a.label}: 중앙 {a.median_year:.0f}년\n가운데 50%가 도입하는 데 {a.iqr_years:g}년 (급격)",
            (2016.6, 11), xytext=(2003, 14), color=INK, fontsize=9, va="center",
            arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
ax.annotate(f"{s.label}: {s.first_year}년부터\n가운데 50%가 도입하는 데 {s.iqr_years:g}년 (점진)",
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

print("저장: figures/stage3_전체_확산곡선.png, stage3_그룹별_확산곡선.png")
