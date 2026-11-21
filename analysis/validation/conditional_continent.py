"""
V2: 대륙 안에서만 섞기 (A, 지역기구・국경・소지역・무역・소득)
실행: python analysis/validation/conditional_continent.py   (1~5번 계층 스크립트 다 돌린 뒤)
설명 문서: docs/analysis/validation.md  /  계획: docs/PROJECT_README.md 8장 V2

- 대륙 = countries.json region (대륙 계층・서현의 V2와 같음). nodes에 메모리에서만 붙임 (data/processed 안 바꿈)
- 계층마다 stage1 basic(전체에서 섞기) vs strata="continent"(같은 대륙 도입국끼리만 섞기)를 같은 표에
  basic 유의 + continent 유의     → 대륙별 시기 차이를 넘어 그 계층 그룹끼리 시기가 묶임 (인과 아님)
  basic 유의 + continent 유의 아님 → 그 계층 효과는 대륙별 시기 차이로 대부분 설명됨
- 대륙 계층 자체는 제외 (대륙 안에서 섞으면 같은 대륙 쌍 연도 집합이 그대로 → 항상 p = 1)
- 언어・식민은 서현이 layers/language/v2_continent_*.csv로 끝냄 → 요약표에만 읽어서 같이 놓음
- 의심 국가(unsure46) 뺀 버전도 ALL만 같이 (국경・무역 효과가 이 나라들에 기댐, exclude_checked.md)

결과: analysis/validation/conditional_<계층>.csv (그룹별, 서현 v2_continent_*.csv와 같은 열)
      analysis/validation/conditional_summary.csv (계층 × 버전, ALL 줄만, 언어・식민 포함)
      analysis/validation/conditional_continent_counts.csv (대륙별 도입국 수, 검정력 참고)
시간: 약 10초
"""
import json
import sys
from pathlib import Path

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "src"))
from common import analysis_countries, load_nodes, stage1  # noqa: E402

L = ROOT / "layers"
OUT = ROOT / "analysis" / "validation"
OUT.mkdir(exist_ok=True)
MIN_ADOPTERS = 5   # 그룹 해석 기준 (서현 V2와 같음)
LAYERS = {
    "igo": L / "region" / "layer_igo_edges.csv",
    "border": L / "region" / "layer_border_edges.csv",
    "subregion": L / "region" / "layer_subregion_edges.csv",
    "trade3": L / "trade" / "layer_trade3_edges.csv",
    "trade": L / "trade" / "layer_trade_edges.csv",       # k = 5 (주 결과)
    "trade10": L / "trade" / "layer_trade10_edges.csv",
    "income": L / "income" / "layer_income_edges.csv",
}
DONE_BY_B = {"language": L / "language" / "v2_continent_language.csv",
             "colony": L / "language" / "v2_continent_colony.csv"}

C = {x["cca3"]: x for x in json.load(open(ROOT / "data" / "raw" / "countries.json", encoding="utf-8"))}
nodes = load_nodes()
nodes["continent"] = [C[k]["region"] for k in nodes.index]

t46 = pd.read_csv(L / "income" / "year_check.csv")
VERSIONS = {"all": [], "unsure46": list(t46[t46.status != "맞음"].iso3)}

# 대륙별 도입국 수 (적은 대륙은 섞을 경우의 수가 적어 검정력 낮음)
counts = []
for ver, drop in VERSIONS.items():
    nd = nodes.copy()
    nd.loc[drop, "in_analysis"] = 0
    c = nd.loc[analysis_countries(nd), "continent"].value_counts()
    counts += [dict(version=ver, continent=k, n_adopters=int(v)) for k, v in c.items()]
pd.DataFrame(counts).to_csv(OUT / "conditional_continent_counts.csv", index=False)


def compare(edges, nd, by_group):
    b = stage1(edges, nd, by_group=by_group)
    c = stage1(edges, nd, by_group=by_group, strata="continent")
    v = b.merge(c[["group", "mean_gap_fake_avg", "p"]], on="group", suffixes=("_basic", "_continent"))
    v["interpret"] = v.n_adopters >= MIN_ADOPTERS
    return v


summary = []
for name, path in LAYERS.items():
    edges = pd.read_csv(path)
    for ver, drop in VERSIONS.items():
        nd = nodes.copy()
        nd.loc[drop, "in_analysis"] = 0
        v = compare(edges, nd, by_group=(ver == "all"))
        if ver == "all":
            v.to_csv(OUT / f"conditional_{name}.csv", index=False)
        summary.append(dict(layer=name, version=ver, **v.iloc[0].drop(["group", "interpret"]).to_dict()))

for name, path in DONE_BY_B.items():   # 서현 결과 (all만). unsure46은 여기서 같은 방식으로 계산
    v = pd.read_csv(path)
    summary.append(dict(layer=name, version="all", **v.iloc[0].drop(["group", "interpret"]).to_dict()))
    nd = nodes.copy()
    nd.loc[VERSIONS["unsure46"], "in_analysis"] = 0
    edges = pd.read_csv(L / "language" / f"layer_{name}_edges.csv")
    v = compare(edges, nd, by_group=False)
    summary.append(dict(layer=name, version="unsure46", **v.iloc[0].drop(["group", "interpret"]).to_dict()))

s = pd.DataFrame(summary)
s["gap_diff_basic"] = (s.mean_gap_fake_avg_basic - s.mean_gap_real).round(2)
s["gap_diff_continent"] = (s.mean_gap_fake_avg_continent - s.mean_gap_real).round(2)
s = s[["layer", "version", "n_adopters", "n_pairs", "mean_gap_real",
       "mean_gap_fake_avg_basic", "gap_diff_basic", "p_basic",
       "mean_gap_fake_avg_continent", "gap_diff_continent", "p_continent"]]
s.to_csv(OUT / "conditional_summary.csv", index=False)
print(pd.DataFrame(counts).pivot(index="continent", columns="version", values="n_adopters").to_string())
print()
print(s.to_string(index=False))
for name in LAYERS:
    g = pd.read_csv(OUT / f"conditional_{name}.csv")
    g = g[(g.group != "ALL") & g.interpret]
    if len(g):
        print(f"\n[{name}] 그룹별 (도입국 {MIN_ADOPTERS}개 이상)")
        print(g.drop(columns="interpret").to_string(index=False))
