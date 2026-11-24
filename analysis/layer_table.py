"""
계층 비교표: 계층마다 네트워크 구조 지표를 한 줄씩 (D)
실행: python analysis/layer_table.py   (2~5 다 끝난 뒤, 몇 초)

- 구조 지표는 common.structure(layer_graph(...)) 그대로
  - 노드는 204개국 전부 (layer_graph가 nodes.csv 전체를 넣음) → 연결 없는 나라는 고립국
  - 엣지 = 중복 뺀 나라 쌍 수. 그룹을 여러 개 공유하는 쌍도 하나로 셈
    → 엣지 파일 줄 수와 다를 수 있음 (지역기구 1,620줄 → 1,483쌍, 언어 3,019줄 → 2,979쌍)
- 도입국 쌍(n_pairs)・연결된 도입국(n_adopters)은 각 계층 result_*.csv의 ALL 줄을 그대로 옮김 (새로 계산 안 함)
  → 1단계가 실제로 비교하는 쌍 수. 계층마다 크게 달라서 p를 바로 비교하면 안 되는 근거
- analysis 열: 기본 / 보조 (서현 layers/language/summary_language_colony.csv와 같은 방식)
  → 무역 k = 3・10은 보조 (k 민감도), 나머지는 기본. 무역 기본은 k = 5
- 결과: analysis/layer_table.csv
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))
from common import layer_graph, load_nodes, structure  # noqa: E402

L = ROOT / "layers"
# 계층 이름: (엣지 파일, 1단계 결과 파일, 기본・보조)
LAYERS = {
    "continent": ("region/layer_continent_edges.csv", "region/result_continent.csv", "기본"),
    "subregion": ("region/layer_subregion_edges.csv", "region/result_subregion.csv", "기본"),
    "border": ("region/layer_border_edges.csv", "region/result_border.csv", "기본"),
    "igo": ("region/layer_igo_edges.csv", "region/result_igo.csv", "기본"),
    "language": ("language/layer_language_edges.csv", "language/result_language.csv", "기본"),
    "colony": ("language/layer_colony_edges.csv", "language/result_colony.csv", "기본"),
    "income": ("income/layer_income_edges.csv", "income/result_income.csv", "기본"),
    "trade3": ("trade/layer_trade3_edges.csv", "trade/result_trade3.csv", "보조"),
    "trade5": ("trade/layer_trade_edges.csv", "trade/result_trade.csv", "기본"),
    "trade10": ("trade/layer_trade10_edges.csv", "trade/result_trade10.csv", "보조"),
}

nodes = load_nodes()
rows = []
for name, (edge_file, result_file, analysis) in LAYERS.items():
    edges = pd.read_csv(L / edge_file)
    st = structure(layer_graph(edges, nodes))
    allr = pd.read_csv(L / result_file).set_index("group").loc["ALL"]
    rows.append(dict(layer=name, analysis=analysis, **st,
                     adopters_linked=int(allr.n_adopters), adopter_pairs=int(allr.n_pairs)))

out = pd.DataFrame(rows)
out.to_csv(ROOT / "analysis" / "layer_table.csv", index=False)
print(out.to_string(index=False))
