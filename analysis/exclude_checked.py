"""
연도가 의심스러운 나라를 뺀 1단계・강건성, 전 계층 한꺼번에
실행: python analysis/exclude_checked.py

- 본 분석은 World Bank DB 연도 그대로. 연도 검증 표는 nodes.csv에 반영하지 않음 (docs/layers/income.md)
- 대신 검증 대상 나라를 연도 비교에서 빼고(in_analysis = 0, 연결은 유지) 결론이 유지되는지 봄
  - all   : 빼지 않음 (각 계층 result_*.csv의 ALL과 같음)
  - excl46: layers/income/year_check.csv 46개국 (A + C 합친 표. 먼저 merge_year_check.py)
  - excl60: 위 + layers/income/year_check_14.csv 14개국
  - unsure46, unsure60: 위 표에서 status가 '맞음'이 아닌 나라만 (수정・모름・설탕세아님). 검증으로 맞다고 확인된 나라는 남김
  - 46개국은 '연도가 틀린 나라'가 아니라 예산법 연도 의심(budget_year = 1) 50개국 중 검증한 46개국 (27개국은 맞음)
- 비교 기준: 같은 수의 도입국을 무작위로 뺐을 때 (RAND번). 도입국이 줄어 검정력이 떨어지는 효과와,
  그 나라들이 효과를 만들던 효과를 구분하려고 → analysis/exclude_checked_random.csv
  - 무작위 쪽은 반복마다 가짜 세계 RAND_R(300)개라 p 눈금이 약 1/300. 실제 p(1000개)와 같은 잣대가 아님
    → rand_share_p05는 '무작위로 빼도 p < 0.05가 나오는 비율' 정도로만 읽기
- 도입 여부 검사는 연도를 안 쓰므로 여기서 다시 돌리지 않음
- 결과: analysis/exclude_checked.csv (계층 × 버전 × 섞는 방식 한 줄씩)
- 시간: 약 40초 (대부분 무작위 비교: 4버전 × 10계층 × 200회 × 가짜 세계 300)
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))
import numpy as np  # noqa: E402
from common import load_nodes, robustness, stage1  # noqa: E402

L = ROOT / "layers"
LAYERS = {
    "continent": L / "region" / "layer_continent_edges.csv",
    "subregion": L / "region" / "layer_subregion_edges.csv",
    "border": L / "region" / "layer_border_edges.csv",
    "igo": L / "region" / "layer_igo_edges.csv",
    "language": L / "language" / "layer_language_edges.csv",
    "colony": L / "language" / "layer_colony_edges.csv",
    "income": L / "income" / "layer_income_edges.csv",
    "trade3": L / "trade" / "layer_trade3_edges.csv",
    "trade5": L / "trade" / "layer_trade_edges.csv",
    "trade10": L / "trade" / "layer_trade10_edges.csv",
}

RAND, RAND_R, RAND_SEED = 200, 300, 0   # 무작위 제외 반복 수, 그 안의 가짜 세계 수, seed

base = load_nodes()
t46 = pd.read_csv(L / "income" / "year_check.csv")
t14 = pd.read_csv(L / "income" / "year_check_14.csv")
c46, c14 = list(t46.iso3), list(t14.iso3)
u46 = list(t46[t46.status != "맞음"].iso3)
u14 = list(t14[t14.status != "맞음"].iso3)
VERSIONS = {"all": [], "excl46": c46, "excl60": c46 + c14, "unsure46": u46, "unsure60": u46 + u14}

rows = []
for ver, drop in VERSIONS.items():
    nodes = base.copy()
    nodes.loc[drop, "in_analysis"] = 0
    n_left = int(nodes.in_analysis.sum())
    print(f"\n=== {ver}: 뺀 나라 {len(drop)}, 남은 분석 도입국 {n_left}")
    for name, path in LAYERS.items():
        edges = pd.read_csv(path)
        rob = robustness(edges, nodes)
        rob.insert(0, "n_adopters", n_left)
        rob.insert(0, "version", ver)
        rob.insert(0, "layer", name)
        rows.append(rob)
        print(f"{name:10s}", "  ".join(f"{s}={p:.3f}" for s, p in zip(rob.shuffle, rob.p)))

out = pd.concat(rows, ignore_index=True)
out.to_csv(ROOT / "analysis" / "exclude_checked.csv", index=False)


# ---------- 비교 기준: 같은 수를 무작위로 뺐을 때 ----------
def gap_diff(edges, drop, r):
    """(가짜 평균 - 실제 평균 연도 차, p). 클수록 같은 그룹끼리 시기가 가까움"""
    nodes = base.copy()
    nodes.loc[drop, "in_analysis"] = 0
    a = stage1(edges, nodes, by_group=False, r=r).set_index("group").loc["ALL"]
    return a.mean_gap_fake_avg - a.mean_gap_real, a.p


ac = base.index[base.in_analysis == 1]
rng = np.random.default_rng(RAND_SEED)
rand_rows = []
print("\n=== 무작위 제외 비교 (basic)")
for ver, drop in VERSIONS.items():
    if not drop:
        continue
    draws = [list(rng.choice(ac, len(drop), replace=False)) for _ in range(RAND)]
    for name, path in LAYERS.items():
        edges = pd.read_csv(path)
        d_real, p_real = gap_diff(edges, drop, 1000)
        sims = np.array([gap_diff(edges, d, RAND_R) for d in draws])
        rand_rows.append(dict(layer=name, version=ver, n_drop=len(drop), gap_diff=round(d_real, 2), p=p_real,
                              rand_gap_diff_median=round(float(np.median(sims[:, 0])), 2),
                              rand_share_p05=round(float(np.mean(sims[:, 1] < 0.05)), 2),
                              rand_share_below=round(float(np.mean(sims[:, 0] <= d_real)), 2)))
        r = rand_rows[-1]
        print(f"{ver:9s}{name:10s} 실제 {r['gap_diff']:5.2f} (p {p_real:.3f}) | 무작위 중앙 {r['rand_gap_diff_median']:5.2f},"
              f" 무작위 중 p<0.05 {r['rand_share_p05']:.2f}, 무작위가 이보다 작을 확률 {r['rand_share_below']:.2f}")
pd.DataFrame(rand_rows).to_csv(ROOT / "analysis" / "exclude_checked_random.csv", index=False)
