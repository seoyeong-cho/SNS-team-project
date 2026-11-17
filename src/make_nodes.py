"""
data/processed/nodes.csv 만들기 (A 담당). 실행: python src/make_nodes.py

전처리 규칙
1. 나라 단위(level == National) 세금만. 도시・주 단위 제외
2. 'National ' 뒤 공백(4행) 제거, 국가코드 PERU → PER
3. 나라마다 가장 이른 도입 연도
4. 분석 단위 = 유엔 회원국(countries.json unMember) ∪ 세금 도입국 → 204개
5. in_analysis = 1990~2023 도입국 (112개국)

강건성 검사용 나라 성격 (가짜 세계를 '같은 성격끼리만' 섞을 때 씀)
- income_db: 설탕세 DB의 income_group (DB 작성 시점 등급. 도입 해 기준 등급은 C가 layers/income에서 따로 만듦)
- health_obj: 건강 목적이 명시된 세금이면 1, 아니면 0 (DB 값, 나라의 첫 세금 기준)
- budget_year: 도입 연도가 예산법・세법 개정 연도와 같아 보이면 1 (법령 이름에 finance/budget/tax code 등 + 도입 연도가 함께 있음).
  자동 판별이라 틀릴 수 있음 → C가 46개국 검증하면서 확인
"""
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"


def national(path):
    d = pd.read_csv(path, encoding="utf-8-sig") if str(path).endswith(".csv") else pd.read_excel(path)
    d = d.rename(columns={"wb_code": "country_code"}).dropna(subset=["jurisdiction"])
    d["level"] = d["level"].astype(str).str.strip()
    d["country_code"] = d["country_code"].replace({"PERU": "PER"})
    return d[d.level == "National"]


def main():
    ssb = national(RAW / "SSB-Tax-Database-Aug23.csv")
    year = ssb.groupby("country_code").year_imp.min()
    first = ssb.sort_values("year_imp").groupby("country_code").first()   # 나라별 첫 세금 행

    budget_pat = re.compile(r"financ|budget|loi de finances|tax code|code g[ée]n[ée]ral|amend|modif", re.I)
    budget = {k: int(bool(budget_pat.search(str(r.legislation))) and str(int(r.year_imp)) in str(r.legislation))
              for k, r in first.iterrows()}

    C = {x["cca3"]: x for x in json.load(open(RAW / "countries.json", encoding="utf-8"))}
    codes = sorted({k for k, v in C.items() if v.get("unMember")} | set(year.index))
    missing = [c for c in codes if c not in C]
    if missing:
        raise ValueError(f"countries.json에 없는 코드: {missing}")

    nodes = pd.DataFrame({
        "iso3": codes,
        "name": [C[k]["name"]["common"] for k in codes],
        "un_member": [int(bool(C[k].get("unMember"))) for k in codes],
        "adopter": [int(k in year.index) for k in codes],
        "year_imp": [year.get(k) for k in codes],
    })
    nodes["in_analysis"] = nodes.year_imp.between(1990, 2023).astype(int)
    nodes["income_db"] = [first.income_group.get(k) for k in codes]
    nodes["health_obj"] = [first.health_obj.get(k) for k in codes]
    nodes["budget_year"] = [budget.get(k) for k in codes]
    out = ROOT / "data" / "processed" / "nodes.csv"
    nodes.to_csv(out, index=False)
    a = nodes[nodes.in_analysis == 1]
    print(f"{out.relative_to(ROOT)}: 분석 단위 {len(nodes)}, 도입국 {nodes.adopter.sum()}, "
          f"1990~2023 도입국 {len(a)} (예산법 연도 의심 {int(a.budget_year.sum())}개국)")


if __name__ == "__main__":
    main()
