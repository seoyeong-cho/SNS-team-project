"""
소득 계층 전처리 (C 담당)
실행: python layers/income/preprocess.py

입력  data/raw/OGHIST_2026_10_08.xlsx  (World Bank 소득 분류 이력, 'Country Analytical History' 시트)
출력  layers/income/income_by_year.csv   iso3, year, group      (정리된 연도별 등급, 긴 형태)
      layers/income/income_nodes.csv     iso3, year_used, group, flag   (204개국 각 나라의 최종 등급)
      layers/income/unmatched.csv        nodes.csv와 안 맞는 코드 점검용

규칙
- 열 머리 'Data for calendar year'를 연도로 사용 (도입 연도 t → 같은 데이터연도 t 열). LAG로 조정 가능
- 도입국: 도입한 해의 등급. 미도입국: 2023년 등급
- 값 정리: 'LM*' → 'LM', '..' → 결측
- 도입한 해 값이 결측/범위 밖(1987 이전)이면 가장 가까운 연도 값으로 대체하고 flag에 남김
"""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.append(str(ROOT / "src"))
from common import load_nodes  # noqa: E402

RAW = ROOT / "data" / "raw" / "OGHIST_2026_10_08.xlsx"
SHEET = "Country Analytical History"
LAG = 0            # 도입 연도 t에 데이터연도 t - LAG 열을 쓴다
REF_YEAR = 2023    # 미도입국 기준 연도
VALID = {"L", "LM", "UM", "H"}

nodes = load_nodes()

# ---------- 1. 읽기 ----------
raw = pd.read_excel(RAW, sheet_name=SHEET, header=None)
year_row = raw.index[raw[1].astype(str).str.startswith("Data for calendar year")][0]
years = raw.iloc[year_row, 2:].dropna().astype(int)          # 열 위치 → 데이터연도
body = raw.iloc[year_row + 1:, :2 + len(years)]
body = body[body[0].astype(str).str.fullmatch(r"[A-Za-z]{3}")]  # iso3 행만 (주석 행 제거)

wide = body.iloc[:, [0, *range(2, 2 + len(years))]].copy()
wide.columns = ["iso3", *years.tolist()]
wide["iso3"] = wide["iso3"].str.upper()

# ---------- 2. 값 정리 ----------
long = wide.melt(id_vars="iso3", var_name="year", value_name="group")
long["year"] = long["year"].astype(int)
long["group"] = long["group"].astype(str).str.strip().str.replace("*", "", regex=False)
long.loc[~long["group"].isin(VALID), "group"] = pd.NA
long = long.dropna(subset=["group"]).sort_values(["iso3", "year"]).reset_index(drop=True)
long.to_csv(HERE / "income_by_year.csv", index=False)
print(f"연도별 등급: {long.iso3.nunique()}개 코드, {long.year.min()}~{long.year.max()}, {len(long)}행")

# ---------- 3. 코드 맞추기 점검 ----------
wb_codes, node_codes = set(long.iso3), set(nodes.index)
only_nodes = sorted(node_codes - wb_codes)
only_wb = sorted(wb_codes - node_codes)
unm = pd.DataFrame(
    [(c, "nodes에만 있음 (WB 등급 없음)", nodes.loc[c, "name"], nodes.loc[c, "adopter"]) for c in only_nodes]
    + [(c, "WB에만 있음 (nodes에 없음)", "", "") for c in only_wb],
    columns=["iso3", "문제", "name", "adopter"])
unm.to_csv(HERE / "unmatched.csv", index=False)
print(f"\nnodes에만 있음 {len(only_nodes)}개: {only_nodes}")
print(f"WB에만 있음 {len(only_wb)}개 (옛 국가·지역 등): {only_wb}")

# ---------- 4. 나라별 최종 등급 ----------
by = {c: g.set_index("year")["group"] for c, g in long.groupby("iso3")}


def pick(code, year):
    """(사용 연도, 등급, flag). 그 해 값이 없으면 가장 가까운 연도 값"""
    s = by.get(code)
    if s is None:
        return pd.NA, pd.NA, "WB 등급 없음"
    if year in s.index:
        return year, s[year], ""
    near = min(s.index, key=lambda y: (abs(y - year), y))
    why = "그 나라 첫 등급 이전 → 가장 이른 연도 값" if year < s.index.min() else "그 해 결측 → 가장 가까운 연도 값"
    return near, s[near], why


# WB 등급이 없는 소규모 영토 수동 보충
# 근거: OECD DAC 목록은 소규모 영토까지 소득 그룹을 매기는데, 2013~2018년 기준 자료에서
#       쿡 제도·몬트세랫·니우에·세인트헬레나·월리스 푸투나가 고소득 바로 앞인 상위중소득(UMIC) 끝에 묶여 있음.
#       → 도입 연도(COK 2014, SHN 2014, WLF 2017)가 이 기간 안이라 UM으로 둠. (WB 확인값이 아닌 추정)
# 니우에(도입 1969)는 도입 연도가 이 기간 밖이라 보충하지 않음. 바티칸(미도입)도 근거가 없어 비워 둠.
# 값과 이유·출처는 manual_fixes.csv (CONTRIBUTING 규칙). flag에는 csv의 '이유'를 그대로 씀
_mf = pd.read_csv(HERE / "manual_fixes.csv", encoding="utf-8")
MANUAL = {r.iso3: (r.group, r.이유, r.year) for r in _mf.itertuples()}

rows = []
for c, r in nodes.iterrows():
    t = int(r.year_imp) - LAG if r.adopter == 1 and pd.notna(r.year_imp) else REF_YEAR
    y, g, flag = pick(c, t)
    if c in MANUAL and pd.isna(g):
        g, flag, y_fix = MANUAL[c]
        assert y_fix == t, f"manual_fixes.csv {c} year {y_fix} ≠ 기준 연도 {t}"
        y = t
    rows.append(dict(iso3=c, adopter=int(r.adopter), in_analysis=int(r.in_analysis),
                     year_target=t, year_used=y, group=g, flag=flag))
out = pd.DataFrame(rows)
out.to_csv(HERE / "income_nodes.csv", index=False)

print("\n[204개국 등급 분포]\n", out.group.value_counts(dropna=False).to_string())
print("\n[flag 있는 나라]")
print(out[out.flag != ""].to_string(index=False))
