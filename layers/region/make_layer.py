"""
지역 계층 (A 담당). 대륙 계층은 완성된 예시 → 다른 분야도 이 순서 그대로 따라 하면 됨
실행: python layers/region/make_layer.py

순서
1. 원본에서 나라-그룹 표 만들기 → layer_<이름>_groups.csv
2. 투영 → layer_<이름>_edges.csv
3. 제출 전 체크
4. 계층 구조 지표 + 1단계 → result_<이름>.csv
5. 강건성 (다른 요인 거른 가짜 세계) → robustness_<이름>.csv
6. 도입 여부 검사 (미도입국까지, 같이 하거나 같이 안 하나) → adoption_<이름>.csv
"""
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.append(str(ROOT / "src"))
from common import (adoption_test, check_edges, groups_to_edges, layer_graph,  # noqa: E402
                    load_nodes, robustness, stage1, structure)

nodes = load_nodes()
C = {x["cca3"]: x for x in json.load(open(ROOT / "data" / "raw" / "countries.json", encoding="utf-8"))}


def build(name, groups=None, edges=None):
    """groups(나라-그룹 표)를 주면 투영해서 엣지를 만들고, 쌍으로 정의되는 계층은 edges를 바로 줌"""
    if edges is None:
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


# 대륙 (예시, 완성)
continent = pd.DataFrame({"iso3": nodes.index, "group": [C[k]["region"] for k in nodes.index]})
build("continent", continent)

# 소지역
subregion = pd.DataFrame({"iso3": nodes.index,
                          "group": [C[k].get("subregion") or C[k]["region"] for k in nodes.index]})
build("subregion", subregion)

# 국경: 그룹이 아니라 쌍이라 countries.json borders로 엣지를 직접 만듦 (group = border)
# nodes.csv에 없는 이웃(예: 영토)은 빼고, 양쪽 표기가 한쪽만 있어도 쌍 하나로 셈
border = sorted({tuple(sorted((a, b))) for a in nodes.index for b in C[a].get("borders", [])
                 if b in nodes.index and a != b})
border = pd.DataFrame(border, columns=["src", "dst"]).assign(group="border")
build("border", edges=border)

# 지역기구: 주요 지역통합기구 15개 (파일럿 임시 목록과 같은 기구). 전 세계 기구(UN・WHO 등)와
# 대륙 전체 기구(AU・OAS)는 뺌. COW 기구 335개를 다 쓰면 나라 쌍 86%가 연결돼서 검정이 의미 없음
# 회원 = 1990~2023년 중 한 번이라도 정회원(COW 값 1). 준회원(2)・옵서버(3)는 제외
# 2014년까지는 COW IGO v3, 2015년 이후 가입과 COW 오류・누락은 data/raw/igo_supplement.csv (행마다 출처)
IGO = ["EU", "ECOWAS", "SADC", "EAC", "COMESA", "ECCAS", "GCC", "ASEAN", "CARICOM", "SICA",
       "Mercosur", "Andean", "PIF", "SAARC", "LOAS"]
COW_BAD = ["EAC"]   # COW 코딩이 실제 회원과 달라서 보충 표로 대체
cow_iso = pd.read_csv(HERE / "cow_iso3.csv").set_index("cow_name").iso3
igo = pd.read_csv(ROOT / "data" / "raw" / "igo_year_formatv3.csv", sep="\t", encoding="latin-1")
igo = igo[igo.ioname.isin(IGO) & ~igo.ioname.isin(COW_BAD) & (igo.year >= 1990)]
igo = igo.melt(id_vars=["ioname", "year"], value_vars=list(cow_iso.index), var_name="cow_name", value_name="status")
igo = igo[pd.to_numeric(igo.status, errors="coerce") == 1]
igo = (igo.assign(iso3=igo.cow_name.map(cow_iso)).groupby(["iso3", "ioname"]).year.agg(["min", "max"])
       .reset_index().set_axis(["iso3", "group", "first_year", "last_year"], axis=1).assign(source="COW IGO v3"))
supp = pd.read_csv(ROOT / "data" / "raw" / "igo_supplement.csv")
member = pd.concat([igo, supp[igo.columns]])
member = member[member.iso3.isin(nodes.index)].sort_values(["group", "iso3"])
member.to_csv(HERE / "layer_igo_membership.csv", index=False)   # 가입 연도 (V3 연도별 검사용)
build("igo", member.groupby(["iso3", "group"]).size().reset_index()[["iso3", "group"]])
