"""
소득 계층 (C 담당). 순서는 layers/region/make_layer.py와 같음
실행: python layers/income/preprocess.py   (income_nodes.csv 생성, 먼저 한 번)
      python layers/income/make_layer.py

그룹 = 소득 등급(L, LM, UM, H). 도입국은 도입한 해 등급, 미도입국은 2023년 등급 (preprocess.py 참고)
등급 없는 나라(NIU, VAT)는 그룹에서 빠짐 → 연결 없음
"""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.append(str(ROOT / "src"))
from common import (adoption_test, check_edges, groups_to_edges, layer_graph,  # noqa: E402
                    load_nodes, robustness, stage1, structure)

nodes = load_nodes()


def build(name, groups):
    groups.to_csv(HERE / f"layer_{name}_groups.csv", index=False)
    edges = groups_to_edges(groups, nodes)
    check_edges(edges, nodes)
    edges.to_csv(HERE / f"layer_{name}_edges.csv", index=False)
    print(f"[{name}]", structure(layer_graph(edges, nodes)))
    res = stage1(edges, nodes)
    res.to_csv(HERE / f"result_{name}.csv", index=False)
    print(res.to_string(index=False))
    rob = robustness(edges, nodes)
    rob.to_csv(HERE / f"robustness_{name}.csv", index=False)
    print(rob.to_string(index=False))
    adopt = pd.DataFrame([adoption_test(edges, nodes)])
    adopt.to_csv(HERE / f"adoption_{name}.csv", index=False)
    print(adopt.to_string(index=False), "\n")


inc = pd.read_csv(HERE / "income_nodes.csv")
build("income", inc.dropna(subset=["group"])[["iso3", "group"]])
