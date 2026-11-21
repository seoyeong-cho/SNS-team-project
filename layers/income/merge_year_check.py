"""46개국 연도 검증 표 합치기: year_check_A.csv + year_check_C.csv → year_check.csv
실행: python layers/income/merge_year_check.py
기준은 CONTRIBUTING.md '도입 연도・설탕세 판단 기준'
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
parts = [pd.read_csv(HERE / f"year_check_{w}.csv", dtype=str) for w in ("A", "C")]
assert list(parts[0].columns) == list(parts[1].columns), "A・C 표의 열이 다름"
out = pd.concat(parts).sort_values("iso3")
assert not out.iso3.duplicated().any(), "A・C에 같은 나라가 겹침"
assert out.status.isin(["맞음", "수정", "설탕세아님", "모름"]).all(), "status 값 확인"
out.to_csv(HERE / "year_check.csv", index=False)
print(len(out), "개국\n", out.status.value_counts().to_string())
