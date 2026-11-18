"""
연도 검증 대상 46개국(year_check_A + year_check_C)을 연도 비교에서 뺀 소득 계층 1단계
실행: python layers/income/exclude46.py
- 46개국은 in_analysis=0으로 바꿔 연도 비교(stage1·robustness)에서 제외 (연결 자체는 유지)
- 결과: result_income_excl46.csv, robustness_income_excl46.csv
"""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parents[1] / "src"))
from common import load_nodes, robustness, stage1  # noqa: E402

nodes = load_nodes()
edges = pd.read_csv(HERE / "layer_income_edges.csv")
checked = pd.concat([pd.read_csv(HERE / f"year_check_{k}.csv") for k in "AC"]).iso3.unique()
print("검증 대상", len(checked), "개국, 그중 분석 대상", int(nodes.loc[checked, "in_analysis"].sum()))

nodes.loc[checked, "in_analysis"] = 0
print("남은 분석 도입국", int(nodes.in_analysis.sum()))
res = stage1(edges, nodes)
res.to_csv(HERE / "result_income_excl46.csv", index=False)
print(res.to_string(index=False))
rob = robustness(edges, nodes)
rob.to_csv(HERE / "robustness_income_excl46.csv", index=False)
print(rob.to_string(index=False))
