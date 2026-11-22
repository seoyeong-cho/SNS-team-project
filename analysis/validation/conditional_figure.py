"""
V2 그림 (A, 11/22): 계층마다 '전체에서 섞기' vs '대륙 안에서만 섞기' 나란히
실행: python analysis/validation/conditional_figure.py   (conditional_continent.py 다음, 몇 초)
설명: docs/analysis/validation.md 1장

- conditional_summary.csv(version = all)만 읽음. 검정 새로 안 함 → 결과 CSV 변화 없음
- x = 차이 (가짜 평균 − 실제 평균 도입 연도 차이, 년). 클수록 같은 그룹끼리 도입 시기가 우연보다 가까움
- 점 2개: 회색 = 전체에서 섞기(basic), 파랑 = 대륙 안에서만 섞기. 선으로 이음 → 대륙 시기 차이를 빼면 얼마나 줄어드나
- 읽기 글자는 validation.md 1장 표 '읽기' 열 그대로
결과: figures/v2_대륙안섞기.png
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "src"))
from common import use_font  # noqa: E402

use_font()
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#898781", "#e6e5e0", "#fcfcfb"
BASIC, CONT = "#a8a69f", "#2a6fdb"

# (계층, 이름, 읽기: validation.md 1장 표 그대로). 위에서부터: 남음 → 경계 → 대륙으로 설명됨 → 원래 없음
ROWS = [("colony", "식민", "남음"), ("language", "언어", "남음"),
        ("trade10", "무역 k = 10", "약하게, 경계"),
        ("igo", "지역기구", "대륙으로 설명됨"), ("border", "국경", "대륙으로 설명됨"),
        ("subregion", "소지역", "대륙으로 설명됨"),
        ("trade", "무역 k = 5", "원래 없음"), ("trade3", "무역 k = 3", "원래 없음"), ("income", "소득", "원래 없음")]
S = pd.read_csv(ROOT / "analysis" / "validation" / "conditional_summary.csv")
S = S[S.version == "all"].set_index("layer")


def pfmt(p):
    return f"p {p:.3f}" if p >= 0.001 else "p < 0.001"


fig, ax = plt.subplots(figsize=(10, 5.6), facecolor=SURF)
ax.set_facecolor(SURF)
n = len(ROWS)
for i, (lay, name, verdict) in enumerate(ROWS):
    y = n - 1 - i
    r = S.loc[lay]
    b, c = r.gap_diff_basic, r.gap_diff_continent
    strong = verdict == "남음"
    ax.plot([b, c], [y, y], color=CONT if strong else "#c9c8c2", lw=2, zorder=1, solid_capstyle="round")
    ax.scatter(b, y, s=70, color=BASIC, edgecolor=SURF, lw=1.5, zorder=3)
    ax.scatter(c, y, s=70, color=CONT, edgecolor=SURF, lw=1.5, zorder=3)
    ax.text(-1.05, y, name, ha="right", va="center", fontsize=10.5, color=INK, fontweight="bold" if strong else "normal")
    ax.text(2.15, y, f"{pfmt(r.p_basic)}  →  {pfmt(r.p_continent)}", ha="left", va="center", fontsize=9.5, color=INK2)
    ax.text(3.35, y, verdict, ha="left", va="center", fontsize=10, color=CONT if strong else INK2,
            fontweight="bold" if strong else "normal")
ax.axvline(0, color=MUTED, lw=1, zorder=0)
ax.text(-0.06, n - 0.35, "← 우연보다 멂", ha="right", va="bottom", fontsize=8.5, color=MUTED)
ax.text(0.06, n - 0.35, "우연보다 가까움 →", ha="left", va="bottom", fontsize=8.5, color=MUTED)
for x in [-1, 1, 2]:
    ax.axvline(x, color=GRID, lw=0.8, zorder=0)
ax.text(2.15, n - 0.35, "p: 전체 → 대륙 안", ha="left", va="bottom", fontsize=8.5, color=MUTED)
ax.set_xlim(-1, 4.6)
ax.set_ylim(-0.6, n - 0.1)
ax.set_xticks([-1, 0, 1, 2])
ax.set_yticks([])
for sp in ["top", "right", "left"]:
    ax.spines[sp].set_visible(False)
ax.spines["bottom"].set_bounds(-1, 2)
ax.spines["bottom"].set_color(MUTED)
ax.tick_params(axis="x", colors=MUTED)
ax.set_xlabel("같은 그룹 도입국 쌍이 우연보다 몇 년 더 가까운가 (가짜 평균 − 실제)", fontsize=9.5, color=INK2, x=0.33)
ax.scatter([], [], s=70, color=BASIC, label="전체에서 섞은 가짜 세계와 비교")
ax.scatter([], [], s=70, color=CONT, label="대륙 안에서만 섞은 가짜 세계와 비교")
ax.legend(loc="upper left", bbox_to_anchor=(-0.17, 1.13), ncol=2, frameon=False, fontsize=9.5, handletextpad=0.3, columnspacing=1.5)
fig.text(0.015, 0.965, "대륙 안에서만 섞어도 남는 건 식민・언어뿐: 지역기구・국경・소지역은 대륙별 시기 차이로 대부분 설명됨",
         fontsize=12.5, fontweight="bold", color=INK, va="top")
fig.text(0.015, 0.012, "V2. 1990~2023년 도입국, 가짜 세계 1,000개 (seed 42). p는 보정 전. 연도 확인 안 된 19개국 빼면 국경・무역은 전체 섞기부터 사라짐 (validation.md 1장)\n"
         "같은 그룹끼리 도입 시기가 우연보다 가까웠다는 뜻이지 따라 했다는 뜻이 아님. 자료: analysis/validation/conditional_summary.csv",
         fontsize=8, color=MUTED, va="bottom", linespacing=1.5)
fig.subplots_adjust(left=0.17, right=0.98, top=0.83, bottom=0.2)
out = ROOT / "figures" / "v2_대륙안섞기.png"
fig.savefig(out, dpi=200, facecolor=SURF)
print(f"저장: {out.relative_to(ROOT)}")
