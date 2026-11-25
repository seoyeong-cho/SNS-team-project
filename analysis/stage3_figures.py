"""
3단계 확산 경로 그림 (B, 서현). stage3_paths.py 다음에 실행
실행: python analysis/stage3_figures.py   (약 5초)
설명 문서: docs/analysis/stage3_paths.md

그림 1  figures/stage3_확산경로_예시_실제vs가짜.png
  언어 계층 아랍어 그룹 도입국(11개국)을 실제 연도 vs 가짜 세계 하나로 나란히
  가짜 세계 하나 = 1,000개 중 평균 간격이 가짜 평균에 가장 가까운 것 (같으면 앞 번호). 11/25 서영:
  예전엔 첫 번째(평균 4.7년)라 보통 가짜보다 퍼져 보여 실제와 차이가 과장됨 → 전형적인 하나로 바꿈
  화살표 = 같은 그룹에서 가장 최근에 먼저 도입한 나라 → 나중 나라 (같은 해 먼저 도입국이 여럿이면 알파벳 앞)
  평균 간격 p = 가짜 세계 1,000개 중 평균 간격이 실제보다 짧거나 같은 비율 (114개국 연도를 전체에서 섞음, seed 42)
그림 2  figures/stage3_경로수_실제vs가짜.png
  stage3_paths.py 결과(stage3_path_nulls.csv, stage3_path_comparison.csv)만 읽음. 새로 계산 안 함
  1~3년 간격 A→B→C 경로 수: 가짜 세계 1,000개 분포 + 실제 값, 언어・식민 × 전체 섞기・대륙 안 섞기

화살표는 '순서'이지 '영향'이 아님. 그림에도 그렇게 적음
"""
import json
import sys
from pathlib import Path

import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import FancyArrowPatch  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from common import R, SEED, load_nodes, use_font  # noqa: E402

A = ROOT / "analysis"
FIG = ROOT / "figures"
FIG1 = FIG / "stage3_확산경로_예시_실제vs가짜.png"
FIG2 = FIG / "stage3_경로수_실제vs가짜.png"
GROUP = "Arabic"
SHORT = {"ARE": "UAE", "SAU": "사우디"}   # 긴 이름 줄임 (파일럿 그림과 같게)

INK, MUTED, FIRST, ARROW, FAKE = "#1a1a1a", "#6b6b6b", "#2a6fdb", "#8a8a8a", "#c9c9c9"


def korean_names():
    rows = json.loads((ROOT / "data" / "raw" / "countries.json").read_text(encoding="utf-8"))
    names = {r["cca3"]: r.get("translations", {}).get("kor", {}).get("common", r["cca3"]) for r in rows}
    names.update(SHORT)
    return names


def parents(codes, years):
    """나라마다 같은 그룹에서 가장 최근에 먼저 도입한 나라 (없으면 None)"""
    out = {}
    for c in codes:
        earlier = [d for d in codes if years[d] < years[c]]
        if not earlier:
            out[c] = None
            continue
        latest = max(years[d] for d in earlier)
        out[c] = sorted(d for d in earlier if years[d] == latest)[0]
    return out


def mean_lag(codes, years):
    par = parents(codes, years)
    lags = [years[c] - years[p] for c, p in par.items() if p is not None]
    return float(np.mean(lags)), len(lags)


def draw_timeline(ax, codes, years, names, title):
    par = parents(codes, years)
    order = sorted(codes, key=lambda c: (years[c], names[c]))
    ypos = {c: i for i, c in enumerate(order)}
    for c, p in par.items():
        if p is None:
            continue
        rad = -0.25 if years[c] - years[p] > 2 else -0.35
        ax.add_patch(FancyArrowPatch((years[p], ypos[p]), (years[c], ypos[c]), arrowstyle="-|>", mutation_scale=11,
                                     color=ARROW, lw=1.3, connectionstyle=f"arc3,rad={rad}", shrinkA=6, shrinkB=6))
    for c in order:
        ax.scatter(years[c], ypos[c], s=70, color=FIRST if par[c] is None else INK, zorder=3)
        ax.text(years[c] + 0.35, ypos[c], names[c], va="center", fontsize=10, color=INK)
    lag, n = mean_lag(codes, years)
    ax.set_title(f"{title}\n화살표 {n}개 · 평균 {lag:.1f}년 뒤에 도입", loc="left", fontsize=11.5, color=INK)
    lo, hi = min(years.values()), max(years.values())
    ax.set_xlim(lo - 1, hi + 3.5)
    ax.set_ylim(-0.8, len(order) - 0.2)
    ax.set_yticks([])
    ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    ax.set_xlabel("도입 연도", color=MUTED)
    for s in ("left", "right", "top"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=MUTED)
    return lag


def fig1(nodes, names):
    edges = pd.read_csv(ROOT / "layers" / "language" / "layer_language_edges.csv")
    sub = edges[edges.group == GROUP]
    ac = list(nodes.index[nodes.in_analysis == 1])
    codes = sorted((set(sub.src) | set(sub.dst)) & set(ac))
    y_all = nodes.loc[ac, "year_imp"].to_numpy(int)
    idx = [ac.index(c) for c in codes]
    real = {c: int(nodes.loc[c, "year_imp"]) for c in codes}
    real_lag, _ = mean_lag(codes, real)

    rng = np.random.default_rng(SEED)
    fake_lags, fakes = [], []
    for k in range(R):
        ys = rng.permutation(y_all)
        fy = {c: int(ys[i]) for c, i in zip(codes, idx)}
        fakes.append(fy)
        fake_lags.append(mean_lag(codes, fy)[0])
    fake_lags = np.array(fake_lags)
    p = (np.sum(fake_lags <= real_lag) + 1) / (R + 1)
    k_show = int(np.argmin(np.abs(fake_lags - fake_lags.mean())))   # 평균에 가장 가까운 가짜 세계

    fig, axes = plt.subplots(1, 2, figsize=(13, 6.2))
    draw_timeline(axes[0], codes, real, names, f"실제 (아랍어권 {len(codes)}개국)")
    draw_timeline(axes[1], codes, fakes[k_show], names,
                  f"가짜 세계 하나 (114개국 연도를 섞음, 1,000개 중 평균에 가장 가까운 것)")
    fig.suptitle("확산 경로는 '순서'일 뿐: 실제가 가짜보다 촘촘한지 비교해야 한다", x=0.015, ha="left",
                 fontsize=15, fontweight="bold", color=INK)
    verdict = ("이 더 촘촘해 보이지만 우연 범위 안" if p >= 0.05 else "로 가짜보다 촘촘함")         if real_lag < fake_lags.mean() else "로 가짜보다 촘촘하지 않음"
    fig.text(0.015, 0.045, f"가짜 세계 {R:,}개의 평균은 {fake_lags.mean():.1f}년. 실제 {real_lag:.1f}년{verdict} (p = {p:.3f})",
             fontsize=11, color=INK)
    fig.text(0.015, 0.012, "화살표: 같은 언어권에서 가장 최근에 먼저 도입한 나라 → 나중 나라. 순서일 뿐, 영향을 줬다는 증거는 아님."
             "  파란 점: 그룹 안 첫 도입국. 에리트레아・튀니지 연도는 검증에서 '모름'", fontsize=9, color=MUTED)
    fig.tight_layout(rect=(0, 0.07, 1, 0.94))
    fig.savefig(FIG1, dpi=150)
    plt.close(fig)
    return dict(group=GROUP, n=len(codes), real_lag=round(real_lag, 2), fake_lag_mean=round(fake_lags.mean(), 2),
                p=round(float(p), 4), fake_shown=k_show + 1, fake_shown_lag=round(float(fake_lags[k_show]), 2))


def fig2():
    nulls = pd.read_csv(A / "stage3_path_nulls.csv")
    comp = pd.read_csv(A / "stage3_path_comparison.csv")
    comp = comp[comp.metric == "constrained_paths"].set_index(["layer", "scheme"])
    layers = [("language/language", "언어"), ("language/colony", "식민")]
    schemes = [("basic", "전체에서 섞기"), ("continent", "대륙 안에서만 섞기")]
    fig, axes = plt.subplots(2, 2, figsize=(12, 7.2), sharex="row")
    for r, (layer, lname) in enumerate(layers):
        for c, (scheme, sname) in enumerate(schemes):
            ax = axes[r, c]
            v = nulls[(nulls.layer == layer) & (nulls.scheme == scheme)].constrained_paths
            row = comp.loc[(layer, scheme)]
            ax.hist(v, bins=40, color=FAKE, edgecolor="white", linewidth=0.4)
            ax.axvline(row.actual_paths, color=INK, lw=2)
            ax.axvspan(row.fake_paths_p025, row.fake_paths_p975, color=FAKE, alpha=0.25, zorder=0)
            ax.text(row.actual_paths, ax.get_ylim()[1] * 0.92, f"  실제 {int(row.actual_paths):,}", color=INK,
                    fontsize=10, va="top")
            ax.set_title(f"{lname} · {sname}\n가짜 평균 {row.fake_paths_mean:,.0f}, p = {row.p_upper:.3f}",
                         loc="left", fontsize=11, color=INK)
            ax.set_yticks([])
            for s in ("left", "right", "top"):
                ax.spines[s].set_visible(False)
            ax.tick_params(colors=MUTED)
            if r == 1:
                ax.set_xlabel("1~3년 간격 A → B → C 경로 수", color=MUTED)
    fig.suptitle("연결을 따라 1~3년 간격으로 이어지는 경로: 실제(검은 선) vs 가짜 세계 1,000개(회색)", x=0.015,
                 ha="left", fontsize=14, fontweight="bold", color=INK)
    fig.text(0.015, 0.012, "옅은 띠: 가짜 세계 가운데 95%. p = 가짜가 실제보다 경로가 많거나 같은 비율. "
             "경로는 도입 순서이지 영향이 아님 (Bonferroni 2개 계층이면 기준 0.025)", fontsize=9, color=MUTED)
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    fig.savefig(FIG2, dpi=150)
    plt.close(fig)


def main():
    use_font()
    FIG.mkdir(exist_ok=True)
    nodes = load_nodes()
    res = fig1(nodes, korean_names())
    fig2()
    print("그림 1 아랍어권:", res)
    print(f"저장: {FIG1.relative_to(ROOT)}, {FIG2.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
