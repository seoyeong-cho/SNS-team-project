"""
data/processed/nodes.csv 만들기 (A 담당). 실행: python src/make_nodes.py

전처리 규칙
1. 나라 단위(level == National) 세금만. 도시・주 단위 제외
2. 'National ' 뒤 공백(4행) 제거, 국가코드 PERU → PER
3. 나라마다 가장 이른 도입 연도
4. 분석 단위 = 유엔 회원국(countries.json unMember) ∪ 세금 도입국 → 204개
5. in_analysis = 1990~2023 도입국 (112개국)
"""
import json
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
    out = ROOT / "data" / "processed" / "nodes.csv"
    nodes.to_csv(out, index=False)
    print(f"{out.relative_to(ROOT)}: 분석 단위 {len(nodes)}, 도입국 {nodes.adopter.sum()}, "
          f"1990~2023 도입국 {nodes.in_analysis.sum()}")


if __name__ == "__main__":
    main()
