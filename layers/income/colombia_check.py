"""
콜롬비아 민감도: 콜롬비아(2023년 11월 시행)를 도입국으로 넣으면 1단계가 어떻게 바뀌나 (C, 11/22)
실행: python layers/income/colombia_check.py   (2~5 다 끝난 뒤, 30초 안팎)
설명: docs/layers/income.md '폐지・누락 국가 찾기'

- 콜롬비아는 DB 기준 시점(2023년 8월판) 뒤에 시행돼서 manual_adoptions.csv에 안 넣음 (11/22 서영 결정, #26)
  → 본 분석은 그대로 두고, 넣었을 때를 민감도로만 보여 줌
- nodes.csv는 안 바꿈. 메모리에서만 COL을 도입국으로 바꿈
  (year_imp 2023, in_analysis 1, income_db UMIC, health_obj 1, budget_year 0, source manual: make_nodes.py가 넣었을 때와 같은 값)
- 계층 10개 ALL 1단계, 가짜 세계 seed 42, 1,000개 (common.stage1 그대로)
- base 줄은 각 계층 result_*.csv ALL과 같아야 함 (스크립트가 확인)
결과: layers/income/colombia_check.csv (계층 × version)
"""
import sys
from pathlib import Path

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "src"))
from common import load_nodes, stage1  # noqa: E402

L = ROOT / "layers"
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

base = load_nodes()
assert base.loc["COL", "adopter"] == 0, "nodes.csv에 이미 COL이 도입국으로 있음"
with_col = base.copy()
with_col.loc["COL", ["adopter", "year_imp", "in_analysis", "income_db", "health_obj", "budget_year", "source"]] = \
    [1, 2023.0, 1, "UMIC", 1.0, 0.0, "manual"]
VERSIONS = {"base": base, "with_COL": with_col}

rows = []
for name, (epath, rpath) in LAYERS.items():
    edges = pd.read_csv(L / epath)
    for ver, nd in VERSIONS.items():
        r = stage1(edges, nd, by_group=False).iloc[0]
        rows.append(dict(layer=name, version=ver, n_adopters=int(r.n_adopters), n_pairs=int(r.n_pairs),
                         mean_gap_real=r.mean_gap_real, mean_gap_fake_avg=r.mean_gap_fake_avg, p=r.p))
    old = pd.read_csv(L / rpath).set_index("group").loc["ALL"]
    assert abs(rows[-2]["p"] - old.p) < 1e-9, f"{name} base p가 result와 다름"
    b, c = rows[-2], rows[-1]
    print(f"{name:10s} p {b['p']:.4f} → {c['p']:.4f}  (도입국 {b['n_adopters']} → {c['n_adopters']}, 쌍 {b['n_pairs']} → {c['n_pairs']})")

out = pd.DataFrame(rows)
out.to_csv(L / "income" / "colombia_check.csv", index=False)
print(f"저장: layers/income/colombia_check.csv ({len(out)}행)")
