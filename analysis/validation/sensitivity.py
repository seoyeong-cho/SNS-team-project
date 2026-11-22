"""
V4 결과 안정성・민감도 (C, 11/22)
실행: python analysis/validation/sensitivity.py   (2~5 다 끝난 뒤, 1분 안팎)
계획: docs/PROJECT_README.md 8장 V4 / 설명: docs/analysis/validation.md 3장

1단계(stage1) 결과가 '계산 방식을 조금 바꿔도' 그대로인지 봄. 1단계와 같은 가짜 세계(seed 42, 1,000개, 전체에서 섞기)를 씀
  → ALL・그룹별 p는 각 계층 result_*.csv와 똑같이 나와야 함 (스크립트가 확인함)

1. 쌍 가중 vs 그룹 동일 가중 (그룹 2개 이상인 계층)
   - 쌍 가중 = 1단계 ALL: 쌍마다 평균 → 쌍이 많은 큰 그룹이 결과를 좌우
   - 그룹 동일 가중: 그룹마다 평균 연도 차이 → 그 평균들을 다시 평균 (그룹 하나 = 한 표)
   - 해석 그룹만 동일 가중: 도입국 5개 이상・쌍 10개 이상 그룹만
2. 큰 그룹 하나가 끌고 가는지: 그룹 하나씩 빼고 ALL 다시 (그 그룹에만 있는 쌍을 뺌)
3. 작은 그룹 안정성: 해석 그룹마다 나라 하나씩 빼고(그 그룹 쌍에서만) 다시 → gap_diff・p 범위, p가 0.05를 넘나드는지
4. 그룹별 BH 보정 (FDR 5%): 계층 안 그룹별 p, ALL 제외. 묶음 두 가지 (쌍 있는 모든 그룹 / 해석 그룹만)
   - BH 함수는 layers/language/supplementary_checks.py의 bh()와 같은 식
5. 효과 크기: gap_diff = 가짜 평균 − 실제 (년, +면 실제가 더 가까움), z = gap_diff / 가짜 표준편차,
   가짜 분포 2.5~97.5% 구간. 그림 figures/v4_순열분포.png

- 46개국 제외는 analysis/exclude_checked.py에 있어서 여기선 안 함
- 나라를 빼도 가짜 세계는 그대로 둠 (114개국 섞기). 빼는 건 '보는 쌍'만
- 결과: analysis/validation/sensitivity_summary.csv (계층 × 조건)
        analysis/validation/groups_<계층>.csv (그룹 2개 이상 계층)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "src"))
from common import R, SEED, _pair_index, _shuffles, load_nodes  # noqa: E402

L = ROOT / "layers"
OUT = ROOT / "analysis" / "validation"
LAYERS = {   # 이름: (엣지, 1단계 결과)
    "continent": ("region/layer_continent_edges.csv", "region/result_continent.csv"),
    "subregion": ("region/layer_subregion_edges.csv", "region/result_subregion.csv"),
    "border": ("region/layer_border_edges.csv", "region/result_border.csv"),
    "igo": ("region/layer_igo_edges.csv", "region/result_igo.csv"),
    "language": ("language/layer_language_edges.csv", "language/result_language.csv"),
    "colony": ("language/layer_colony_edges.csv", "language/result_colony.csv"),
    "income": ("income/layer_income_edges.csv", "income/result_income.csv"),
    "trade3": ("trade/layer_trade3_edges.csv", "trade/result_trade3.csv"),
    "trade5": ("trade/layer_trade_edges.csv", "trade/result_trade.csv"),
    "trade10": ("trade/layer_trade10_edges.csv", "trade/result_trade10.csv"),
}
MIN_ADOPTERS = 5   # 해석 기준: 도입국 5개 이상 (language.md・validation.md와 같음)
# PROJECT_README 8장은 '쌍 10개 이상'도 적었지만, 식민 colony_* 그룹은 종주국-식민지 별 모양이라
# 쌍 = 도입국 − 1 → 쌍 기준을 넣으면 서현의 fdr_colony.csv와 해석 그룹이 달라짐. 도입국 기준만 씀


def bh(p):
    """Benjamini–Hochberg 보정 p (q). NaN은 그대로"""
    p = np.asarray(p, float)
    q = np.full_like(p, np.nan)
    ok = ~np.isnan(p)
    m = ok.sum()
    if m == 0:
        return q
    order = np.argsort(p[ok])
    ranked = p[ok][order] * m / np.arange(1, m + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    tmp = np.empty(m)
    tmp[order] = np.minimum(ranked, 1)
    q[ok] = tmp
    return q


def pval(real, fake):
    """1단계와 같은 식: 가짜가 실제보다 작거나 같은 비율"""
    return (np.sum(fake <= real) + 1) / (len(fake) + 1)


def effect(real, fake):
    sd = fake.std(ddof=1)
    return dict(gap_real=round(float(real), 3), gap_fake_avg=round(float(fake.mean()), 3),
                gap_diff=round(float(fake.mean() - real), 3),
                z=round(float((fake.mean() - real) / sd), 2) if sd > 0 else np.nan,
                fake_lo95=round(float(np.quantile(fake, 0.025)), 3),
                fake_hi95=round(float(np.quantile(fake, 0.975)), 3),
                p=round(float(pval(real, fake)), 4))


nodes = load_nodes()
summary, dists = [], {}
for name, (epath, rpath) in LAYERS.items():
    edges = pd.read_csv(L / epath)
    ac, pos, e = _pair_index(edges, nodes)
    y = nodes.loc[ac, "year_imp"].to_numpy(float)

    # 쌍(중복 없이) 하나하나의 연도 차이: 실제 1개 + 가짜 R개 → 모든 통계를 이 표에서 계산
    e = e.assign(a=e.src.map(pos), b=e.dst.map(pos))
    e[["a", "b"]] = np.sort(e[["a", "b"]].to_numpy(), axis=1)
    uniq = e[["a", "b"]].drop_duplicates().reset_index(drop=True)
    col = {(a, b): k for k, (a, b) in enumerate(uniq.itertuples(index=False))}
    ia, ib = uniq.a.to_numpy(), uniq.b.to_numpy()
    real_g = np.abs(y[ia] - y[ib])
    fake_g = np.array([np.abs(ys[ia] - ys[ib]) for ys in _shuffles(y, R, SEED)])   # R × 쌍

    groups = {g: np.array(sorted({col[(a, b)] for a, b in zip(s.a, s.b)})) for g, s in e.groupby("group")}
    members = {g: sorted(set(ia[c]) | set(ib[c])) for g, c in groups.items()}
    interp = {g: len(members[g]) >= MIN_ADOPTERS for g in groups}

    def stat(cols):
        return real_g[cols].mean(), fake_g[:, cols].mean(1)

    # 1단계 ALL 그대로 (확인용)
    r_all, f_all = stat(np.arange(len(uniq)))
    dists[name] = (r_all, f_all)
    res = pd.read_csv(L / rpath).set_index("group")
    row = dict(layer=name, condition="pair_weighted", n_groups=len(groups), n_pairs=len(uniq), **effect(r_all, f_all))
    assert abs(row["p"] - res.loc["ALL", "p"]) < 1e-9, f"{name} ALL p가 result와 다름"
    summary.append(row)

    if len(groups) < 2:
        print(f"{name:10s} ALL p {row['p']:.3f}  (그룹 1개 → 동일 가중・그룹별 없음)")
        continue

    # 1. 그룹 동일 가중
    for cond, gs in [("group_equal", list(groups)), ("group_equal_interpret", [g for g in groups if interp[g]])]:
        if not gs:
            continue
        r = np.mean([real_g[groups[g]].mean() for g in gs])
        f = np.mean([fake_g[:, groups[g]].mean(1) for g in gs], axis=0)
        summary.append(dict(layer=name, condition=cond, n_groups=len(gs),
                            n_pairs=int(sum(len(groups[g]) for g in gs)), **effect(r, f)))

    # 그룹별
    rows = []
    for g, cols in groups.items():
        r, f = stat(cols)
        ef = effect(r, f)
        assert abs(ef["p"] - res.loc[g, "p"]) < 1e-9, f"{name} {g} p가 result와 다름"
        row = dict(layer=name, group=g, n_adopters=len(members[g]), n_pairs=len(cols), interpret=interp[g], **ef)

        # 2. 이 그룹을 빼면 ALL은? (다른 그룹에도 있는 쌍은 남김)
        others = np.unique(np.concatenate([c for h, c in groups.items() if h != g])) if len(groups) > 1 else np.array([], int)
        if len(others):
            ro, fo = stat(others)
            row.update(all_without_gap_diff=round(float(fo.mean() - ro), 3), all_without_p=round(float(pval(ro, fo)), 4))

        # 3. 나라 하나씩 빼기 (해석 그룹만, 그 그룹 쌍에서만)
        if interp[g]:
            diffs, ps, empty = [], [], []
            for c in members[g]:
                keep = cols[(ia[cols] != c) & (ib[cols] != c)]
                if len(keep) == 0:      # 별 모양 그룹(colony_*)에서 가운데 종주국을 빼면 쌍이 안 남음 → 건너뜀
                    empty.append(ac[c])
                    continue
                rk, fk = stat(keep)
                diffs.append(fk.mean() - rk)
                ps.append(pval(rk, fk))
            row.update(loo_n=len(ps), loo_skipped=";".join(empty),
                       loo_gap_diff_min=round(min(diffs), 3), loo_gap_diff_max=round(max(diffs), 3),
                       loo_p_min=round(min(ps), 4), loo_p_max=round(max(ps), 4),
                       loo_crosses_05=bool(min(ps) < 0.05 <= max(ps)))
        rows.append(row)

    gdf = pd.DataFrame(rows)
    # 4. BH
    gdf["q_bh_all_groups"] = np.round(bh(gdf.p), 4)
    gdf["q_bh_interpret_only"] = np.nan
    m = gdf.interpret.to_numpy()
    gdf.loc[m, "q_bh_interpret_only"] = np.round(bh(gdf.p[m]), 4)
    gdf.to_csv(OUT / f"groups_{name}.csv", index=False)

    s = [x for x in summary if x["layer"] == name]
    print(f"{name:10s} " + "  ".join(f"{x['condition']}={x['p']:.3f}" for x in s)
          + f"  | 그룹 {len(gdf)} (해석 {int(m.sum())}), p<0.05 {int((gdf.p < 0.05).sum())}"
          + f" → BH 후 {int((gdf.q_bh_all_groups < 0.05).sum())} / 해석만 {int((gdf.q_bh_interpret_only < 0.05).sum())}")

out = pd.DataFrame(summary)
out.to_csv(OUT / "sensitivity_summary.csv", index=False)
print(f"저장: analysis/validation/sensitivity_summary.csv ({len(out)}행), groups_<계층>.csv")

# 5. 순열분포 그림
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

# 글꼴: Pretendard (OFL, layers/income/fonts/). 설치 안 해도 저장소 파일로 똑같이 그려짐
for _f in (ROOT / "layers" / "income" / "fonts").glob("Pretendard-*.otf"):
    font_manager.fontManager.addfont(str(_f))
plt.rcParams["font.family"] = "Pretendard"
plt.rcParams["axes.unicode_minus"] = False
KO = dict(continent="대륙", subregion="소지역", border="국경", igo="지역기구", language="언어", colony="식민",
          income="소득", trade3="무역 k=3", trade5="무역 k=5", trade10="무역 k=10")

fig, axes = plt.subplots(2, 5, figsize=(17, 6.6), sharey=False)
for ax, (name, (r, f)) in zip(axes.flat, dists.items()):
    s = out[(out.layer == name) & (out.condition == "pair_weighted")].iloc[0]
    counts, _, _ = ax.hist(f, bins=40, color="#b8c4d6", edgecolor="white")
    ax.set_ylim(0, counts.max() * 1.6)   # 위쪽 여유 → 글상자가 막대를 안 가림
    ax.axvline(r, color="#c0392b", lw=2)
    ax.set_title(f"{KO[name]}  ({s.n_pairs}쌍)", loc="left", fontsize=11)
    right = r < np.median(f)   # 글자는 빨간 선 반대쪽에
    ax.text(0.98 if right else 0.02, 0.97, f"실제 {r:.2f}년\n가짜 평균 {f.mean():.2f}년\n차이 {s.gap_diff:+.2f}년, p {s.p:.3f}",
            transform=ax.transAxes, va="top", ha="right" if right else "left", fontsize=8.5,
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=1.5))
    ax.set_yticks([])
    for sp in ["top", "right", "left"]:
        ax.spines[sp].set_visible(False)
for ax in axes[1]:
    ax.set_xlabel("같은 그룹 도입국 쌍의 평균 도입 연도 차이 (년)", fontsize=8.5)
fig.suptitle("V4 순열분포: 가짜 세계 1,000개 (회색) vs 실제 (빨간 선). 선이 왼쪽 끝일수록 같은 그룹끼리 도입 시기가 우연보다 가까움",
             x=0.01, ha="left", fontsize=12)
fig.text(0.01, 0.01, "칸마다 x축 범위가 다름 (쌍 수가 적을수록 가짜 분포가 넓음) → 빨간 선 위치를 칸끼리 비교하지 말고 '차이(년)'와 p로 비교",
         ha="left", fontsize=9.5, color="#555555")
fig.tight_layout(rect=(0, 0.03, 1, 0.95))
fig.savefig(ROOT / "figures" / "v4_순열분포.png", dpi=150)
print("저장: figures/v4_순열분포.png")
