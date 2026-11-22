"""
언어・식민 계층 보조 검증 (B). make_layer.py 결과를 읽기만 하고, 결과는 전부 supplementary/에 저장
실행: python layers/language/make_layer.py 다음에 python layers/language/supplementary_checks.py

1. 영국 연결 제외: colony에서 colony_GBR, samecol_GBR를 뺀 순열검정 → 기존 colony와 비교
2. 그룹별 BH-FDR 보정: result_language.csv, result_colony.csv의 그룹별 p (검증 계획 V4와 같은 방식. V4 담당이 생기면 bh() 그대로 가져가면 됨)
3. 확산 곡선: 아랍어권 vs 스페인어권 (common.group_curve, 분모 = 언어권 전체 나라)
4. 2-1단계 미리보기: 다른 대륙 쌍만 1단계 + follow_test (최종본은 analysis/stage2_1.py에서 다섯 분야 다 모이면)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SUP = HERE / "supplementary"
sys.path.append(str(ROOT / "src"))
from common import (Y_MAX, Y_MIN, adoption_test, follow_test, group_curve,  # noqa: E402
                    load_nodes, robustness, stage1, use_font)

nodes = load_nodes()
C = {x["cca3"]: x for x in json.load(open(ROOT / "data" / "raw" / "countries.json", encoding="utf-8"))}
cont = {k: C[k]["region"] for k in nodes.index}
MIN_ADOPTERS = 5


def nodes_with_continent():
    n = nodes.copy()
    n["continent"] = n.index.map(cont)          # 메모리에서만
    return n


def layer_row(name, edges):
    """계층 전체(ALL) 비교표 한 줄"""
    a = stage1(edges, nodes, by_group=False).iloc[0]
    rob = robustness(edges, nodes).set_index("shuffle").p
    ad = adoption_test(edges, nodes)
    v2 = stage1(edges, nodes_with_continent(), by_group=False, strata="continent").iloc[0]
    return dict(layer=name, unique_pairs=len(edges[["src", "dst"]].drop_duplicates()),
                adopter_pairs=int(a.n_pairs), adopters_linked=int(a.n_adopters),
                gap_real=a.mean_gap_real, gap_fake=a.mean_gap_fake_avg,
                gap_diff=round(a.mean_gap_fake_avg - a.mean_gap_real, 2), p=a.p,
                p_income_db=rob["income_db"], p_budget_year=rob["budget_year"], p_health_obj=rob["health_obj"],
                gap_fake_continent=v2.mean_gap_fake_avg, p_continent=v2.p,
                adopt_same_real=ad["same_status_real"], adopt_same_fake=ad["same_status_fake_avg"], adopt_p=ad["p"])


# ---------- 1. 영국 연결 제외 ----------
def gbr_exclusion():
    e = pd.read_csv(HERE / "layer_colony_edges.csv")
    gbr = ["colony_GBR", "samecol_GBR"]
    e_no = e[~e.group.isin(gbr)]
    # 영국 그룹에만 있는 쌍 / 다른 그룹과 같이 있는 쌍 (같이 있으면 빼도 쌍은 남음)
    ac = set(nodes.index[nodes.in_analysis == 1])
    pairs = e.assign(ad=e.src.isin(ac) & e.dst.isin(ac), gb=e.group.isin(gbr))
    by_pair = pairs.groupby(["src", "dst"]).agg(ad=("ad", "first"), gb=("gb", "any"), other=("gb", lambda s: (~s).any()))
    share = by_pair[by_pair.ad]
    print(f"도입국 쌍 {len(share)}개 중 영국 그룹 포함 {int(share.gb.sum())}개 ({share.gb.mean():.1%}), "
          f"영국 그룹에만 있는 쌍 {int((share.gb & ~share.other).sum())}개")
    rows = [layer_row("colony (기본)", e), layer_row("colony 영국 연결 제외", e_no)]
    out = pd.DataFrame(rows)
    out.to_csv(SUP / "gbr_exclusion_colony.csv", index=False)
    stage1(e_no, nodes).to_csv(SUP / "result_colony_no_gbr.csv", index=False)
    e_no.to_csv(SUP / "layer_colony_no_gbr_edges.csv", index=False)
    print(out.to_string(index=False))
    return out


# ---------- 2. BH-FDR ----------
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


def fdr(name):
    """그룹별 p(ALL 제외)에 BH. 검정 묶음 두 가지: 쌍이 있는 모든 그룹 / 도입국 5개 이상 그룹만"""
    r = pd.read_csv(HERE / f"result_{name}.csv")
    g = r[(r.group != "ALL") & (r.n_pairs > 0)].copy()
    g["interpret"] = g.n_adopters >= MIN_ADOPTERS
    g["q_bh_all_groups"] = bh(g.p).round(4)
    g["q_bh_interpret_only"] = np.nan
    g.loc[g.interpret, "q_bh_interpret_only"] = bh(g.loc[g.interpret, "p"]).round(4)
    g["sig_raw"] = g.p < 0.05
    g["sig_bh_all_groups"] = g.q_bh_all_groups < 0.05
    g["sig_bh_interpret_only"] = g.q_bh_interpret_only < 0.05
    g.insert(0, "layer", name)
    g.to_csv(SUP / f"fdr_{name}.csv", index=False)
    return g


# ---------- 3. 확산 곡선 ----------
def curves():
    groups = pd.read_csv(HERE / "layer_language_groups.csv")
    out, info = [], []
    for lang, ko in [("Arabic", "아랍어권"), ("Spanish", "스페인어권")]:
        c = group_curve(groups, nodes, lang).assign(group=lang)
        out.append(c)
        mem = groups.loc[groups.group == lang, "iso3"]
        y = nodes.loc[mem, "year_imp"].dropna()
        y9 = y[(y >= Y_MIN) & (y <= Y_MAX)]
        info.append(dict(group=lang, label=ko, members=len(mem), adopters_by_2023=int((y <= Y_MAX).sum()),
                         adopters_1990_2023=len(y9), before_1990=int((y < Y_MIN).sum()),
                         first_year=int(y9.min()), median_year=float(y9.median()), last_year=int(y9.max()),
                         iqr_years=float(y9.quantile(.75) - y9.quantile(.25)),
                         final_pct=float(c.cum_pct.iloc[-1]),
                         members_list=" ".join(sorted(mem))))
    cur = pd.concat(out)
    cur.to_csv(SUP / "curve_arabic_spanish.csv", index=False)
    inf = pd.DataFrame(info)
    inf.to_csv(SUP / "curve_arabic_spanish_summary.csv", index=False)
    print(inf.drop(columns="members_list").to_string(index=False))
    plot_curves(cur, inf)


def plot_curves(cur, inf):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    use_font()
    plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#86868b",
                         "axes.labelcolor": "#424245", "xtick.color": "#6e6e73", "ytick.color": "#6e6e73",
                         "font.size": 10, "axes.unicode_minus": False})
    INK, MID, COL = "#1d1d1f", "#86868b", {"Arabic": "#2a6fdb", "Spanish": "#d9822b"}
    fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=150)
    for r in inf.itertuples():
        c = cur[cur.group == r.group]
        ax.step(c.year, c.cum_pct, where="post", color=COL[r.group], lw=2.2)
        # 선이 평평한 구간 위에 이름표 (선・점선과 안 겹치게)
        x, y = {"Spanish": (2002.3, 43), "Arabic": (2002.3, 8)}[r.group]
        ax.text(x, y, f"{r.label}  {r.adopters_by_2023}/{r.members}개국 도입 ({r.final_pct:.0f}%)",
                color=COL[r.group], fontsize=9.5, fontweight="bold")
        ax.axvline(r.median_year, color=COL[r.group], lw=1, ls=":", alpha=.8)
    ax.text(1990.6, 96, "점선 = 1990~2023 도입국의 도입 연도 중앙값\n"
            + "  ".join(f"{r.label} {r.median_year:.0f}" for r in inf.itertuples()),
            color=MID, fontsize=8.5, va="top")
    ax.set_xlim(Y_MIN, Y_MAX + .5)
    ax.set_ylim(0, 100)
    ax.set_ylabel("누적 도입 비율 (%, 분모 = 언어권 전체 나라)")
    ax.grid(axis="y", color="#e8e8ed", lw=.8)
    ax.set_title("아랍어권 vs 스페인어권 설탕세 누적 도입", loc="left", fontsize=12.5, fontweight="bold", color=INK)
    fig.text(.01, .01, "공용어 기준(Factbook 2026-01 + 보충). 분모 = 언어권 전체 나라(미도입 포함).\n"
             "곡선은 시기 비교용이며 나라 간 확산(인과)을 뜻하지 않음", fontsize=7.5, color=MID)
    fig.tight_layout(rect=(0, .07, 1, 1))
    fig.savefig(SUP / "curve_arabic_spanish.png")
    plt.close(fig)


# ---------- 4. 2-1단계 미리보기 ----------
def stage2_1_preview():
    """다른 대륙 쌍만 남겨서 1단계 + follow_test (창 1~1, 1~2, 1~3년)"""
    rows = []
    for name, f in [("language", "layer_language_edges.csv"), ("colony", "layer_colony_edges.csv")]:
        e = pd.read_csv(HERE / f)
        x = e[[cont[a] != cont[b] for a, b in zip(e.src, e.dst)]]
        s = stage1(x, nodes, by_group=False).iloc[0]
        for hi in (1, 2, 3):
            ft = follow_test(x, nodes, lo=1, hi=hi)
            rows.append(dict(layer=name, cross_pairs=len(x[["src", "dst"]].drop_duplicates()),
                             cross_adopter_pairs=int(s.n_pairs), cross_adopters=int(s.n_adopters),
                             gap_real=s.mean_gap_real, gap_fake=s.mean_gap_fake_avg, p_stage1=s.p,
                             **ft))
    out = pd.DataFrame(rows)
    out.to_csv(SUP / "stage2_1_preview.csv", index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    print("== 1. 영국 연결 제외"); gbr_exclusion()
    print("\n== 2. BH-FDR")
    f = pd.concat([fdr("language"), fdr("colony")])
    print(f[f.sig_raw | f.interpret][["layer", "group", "n_adopters", "n_pairs", "p", "q_bh_all_groups",
                                      "q_bh_interpret_only", "sig_raw", "sig_bh_all_groups",
                                      "sig_bh_interpret_only"]].to_string(index=False))
    print("\n== 3. 확산 곡선"); curves()
    print("\n== 4. 2-1단계 미리보기"); stage2_1_preview()
