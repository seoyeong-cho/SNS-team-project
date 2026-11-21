# 소득 계층 (C)

소득 등급 계층과, A・C가 같이 한 도입 연도 검증 표. 코드와 결과는 `layers/income/`.

```bash
python layers/income/preprocess.py        # 처음 한 번: 소득 등급 정리 → income_by_year.csv, income_nodes.csv
python layers/income/make_layer.py        # 엣지 → 1단계 → 강건성 → 도입 여부
python layers/income/merge_year_check.py  # 연도 검증 표 A + C → year_check.csv
python layers/income/exclude46.py         # 검증 대상 나라를 뺀 1단계 (excl46, excl60)
```

- 모든 결과는 `src/common.py` 함수를 그대로 씀 (가짜 세계 1,000개, seed 42)
- 2026-11-21 main 기준으로 다시 돌려서 결과 파일이 그대로 나오는 것 확인함

## 파일 (`layers/income/`)

| 파일 | 내용 | 열 |
|---|---|---|
| `preprocess.py` | World Bank 소득 분류 이력 → 연도별 등급, 나라별 최종 등급 | |
| `make_layer.py` | 엣지 → 1단계・강건성・도입 여부 | |
| `income_by_year.csv` | 연도별 소득 등급 (1987~2025, 223개 지역) | `iso3, year, group` |
| `income_nodes.csv` | 204개국 각 나라에 쓴 등급과 그 근거 | `iso3, adopter, in_analysis, year_target, year_used, group, flag` |
| `unmatched.csv` | nodes와 WB 코드가 안 맞는 나라 점검용 | `iso3, 문제, name, adopter` |
| `manual_fixes.csv` | 손으로 넣은 등급 (WB에 없는 3개국) | `iso3, group, year, 이유, 출처` |
| `layer_income_groups.csv` / `layer_income_edges.csv` | 계층 | `iso3, group` / `src, dst, group` |
| `result_income.csv`, `robustness_income.csv`, `adoption_income.csv` | 1단계・강건성・도입 여부 | 다른 계층과 같음 |
| `result_income_excl{46,60}.csv`, `robustness_income_excl{46,60}.csv` | 연도 검증 대상 나라를 연도 비교에서 뺀 1단계・강건성 | 다른 계층과 같음 |
| `year_check_A.csv`, `year_check_C.csv` → `year_check.csv` | 46개국 도입 연도 검증 (A 22개국 + C 24개국) | 아래 '연도 검증' |
| `year_check_14.csv` | 추가로 의심된 14개국 검증 | 위와 같음 |

## 원본 데이터

| 파일 | 내용 | 출처 |
|---|---|---|
| `data/raw/OGHIST_2026_10_08.xlsx` | 나라별 연도별 소득 등급 (`Country Analytical History` 시트) | World Bank Country and Lending Groups (historical), 2026-10-08 받음 |

## 계층 만들기

### 등급 고르기 (`preprocess.py`)

- 그룹 = World Bank 소득 등급 4개: `L`, `LM`, `UM`, `H`
- **도입국: 도입한 해의 등급. 미도입국: 2023년 등급**
- 연도는 열 머리 'Data for calendar year'를 씀 (도입 연도 t → 데이터연도 t). 시차는 `LAG`로 바꿀 수 있음 (지금 0)
- 값 정리: `LM*` → `LM`, `..` → 결측

**그 해 값이 없는 나라 (`flag` 열)**

| 경우 | 처리 | 나라 수 |
|---|---|---|
| 도입 연도가 그 나라 첫 WB 등급보다 이름 (WB는 1987년부터, SSD처럼 신생국은 더 늦음) | 그 나라 가장 이른 연도 값 | 9 |
| 그 해 값만 결측 | 가장 가까운 연도 값 | 1 (VEN) |
| WB에 아예 없음 → OECD DAC 2013~18 UMIC 묶음 근거로 `UM` 추정 | `manual_fixes.csv` | 3 (COK, SHN, WLF) |
| WB에 아예 없음, 근거도 없음 | 그룹에서 빠짐 → 연결 없음 | 2 (NIU, VAT) |

### 결과 그룹

| 등급 | 전체 | 도입국 | 미도입국 |
|---|---|---|---|
| H | 62 | 31 | 31 |
| UM | 51 | 27 | 24 |
| LM | 54 | 35 | 19 |
| L | 35 | 27 | 8 |

- 엣지 5,192개, 평균 연결 수 50.9, 고립국 2 (NIU, VAT)
- 같은 등급이면 다 연결 → 다섯 계층 중 가장 촘촘함 (대륙 4,395개보다 많음)

## 결과

### 1단계: 같은 등급 도입국끼리 도입 시기가 가까운가

| 그룹 | 도입국 | 도입국 쌍 | 실제 평균 연도 차 | 가짜 세계 평균 | p |
|---|---|---|---|---|---|
| **ALL** | **114** | **1,584** | **9.22년** | **9.15년** | **0.621** |
| H | 29 | 406 | 8.16년 | 9.11년 | 0.210 |
| L | 26 | 325 | 8.55년 | 9.21년 | 0.282 |
| LM | 33 | 528 | 10.49년 | 9.14년 | 0.911 |
| UM | 26 | 325 | 9.15년 | 9.17년 | 0.492 |

- 같은 소득 등급끼리 도입 시기가 가깝지 않음. 어느 등급도 유의하지 않음
- 그룹별 도입국 수(29+26+33+26 = 114)는 '도입한 해 등급' 기준이라 위 '결과 그룹' 표(도입국 31・27・35・27)와 다름. 위 표는 1990년 이전 도입국까지 센 것

### 강건성 (p)

| basic | income_db | budget_year | health_obj |
|---|---|---|---|
| 0.621 | 0.492 | 0.627 | 0.723 |

- 원래 효과가 없어서 어떤 성격으로 섞어도 없음

### 도입 여부 (204개국)

| 쌍 | 도입 여부 같은 비율 (실제) | 가짜 세계 | 둘 다 도입 | p |
|---|---|---|---|---|
| 5,192 | 0.520 | 0.515 | 0.339 | 0.181 |

- 같은 등급끼리 도입 여부가 같은 비율도 우연과 비슷함

### 연도 검증 나라를 뺀 결과 (`exclude46.py`)

연도가 의심스러운 나라를 연도 비교에서 빼도(`in_analysis = 0`, 연결은 유지) 결론이 같은지 확인

| 버전 | 뺀 나라 | 남은 분석 도입국 | p (basic) | p (income_db) |
|---|---|---|---|---|
| 전체 | 0 | 114 | 0.621 | 0.492 |
| excl46 | 46개국 (`year_check.csv`) | 68 | 0.387 | 0.247 |
| excl60 | 46 + 14개국 (`year_check_14.csv`) | 54 | 0.250 | 0.089 |

- 어느 버전에서도 유의하지 않음 → 소득 계층에서는 연도 오류 때문에 결론이 바뀌지 않음

### 해석

- **소득 수준이 같다고 도입 시기나 도입 여부가 같이 가지 않음**
- 지역・무역 계층에서 나온 묶임이 '비슷한 소득 나라끼리 모여 있어서'라는 설명은 약해짐. 다만 소지역은 `income_db`로 섞으면 효과가 사라졌으므로(`docs/layers/region.md`) 2단계에서 같이 봄
- 대신 `income_by_year.csv`는 다른 계층의 강건성에 쓸 수 있음: 204개국 전부 연도별 등급이 있으므로 도입 여부 검사의 소득 `strata`로 쓰면 됨 (지역・무역 문서의 '정할 것')

## 연도 검증 (A・C 공동)

설탕세 DB 연도가 실제 첫 도입 연도와 다른지 법령으로 확인한 표. 기준은 `CONTRIBUTING.md` '도입 연도・설탕세 판단 기준'

| 표 | 나라 | 맞음 | 수정 | 모름 |
|---|---|---|---|---|
| `year_check.csv` (A 22 + C 24) | 46 | 27 | 8 | 11 |
| `year_check_14.csv` (추가 의심) | 14 | 1 | 12 | 1 |

열: `iso3, name, continent, year_db, year_checked, year_enacted, status, evidence, checker, legislation, url_db`

- **아직 `data/processed/nodes.csv`에 반영 안 함.** 지금 모든 계층 결과는 DB 연도 기준
- `year_check_14.csv`의 `수정` 12개국은 대부분 1990년 이전으로 바뀜 (예: THA 1952, BEL 1939, ARG 1979). `[상한값]` = '늦어도 이 해에는 있었음'이라 실제는 더 이를 수 있음. 반영하면 이 나라들은 1990~2023 분석 기간 밖으로 빠짐 → 결과가 크게 바뀔 수 있어 팀 결정 필요

## 한계

- 도입국은 도입한 해, 미도입국은 2023년 등급 → 두 집단의 기준 연도가 다름
- 도입 연도에 WB 등급이 없는 9개국(1987년 이전 도입국, 신생국)은 그 나라 가장 이른 등급으로 대신함
- COK・SHN・WLF 등급은 OECD DAC 묶음으로 추정한 값
- 4개 등급 경계는 WB 기준 그대로. 경계 근처 나라(예: 한 해 차이로 UM ↔ H)도 다른 그룹이 됨

## 정할 것

- [ ] 연도 검증 결과를 `nodes.csv`에 반영할지, 반영한다면 46개국만인지 60개국까지인지 (A가 `make_nodes.py` 수정)
- [ ] `income_by_year.csv`로 다른 계층 도입 여부 검사에 소득 강건성 추가 (`common.py`에 넣을지 A와 정함)
