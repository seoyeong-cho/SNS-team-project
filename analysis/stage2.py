"""
2단계: 여러 분야 연결을 한꺼번에 놓고 겹침・각 분야 몫・공유 분야 수 (A)
실행: python analysis/stage2.py   (1~5번 계층 스크립트 다 돌린 뒤. README 재현 순서 참고)
설명 문서: docs/analysis/stage2.md

분야 6개 (언어・식민은 따로 셈. 겹침이 Jaccard 0.34라 따로 보는 게 정보가 많음, docs/analysis/stage2_1.md)
  continent(지역 = 대륙), igo(지역기구), language, colony, income, trade(서로 상위 5위)
  보조 계층(layers/language/supplementary/)은 안 씀

1. 나라 쌍 표 → analysis/stage2_pairs.csv
   204개국 모든 쌍(20,706) 한 줄씩: 분야별 연결 0/1 + 민감도용 subregion・border・trade3・trade10,
   공유 분야 수, 둘 다 분석 도입국(1990~2023)이면 도입 연도 차이
2. 겹침 표 → analysis/stage2_overlap.csv
   분야 × 분야: 공통 쌍 수, Jaccard, '행 분야 쌍 중 열 분야로도 연결된 비율'. 204개국 쌍 기준 / 도입국 쌍 기준
3. 각 분야 몫 → analysis/stage2_share.csv
   도입국 쌍(114개국, 6,441쌍)에서  연도 차이 = b0 + Σ b_k × (분야 k 연결) 최소제곱
   b_k < 0 = 다른 분야 연결을 같이 넣고도 그 분야로 연결된 쌍이 시기가 더 가까움
   p = 가짜 세계(1단계와 같은 섞기, seed 42, 1,000개)에서 b_k가 실제 이하인 비율 (한쪽, 작을수록 '묶임')
   → 쌍끼리 독립이 아니라 보통 회귀 p는 못 씀. 나라 단위로 연도를 섞어 그 문제를 피함 (QAP와 같은 생각)
   - 섞는 방식: basic + 강건성 3개(income_db, budget_year, health_obj 안에서만)
   - 모형 민감도: 대륙 → 소지역, 국경 추가, 무역 k = 3 / 10
   - 나라 빼기: excl46, unsure46 (analysis/exclude_checked.py와 같은 목록. 연결은 두고 연도 비교에서만 뺌)
     basic + 강건성 3개 모두
4. 공유 분야 수 → analysis/stage2_shared_count.csv
   도입국 쌍을 공유 분야 수(0, 1, 2, 3, 4+)로 나눠 평균 연도 차이 vs 가짜 세계. all / excl46 / unsure46
5. 나라 빼기 비교 기준 → analysis/stage2_exclude_random.csv
   excl46・unsure46과 같은 수의 도입국을 무작위로 200번 빼서 각 분야 몫 다시 (반복마다 가짜 세계 300개, seed 0)
   rand_share_weaker = 무작위로 뺐을 때 계수가 실제 이상(효과 같거나 약함)인 비율. 작으면 뺀 나라들이 그 효과를 받치던 것

해석: 유의해도 '연결된 쌍끼리 시기가 묶임'까지. 따라 했다(확산)는 2-1단계・추가 검증(V1~V3)과 같이 봄
시간: 약 5초
"""
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))
from common import R, SEED, STRATA, _shuffles, _strata_labels, analysis_countries, load_nodes  # noqa: E402

L = ROOT / "layers"
OUT = ROOT / "analysis"
MAIN = ["continent", "igo", "language", "colony", "income", "trade"]
FILES = {
    "continent": L / "region" / "layer_continent_edges.csv",
    "igo": L / "region" / "layer_igo_edges.csv",
    "language": L / "language" / "layer_language_edges.csv",
    "colony": L / "language" / "layer_colony_edges.csv",
    "income": L / "income" / "layer_income_edges.csv",
    "trade": L / "trade" / "layer_trade_edges.csv",
    # 민감도용
    "subregion": L / "region" / "layer_subregion_edges.csv",
    "border": L / "region" / "layer_border_edges.csv",
    "trade3": L / "trade" / "layer_trade3_edges.csv",
    "trade10": L / "trade" / "layer_trade10_edges.csv",
}
MODELS = {   # 모형 이름 → 넣는 분야
    "main": MAIN,
    "subregion": ["subregion" if k == "continent" else k for k in MAIN],
    "border_added": MAIN + ["border"],
    "trade3": ["trade3" if k == "trade" else k for k in MAIN],
    "trade10": ["trade10" if k == "trade" else k for k in MAIN],
}

nodes = load_nodes()

# ---------- 1. 나라 쌍 표 ----------
codes = sorted(nodes.index)
pairs = pd.DataFrame(list(combinations(codes, 2)), columns=["src", "dst"])
key = pairs.src + "-" + pairs.dst
for name, path in FILES.items():
    e = pd.read_csv(path)[["src", "dst"]].drop_duplicates()
    assert (e.src < e.dst).all(), f"{name}: src < dst 아님"
    pairs[name] = key.isin(set(e.src + "-" + e.dst)).astype(int)
    assert pairs[name].sum() == len(e), f"{name}: nodes.csv 밖 코드"
pairs["n_shared"] = pairs[MAIN].sum(axis=1)
ac = set(analysis_countries(nodes))
pairs["both_adopters"] = (pairs.src.isin(ac) & pairs.dst.isin(ac)).astype(int)
y = nodes.year_imp
pairs["gap"] = np.where(pairs.both_adopters == 1, (pairs.src.map(y) - pairs.dst.map(y)).abs(), np.nan)
pairs.to_csv(OUT / "stage2_pairs.csv", index=False)
print(f"나라 쌍 {len(pairs):,}, 도입국 쌍 {int(pairs.both_adopters.sum()):,}")
print("분야별 연결 쌍 (전체 / 도입국끼리)")
for k in FILES:
    print(f"  {k:10s} {pairs[k].sum():5d} / {pairs.loc[pairs.both_adopters == 1, k].sum():5d}")

# ---------- 2. 겹침 표 ----------
rows = []
for base, sub in [("all_pairs", pairs), ("adopter_pairs", pairs[pairs.both_adopters == 1])]:
    for a in MAIN:
        for b in MAIN:
            both = int((sub[a] & sub[b]).sum())
            union = int((sub[a] | sub[b]).sum())
            rows.append(dict(base=base, row=a, col=b, n_row=int(sub[a].sum()), n_both=both,
                             jaccard=round(both / union, 3) if union else np.nan,
                             share_of_row=round(both / sub[a].sum(), 3) if sub[a].sum() else np.nan))
overlap = pd.DataFrame(rows)
overlap.to_csv(OUT / "stage2_overlap.csv", index=False)
print("\n[겹침 Jaccard, 204개국 쌍]")
print(overlap[overlap.base == "all_pairs"].pivot(index="row", columns="col", values="jaccard").loc[MAIN, MAIN].to_string())


# ---------- 3. 각 분야 몫 ----------
def year_check_lists():
    t46 = pd.read_csv(L / "income" / "year_check.csv")
    return {"all": [], "excl46": list(t46.iso3), "unsure46": list(t46[t46.status != "맞음"].iso3)}


def share_fit(layers, nd, strata=None, r=R, seed=SEED):
    """도입국 쌍에서 연도 차이 ~ 분야 연결 최소제곱 + 가짜 세계 p. 분야마다 한 줄"""
    ad = list(analysis_countries(nd))
    pos = {c: i for i, c in enumerate(ad)}
    sub = pairs[pairs.src.isin(pos) & pairs.dst.isin(pos)]
    i, j = sub.src.map(pos).to_numpy(), sub.dst.map(pos).to_numpy()
    X = np.column_stack([np.ones(len(sub))] + [sub[k].to_numpy(float) for k in layers])
    P = np.linalg.pinv(X)                      # b = P @ gap (X는 고정, 연도만 섞임)
    yy = nd.loc[ad, "year_imp"].to_numpy(float)
    real = P @ np.abs(yy[i] - yy[j])
    fake = np.array([P @ np.abs(ys[i] - ys[j]) for ys in _shuffles(yy, r, seed, _strata_labels(nd, ad, strata))])
    out = []
    for n, k in enumerate(layers, start=1):
        out.append(dict(layer=k, n_pairs_linked=int(sub[k].sum()), coef=round(real[n], 3),
                        coef_fake_avg=round(fake[:, n].mean(), 3),
                        p=round((np.sum(fake[:, n] <= real[n]) + 1) / (r + 1), 4)))
    return pd.DataFrame(out), len(ad), len(sub), round(real[0], 3)


rows = []
lists = year_check_lists()
runs = [("main", "all", s) for s in [None, *STRATA]]
runs += [(m, "all", None) for m in MODELS if m != "main"]
runs += [("main", v, None) for v in lists if v != "all"]
runs += [("main", v, s) for v in lists if v != "all" for s in STRATA]   # 나라 빼고 + 강건성
for model, ver, strata in runs:
    nd = nodes.copy()
    nd.loc[lists[ver], "in_analysis"] = 0
    res, n_ad, n_pairs, b0 = share_fit(MODELS[model], nd, strata)
    res.insert(0, "intercept", b0)
    res.insert(0, "n_adopter_pairs", n_pairs)
    res.insert(0, "n_adopters", n_ad)
    res.insert(0, "shuffle", strata or "basic")
    res.insert(0, "version", ver)
    res.insert(0, "model", model)
    rows.append(res)
share = pd.concat(rows, ignore_index=True)
share.to_csv(OUT / "stage2_share.csv", index=False)
print("\n[각 분야 몫: 연도 차이 회귀 계수 (음수 = 시기 가까움), p]")
wide = share.assign(cell=share.coef.map("{:+.2f}".format) + " (" + share.p.map("{:.3f}".format) + ")")
wide["run"] = wide.model + "/" + wide.version + "/" + wide.shuffle
print(wide.pivot(index="run", columns="layer", values="cell").reindex(columns=MAIN + ["subregion", "border", "trade3", "trade10"])
      .dropna(axis=1, how="all").fillna("").loc[wide.run.unique()].to_string())

# ---------- 4. 공유 분야 수 ----------
def shared_count(nd):
    ad = list(analysis_countries(nd))
    pos = {c: i for i, c in enumerate(ad)}
    sub = pairs[pairs.src.isin(pos) & pairs.dst.isin(pos)]
    i, j = sub.src.map(pos).to_numpy(), sub.dst.map(pos).to_numpy()
    bins = sub.n_shared.clip(upper=4).to_numpy()
    yy = nd.loc[ad, "year_imp"].to_numpy(float)

    def means(ys):
        g = np.abs(ys[i] - ys[j])
        return np.array([g[bins == b].mean() for b in range(5)])

    real = means(yy)
    fake = np.array([means(ys) for ys in _shuffles(yy)])
    return pd.DataFrame(dict(n_shared=["0", "1", "2", "3", "4+"], n_pairs=[int((bins == b).sum()) for b in range(5)],
                             mean_gap_real=real.round(2), mean_gap_fake_avg=fake.mean(0).round(2),
                             p=((np.sum(fake <= real, axis=0) + 1) / (R + 1)).round(4)))


cnts = []
for ver, drop in lists.items():
    nd = nodes.copy()
    nd.loc[drop, "in_analysis"] = 0
    cnts.append(shared_count(nd).assign(version=ver))
cnt = pd.concat(cnts, ignore_index=True)
cnt = cnt[["version"] + [c for c in cnt.columns if c != "version"]]
cnt.to_csv(OUT / "stage2_shared_count.csv", index=False)
print("\n[공유 분야 수별 평균 연도 차이]")
print(cnt.to_string(index=False))

# ---------- 5. 나라 빼기 비교 기준: 같은 수를 무작위로 뺐을 때 ----------
# exclude_checked.py와 같은 방식. 도입국이 줄어 검정력이 떨어지는 효과 vs 그 나라들이 효과를 만들던 효과
# 무작위 쪽은 반복마다 가짜 세계 RAND_R개라 p 눈금이 약 1/300 → rand_share_p05는 대략으로만 읽기
RAND, RAND_R, RAND_SEED = 200, 300, 0
real_share = share[(share.model == "main") & (share.shuffle == "basic")].set_index(["version", "layer"])
ac_all = list(analysis_countries(nodes))
rng = np.random.default_rng(RAND_SEED)
rand_rows = []
print("\n[나라 빼기 vs 같은 수 무작위로 빼기 (main, basic)]")
for ver, drop in lists.items():
    if not drop:
        continue
    sims = []
    for _ in range(RAND):
        nd = nodes.copy()
        nd.loc[list(rng.choice(ac_all, len(drop), replace=False)), "in_analysis"] = 0
        sims.append(share_fit(MAIN, nd, r=RAND_R)[0].set_index("layer"))
    for k in MAIN:
        c = np.array([s.loc[k, "coef"] for s in sims])
        p = np.array([s.loc[k, "p"] for s in sims])
        rr = real_share.loc[(ver, k)]
        rand_rows.append(dict(version=ver, layer=k, n_drop=len(drop), coef=rr.coef, p=rr.p,
                              rand_coef_median=round(float(np.median(c)), 3),
                              rand_share_p05=round(float(np.mean(p < 0.05)), 2),
                              rand_share_weaker=round(float(np.mean(c >= rr.coef)), 2)))
rand_df = pd.DataFrame(rand_rows)
rand_df.to_csv(OUT / "stage2_exclude_random.csv", index=False)
print(rand_df.to_string(index=False))
