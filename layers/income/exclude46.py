"""
연도 검증 대상 국가를 연도 비교에서 뺀 소득 계층 1단계
실행: python layers/income/exclude46.py
- excl46: year_check.csv 46개국 (A + C 합친 표. 먼저 merge_year_check.py) (문서 기준 결과)
- excl60: 위 46개국 + year_check_14.csv 14개국 (추가 의심 14개국까지 뺀 더 엄격한 확인)
- 대상은 in_analysis=0으로 바꿔 연도 비교(stage1·robustness)에서 제외 (연결 자체는 유지)
- 결과: result_income_excl{46,60}.csv, robustness_income_excl{46,60}.csv
- robustness는 analysis/exclude_checked.py의 income excl46・excl60 줄과 같은 값 (전 계층 비교는 그쪽).
  여기는 그룹별 1단계(result_*)를 docs/layers/income.md에 쓰려고 남겨 둠
"""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parents[1] / "src"))
from common import load_nodes, robustness, stage1  # noqa: E402

base = load_nodes()
edges = pd.read_csv(HERE / "layer_income_edges.csv")
c46 = pd.read_csv(HERE / "year_check.csv").iso3.unique()
c14 = pd.read_csv(HERE / "year_check_14.csv").iso3.unique()

for tag, checked in [("46", c46), ("60", list(c46) + list(c14))]:
    nodes = base.copy()
    print(f"\n=== excl{tag}: 검증 대상 {len(checked)}개국, 그중 분석 대상 {int(nodes.loc[checked, 'in_analysis'].sum())}")
    nodes.loc[checked, "in_analysis"] = 0
    print("남은 분석 도입국", int(nodes.in_analysis.sum()))
    res = stage1(edges, nodes)
    res.to_csv(HERE / f"result_income_excl{tag}.csv", index=False)
    print(res.to_string(index=False))
    rob = robustness(edges, nodes)
    rob.to_csv(HERE / f"robustness_income_excl{tag}.csv", index=False)
    print(rob.to_string(index=False))
