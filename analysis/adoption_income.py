"""
도입 여부 검사(1-2단계)에 소득 강건성 추가, 전 계층 한꺼번에
실행: python analysis/adoption_income.py   (2~5 다 끝난 뒤, 몇 초)

- 도입 여부 검사는 204개국 전부 섞으므로 소득 열도 204개국 전부 있어야 함
  → nodes.csv의 income_db는 도입국만 있어서 못 썼음. 수정(C)의 layers/income/income_by_year.csv로 붙임 (메모리에서만, nodes.csv 안 바꿈)
- 기준 연도를 하나로 고정함. 소득 계층(income_nodes.csv)처럼 '도입국은 도입한 해, 미도입국은 2023년'으로 하면
  등급을 재는 해가 도입 여부에 따라 달라져서, 도입 여부를 섞는 검사의 묶음 자체가 도입 여부에 기댐
  - income2016: 2016년 등급 (주). WHO 설탕세 권고 해, 도입이 몰린 2014~2019의 가운데
  - income2023: 2023년 등급 (확인용). 관찰 끝 해
- World Bank 등급이 없는 나라(2016: 쿡제도・니우에・세인트헬레나・바티칸・월리스푸투나 5개, 2023: + 베네수엘라)는
  'NA' 한 묶음으로 둠 (그 안에서만 섞임)
- basic 줄은 각 계층 adoption_*.csv와 같아야 함 (같은 함수・seed)
- 결과: analysis/adoption_income.csv (계층 × 섞는 방식 한 줄씩)
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))
from common import adoption_test, load_nodes  # noqa: E402

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
YEARS = {"income2016": 2016, "income2023": 2023}

nodes = load_nodes()
ib = pd.read_csv(L / "income" / "income_by_year.csv")
for col, y in YEARS.items():
    s = ib[ib.year == y].set_index("iso3").group.reindex(nodes.index)
    print(f"{col}: 등급 없음 {int(s.isna().sum())}개 {list(s[s.isna()].index)} → 'NA' 묶음")
    nodes[col] = s.fillna("NA")

rows = []
for name, path in LAYERS.items():
    edges = pd.read_csv(path)
    for shuffle in [None, *YEARS]:
        r = adoption_test(edges, nodes, strata=shuffle)
        rows.append(dict(layer=name, shuffle=shuffle or "basic", **r))
    print(f"{name:10s}", "  ".join(f"{x['shuffle']}={x['p']:.3f}" for x in rows[-3:]))

out = pd.DataFrame(rows)
out.to_csv(ROOT / "analysis" / "adoption_income.csv", index=False)
print(f"저장: analysis/adoption_income.csv ({len(out)}행)")
