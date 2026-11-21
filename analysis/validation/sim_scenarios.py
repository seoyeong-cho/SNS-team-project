"""
V1: 정답 아는 가상 데이터로 순열검정 성능 확인 (B, 서현)
실행: python analysis/validation/sim_scenarios.py            (전체: 시나리오 6개 × 500세트, 가짜 세계 499개)
      python analysis/validation/sim_scenarios.py --n 50     (빠르게 확인용)
설명 문서: docs/analysis/validation.md  /  계획: docs/PROJECT_README.md 8장 V1

- 나라와 연결 구조(대륙・언어 계층 엣지)는 실제 그대로, 도입 연도만 가상으로 만듦
- 1990~2023 연 단위 이산시간 모형. 아직 도입 안 한 나라 i가 t년에 도입할 확률 h_it
  기본 확률 h0_t = 실제 t년 도입 수 / t년 시작 때 아직 안 한 나라 수 (1990년 전 도입국 7개는 빼고 197개국)
- 시나리오
  S0 영향 없음      h_it = h0_t
  S1 따라 함 (β)    h_it ∝ h0_t × (1 + β·E_it), E_it = 언어 계층으로 연결된 나라 중 t−3 ~ t−1년 도입국 있음
  S2 지역 공통 충격 h_it ∝ h0_t × exp(−(t − m_c)² / 2σ²), m_c = 실제 대륙별 도입 연도 중앙값, σ = 4
  S1・S2는 해마다 아직 안 한 나라 전체의 기대 도입 수가 h0_t × (남은 나라 수)가 되도록 정규화
  → β가 커져도 도입국 수는 늘지 않고 '누가' 언제 하는지만 바뀜 (도입국 수가 늘어 검출이 쉬워지는 효과 제거)
- 검정 (common.py 함수 그대로, 수정 안 함)
  cont_stage1        대륙 계층 1단계 (전체에서 섞기)
  lang_stage1        언어 계층 1단계 (전체에서 섞기)
  lang_stage1_cont   언어 계층 1단계 (대륙 안에서만 섞기)
  lang_follow        언어 계층 따라 함 1~3년 (전체에서 섞기)
  lang_follow_cont   언어 계층 따라 함 1~3년 (대륙 안에서만 섞기)
- 대륙 = countries.json region. nodes에 메모리에서만 붙임 (data/processed 안 바꿈)
- seed: 가상 데이터 k번째 = [42, 시나리오 번호, k], 가짜 세계는 common.SEED(42)

결과: analysis/validation/sim_rejection_rates.csv  시나리오 × 검정 유의 비율(α = 0.05) + 95% CI (Wilson)
      analysis/validation/sim_effect_sizes.csv     가상 데이터마다 효과 크기・p (실제 데이터 줄 포함, scenario = real)
      figures/v1_가상데이터_검출비율.png
시간: 전체 약 20~40분 (코어 수에 따라)
"""
import argparse
import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "src"))
from common import SEED, Y_MAX, Y_MIN, follow_test, load_nodes, stage1  # noqa: E402

OUT = ROOT / "analysis" / "validation"
FIG = ROOT / "figures" / "v1_가상데이터_검출비율.png"
R_SIM = 499          # 가짜 세계 개수 (계획: 시뮬레이션은 499, p 최소 0.002)
N_SIM = 500          # 시나리오마다 가상 데이터 세트 수
ALPHA = 0.05
SIGMA = 4.0          # S2 공통 충격 폭 (년)
BETAS = (0.5, 1, 2, 4)
SCENARIOS = [("S0", 0.0)] + [("S1", b) for b in BETAS] + [("S2", 0.0)]
TESTS = ["cont_stage1", "lang_stage1", "lang_stage1_cont", "lang_follow", "lang_follow_cont"]
YEARS = np.arange(Y_MIN, Y_MAX + 1)

# 워커 프로세스에서 쓰는 공용 데이터 (init에서 채움)
G = {}


def load_base():
    nodes = load_nodes()
    countries = json.loads((ROOT / "data" / "raw" / "countries.json").read_text(encoding="utf-8"))
    continent = {row["cca3"]: row["region"] for row in countries}
    nodes["continent"] = nodes.index.map(continent)
    if nodes.continent.isna().any():
        raise ValueError(f"대륙 없는 나라: {list(nodes.index[nodes.continent.isna()])}")
    cont_edges = pd.read_csv(ROOT / "layers" / "region" / "layer_continent_edges.csv")
    lang_edges = pd.read_csv(ROOT / "layers" / "language" / "layer_language_edges.csv")
    return nodes, cont_edges, lang_edges


def calibrate(nodes):
    """h0_t: 실제 연도별 도입 수 / 그해 시작 때 아직 안 한 나라 수 (1990년 전 도입국 제외)"""
    pre = (nodes.adopter == 1) & (nodes.year_imp < Y_MIN)
    at_risk = int((~pre).sum())
    counts = nodes.loc[nodes.in_analysis == 1, "year_imp"].value_counts()
    h0, left = [], at_risk
    for t in YEARS:
        c = int(counts.get(t, 0))
        h0.append(c / left)
        left -= c
    return np.array(h0), ~pre.to_numpy()


def init_worker():
    nodes, cont_edges, lang_edges = load_base()
    h0, risk = calibrate(nodes)
    iso = list(nodes.index)
    pos = {c: i for i, c in enumerate(iso)}
    n = len(iso)
    A = np.zeros((n, n), bool)
    pairs = lang_edges[["src", "dst"]].drop_duplicates()
    i, j = pairs.src.map(pos).to_numpy(), pairs.dst.map(pos).to_numpy()
    A[i, j] = A[j, i] = True
    cont = nodes.continent.to_numpy()
    peak = nodes[nodes.in_analysis == 1].groupby("continent").year_imp.median().to_dict()
    G.update(nodes=nodes, cont_edges=cont_edges, lang_edges=lang_edges, h0=h0, risk=risk, A=A,
             peak=np.array([peak[c] for c in cont]))


def simulate(scen, beta, rng):
    """가상 도입 연도 (도입 안 하면 nan). 1990년 전 도입국은 시뮬레이션에서 빠짐"""
    h0, risk, A, peak = G["h0"], G["risk"], G["A"], G["peak"]
    n = len(risk)
    year = np.full(n, np.nan)
    for k, t in enumerate(YEARS):
        open_ = risk & np.isnan(year)
        if not open_.any():
            break
        if scen == "S0":
            w = np.ones(n)
        elif scen == "S1":
            recent = (year >= t - 3) & (year <= t - 1)
            E = (A[:, recent].any(1)).astype(float)
            w = 1 + beta * E
        else:  # S2
            w = np.exp(-((t - peak) ** 2) / (2 * SIGMA ** 2))
        w_open = w[open_]
        h = np.zeros(n)
        if w_open.mean() > 0:
            h[open_] = np.minimum(1.0, h0[k] * w_open / w_open.mean())
        year[open_ & (rng.random(n) < h)] = t
    return year


def fake_nodes(year):
    """가상 연도로 바꾼 nodes (메모리에서만). 1990년 전 도입국은 원래 값 그대로, 분석 대상 아님"""
    nodes = G["nodes"].copy()
    pre = ~G["risk"]
    adopt = ~np.isnan(year)
    nodes["year_imp"] = np.where(pre, nodes.year_imp, year)
    nodes["adopter"] = ((pre & (nodes.adopter == 1)) | adopt).astype(int)
    nodes["in_analysis"] = adopt.astype(int)
    return nodes


def run_tests(nodes, r=R_SIM):
    ce, le = G["cont_edges"], G["lang_edges"]
    out = {}
    for name, edges, strata in [("cont_stage1", ce, None), ("lang_stage1", le, None),
                                ("lang_stage1_cont", le, "continent")]:
        s = stage1(edges, nodes, by_group=False, r=r, strata=strata).iloc[0]
        out[name] = dict(p=s.p, real=s.mean_gap_real, fake=s.mean_gap_fake_avg,
                         effect=round(s.mean_gap_fake_avg - s.mean_gap_real, 3))  # gap_diff (년), 클수록 가까움
    for name, strata in [("lang_follow", None), ("lang_follow_cont", "continent")]:
        f = follow_test(le, nodes, lo=1, hi=3, r=r, strata=strata)
        out[name] = dict(p=f["p"], real=f["share_real"], fake=f["share_fake_avg"],
                         effect=round(f["share_real"] - f["share_fake_avg"], 3))  # share_diff, 클수록 따라 함
    return out


def one(job):
    si, scen, beta, k = job
    rng = np.random.default_rng([SEED, si, k])
    nodes = fake_nodes(simulate(scen, beta, rng))
    res = run_tests(nodes)
    n_ad = int(nodes.in_analysis.sum())
    return [dict(scenario=scen, beta=beta, sim=k, test=t, n_adopters=n_ad, **v) for t, v in res.items()]


def wilson(x, n, z=1.96):
    p = x / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def plot(rates):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    have = {f.name for f in font_manager.fontManager.ttflist}
    plt.rcParams["font.family"] = next((f for f in ["Malgun Gothic", "AppleGothic", "NanumGothic"] if f in have),
                                       "DejaVu Sans")
    plt.rcParams["axes.unicode_minus"] = False
    label = {"cont_stage1": "대륙 1단계", "lang_stage1": "언어 1단계", "lang_stage1_cont": "언어 1단계 (대륙 안)",
             "lang_follow": "언어 따라 함 1~3년", "lang_follow_cont": "언어 따라 함 1~3년 (대륙 안)"}
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1.4, 1]})
    s1 = rates[rates.scenario.isin(["S0", "S1"])].copy()
    for t in TESTS:
        d = s1[s1.test == t].sort_values("beta")
        axes[0].errorbar(d.beta, d.rate, yerr=[d.rate - d.ci_low, d.ci_high - d.rate], marker="o", capsize=3,
                         label=label[t])
    axes[0].axhline(ALPHA, color="gray", ls="--", lw=1)
    axes[0].set(xlabel="β (S1 따라 함 세기, 0 = S0 영향 없음)", ylabel="유의 비율 (p < 0.05)",
                title="S0, S1: 언어 계층으로 따라 하게 만들었을 때", ylim=(0, 1.02))
    axes[0].legend(fontsize=8, loc="upper left")
    s2 = rates[rates.scenario == "S2"].set_index("test").loc[TESTS]
    x = np.arange(len(TESTS))
    axes[1].bar(x, s2.rate, yerr=[s2.rate - s2.ci_low, s2.ci_high - s2.rate], capsize=3, color="#888")
    axes[1].axhline(ALPHA, color="gray", ls="--", lw=1)
    axes[1].set_xticks(x, [label[t] for t in TESTS], rotation=30, ha="right", fontsize=8)
    axes[1].set(ylabel="유의 비율 (p < 0.05)", title=f"S2: 따라 함 없이 대륙별 시기만 다름 (σ = {SIGMA:g}년)",
                ylim=(0, 1.02))
    fig.tight_layout()
    FIG.parent.mkdir(exist_ok=True)
    fig.savefig(FIG, dpi=150)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=N_SIM, help="시나리오마다 가상 데이터 세트 수")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    args = ap.parse_args()

    t0 = time.time()
    init_worker()
    real = run_tests(G["nodes"])
    rows = [dict(scenario="real", beta=np.nan, sim=0, test=t, n_adopters=int(G["nodes"].in_analysis.sum()), **v)
            for t, v in real.items()]

    jobs = [(si, scen, beta, k) for si, (scen, beta) in enumerate(SCENARIOS) for k in range(args.n)]
    print(f"가상 데이터 {len(jobs)}세트 (시나리오 {len(SCENARIOS)}개 × {args.n}), 가짜 세계 {R_SIM}개, 워커 {args.workers}")
    with Pool(args.workers, initializer=init_worker) as pool:
        for i, res in enumerate(pool.imap(one, jobs, chunksize=4), 1):
            rows.extend(res)
            if i % 100 == 0:
                print(f"  {i}/{len(jobs)}  {time.time() - t0:.0f}초")

    eff = pd.DataFrame(rows)
    eff.to_csv(OUT / "sim_effect_sizes.csv", index=False)

    sim = eff[eff.scenario != "real"]
    out = []
    for (scen, beta, test), d in sim.groupby(["scenario", "beta", "test"], sort=False):
        x, n = int((d.p < ALPHA).sum()), len(d)
        lo, hi = wilson(x, n)
        out.append(dict(scenario=scen, beta=beta, test=test, n_sim=n, n_reject=x, rate=round(x / n, 3),
                        ci_low=round(lo, 3), ci_high=round(hi, 3), effect_mean=round(d.effect.mean(), 3),
                        n_adopters_mean=round(d.n_adopters.mean(), 1)))
    rates = pd.DataFrame(out)
    rates.to_csv(OUT / "sim_rejection_rates.csv", index=False)
    plot(rates)

    print(rates.to_string(index=False))
    print("실제 데이터 p:", {t: float(v["p"]) for t, v in real.items()})
    print(f"저장: {OUT / 'sim_rejection_rates.csv'}, {OUT / 'sim_effect_sizes.csv'}, {FIG}  ({time.time() - t0:.0f}초)")


if __name__ == "__main__":
    main()
