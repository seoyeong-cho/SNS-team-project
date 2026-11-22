"""
data/processed/nodes.csv 만들기 (A 담당). 실행: python src/make_nodes.py

전처리 규칙
1. 나라 단위(level == National) 세금만. 도시・주 단위 제외
2. 'National ' 뒤 공백(4행) 제거, 국가코드 PERU → PER
3. 나라마다 가장 이른 도입 연도
4. 폐지・누락 보충: 설탕세 DB는 '지금 시행 중인 세금' 목록이라 폐지된 세금은 사라짐
   → data/raw/manual_adoptions.csv(출처 포함)의 나라를 도입국으로 추가. 도입한 해 기준이고 폐지 여부는 상관없음
5. 분석 단위 = 유엔 회원국(countries.json unMember) ∪ 세금 도입국 → 204개
6. in_analysis = 1990~2023 도입국 (114개국)

열
- source: aug23(현행 DB) / manual(폐지・누락 보충)
- repeal_year: 폐지한 해 (확인된 나라만)

강건성 검사용 나라 성격 (가짜 세계를 '같은 성격끼리만' 섞을 때 씀)
- income_db: 설탕세 DB의 income_group (DB 작성 시점 등급, 도입국만 있음. 도입 해 기준 등급은 C가 layers/income에서 따로 만듦)
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
    # 같은 나라・같은 첫 해에 행이 여럿이고 값이 다르면 어느 행을 쓸지 여기서 정함 (파일 순서에 기대지 않음, #10)
    # NCL 2017: health_obj 0 (관세법 + 일반소비세) vs 1 (일반소비세 법령만) → 0 (11/22 팀 결정, #10)
    #   health_obj 1 쪽 TGC는 술・담배・컴퓨터・자동차까지 22% 붙는 일반 소비세 → 11/17 기준상 설탕세 아님. 남는 음료세가 건강 목적 0
    TIE_PICK = {"NCL": ("health_obj", 0)}
    first_year = ssb.groupby("country_code").year_imp.transform("min")
    for code, (col, val) in TIE_PICK.items():
        ssb = ssb[~((ssb.country_code == code) & (ssb.year_imp == first_year) & (ssb[col] != val))]
        first_year = ssb.groupby("country_code").year_imp.transform("min")
    tied = ssb[ssb.year_imp == first_year]
    tied = tied[tied.duplicated("country_code", keep=False)]
    cols_used = ["year_imp", "income_group", "health_obj", "legislation"]
    unclear = [c for c, g in tied.groupby("country_code") if (g[cols_used].nunique(dropna=False) > 1).any()]
    if unclear:
        raise ValueError(f"첫 해 행이 여럿이고 값이 다른 나라: {unclear} → TIE_PICK에 정하기")
    # 나라별 첫 세금 행 (행 통째로. groupby().first()는 열마다 첫 비결측값을 골라 행이 섞일 수 있음)
    first = ssb.sort_values("year_imp", kind="stable").drop_duplicates("country_code").set_index("country_code")

    budget_pat = re.compile(r"financ|budget|loi de finances|tax code|code g[ée]n[ée]ral|amend|modif", re.I)
    first["budget_year"] = [int(bool(budget_pat.search(str(r.legislation))) and str(int(r.year_imp)) in str(r.legislation))
                            for _, r in first.iterrows()]
    first["source"] = "aug23"
    first["repeal_year"] = pd.NA

    manual = pd.read_csv(RAW / "manual_adoptions.csv").set_index("iso3")
    dup = set(manual.index) & set(first.index)
    if dup:
        raise ValueError(f"manual_adoptions.csv에 현행 DB에 이미 있는 나라: {sorted(dup)}")
    manual = manual.assign(source="manual", budget_year=0).rename(columns={"year_imp": "year_imp"})
    manual.loc[manual.year_imp < 1990, "budget_year"] = pd.NA
    cols = ["year_imp", "income_group", "health_obj", "budget_year", "source", "repeal_year"]
    tax = pd.concat([first[cols], manual[cols]])

    C = {x["cca3"]: x for x in json.load(open(RAW / "countries.json", encoding="utf-8"))}
    codes = sorted({k for k, v in C.items() if v.get("unMember")} | set(tax.index))
    missing = [c for c in codes if c not in C]
    if missing:
        raise ValueError(f"countries.json에 없는 코드: {missing}")

    t = tax.reindex(codes)
    nodes = pd.DataFrame({
        "iso3": codes,
        "name": [C[k]["name"]["common"] for k in codes],
        "un_member": [int(bool(C[k].get("unMember"))) for k in codes],
        "adopter": t.year_imp.notna().astype(int).to_numpy(),
        "year_imp": t.year_imp.to_numpy(),
    })
    nodes["in_analysis"] = nodes.year_imp.between(1990, 2023).astype(int)
    nodes["income_db"] = t.income_group.to_numpy()
    nodes["health_obj"] = t.health_obj.to_numpy()
    nodes["budget_year"] = t.budget_year.to_numpy()
    nodes["source"] = t.source.to_numpy()
    nodes["repeal_year"] = t.repeal_year.to_numpy()

    out = ROOT / "data" / "processed" / "nodes.csv"
    nodes.to_csv(out, index=False)
    a = nodes[nodes.in_analysis == 1]
    print(f"{out.relative_to(ROOT)}: 분석 단위 {len(nodes)}, 도입국 {nodes.adopter.sum()} "
          f"(현행 DB {int((nodes.source == 'aug23').sum())} + 보충 {int((nodes.source == 'manual').sum())}), "
          f"1990~2023 도입국 {len(a)} (예산법 연도 의심 {int(a.budget_year.sum())}개국)")


if __name__ == "__main__":
    main()
