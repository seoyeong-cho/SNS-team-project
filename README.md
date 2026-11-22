# 🍫 설탕세는 어떻게 퍼지는가

소셜네트워크과학 팀 프로젝트 (2조)

121개국 설탕세 도입(현행 DB 117 + 폐지・누락 보충 4)을 5개 분야 연결(지역, 언어・식민, 소득, 지역기구, 무역) 위에 놓고, 같은 그룹 나라끼리 도입 시기가 우연보다 더 묶이는지 가짜 세계 1,000개와 비교해 검증함. 나라끼리 따라 한 것(확산)인지, WHO 권고 같은 공통 원인에 다 같이 반응한 것인지 구분하는 게 목표.

- 설계서・설명서: 노션 (팀 링크 참고)
- **역할 분담 (누가 무엇을, 진행 상황): [docs/ROLES.md](docs/ROLES.md)**
- 일정: 슬라이드 11/30, 발표 12/7, 최종 제출 12/18

## 처음부터 다시 돌리기 (재현 순서)

위에서부터 차례로 실행. 저장소 루트에서 실행 (어느 폴더에서 해도 되지만 기준은 루트). 전체 1분 정도 (`exclude_checked.py`가 30초 남짓)

```bash
pip install -r requirements.txt
python src/make_nodes.py                        # 1. data/processed/nodes.csv (204개국, 1990~2023 도입 114개국)
python layers/region/make_layer.py              # 2. 지역: 대륙・소지역・국경・지역기구 (A)
python layers/language/fetch_external.py        # 3. 외부 자료 받기 (B). 인터넷 필요, 꼭 언어 계층보다 먼저
python layers/language/make_layer.py            #    언어・식민 계층 (B)
python layers/language/supplementary_checks.py  #    언어・식민 보조 검증 (B)
python layers/income/preprocess.py              # 4. 소득 등급 전처리 → income_nodes.csv (C)
python layers/income/make_layer.py              #    소득 계층 (C)
python layers/income/merge_year_check.py        #    연도 검증 표 합치기 → year_check.csv
python layers/income/exclude46.py               #    검증 대상 46・60개국 뺀 소득 1단계
python layers/income/colombia_check.py          #    콜롬비아(2023년 11월)를 넣었을 때 1단계 민감도 (C, 2~5 다 끝난 뒤)
python layers/trade/make_layer.py               # 5. 무역 계층 k = 3, 5, 10 (D)
python analysis/exclude_checked.py              # 6. 연도 의심 국가 제외 검사, 전 계층 (2~5 다 끝난 뒤)
python analysis/adoption_income.py              #    도입 여부 검사 소득 강건성, 전 계층 (A, 2~5 다 끝난 뒤)
python analysis/stage2.py                       # 7. 2단계: 겹침 6×6, 각 분야 몫, 공유 분야 수 (2~5 다 끝난 뒤)
python analysis/stage2_region_split.py          #    2단계 보충: 대륙・지역기구・국경 겹침 분리 (A, stage2.py 다음)
python analysis/stage2_continent_check.py       #    2단계 보충: 대륙 효과 점검 (대륙별・나라 가중・정의 점검 + 그림, A, stage2.py 다음)
python analysis/validation/conditional_continent.py  # 8. V2: 대륙 안에서만 섞기, 지역기구・국경・소지역・무역・소득 (2~5 다 끝난 뒤)
python analysis/stage2_1.py                     # 9. 2-1단계: 다른 대륙 쌍만 1단계 + 따라 함 1~3년 (B, 2~5 다 끝난 뒤)
python analysis/stage3_paths.py                 # 10. 3단계 확산 경로 실제 vs 가짜, 언어・식민 (B)
python analysis/stage3_figures.py               #     확산 경로 그림 2장 → figures/stage3_*.png (B)
python analysis/validation/sim_scenarios.py     # 11. V1: 가상 데이터 S0・S1・S2로 검정 성능 확인 (B, 1분 안팎)
```

- 3번: ICOW 식민 자료・countrycode 변환표는 재배포 금지라 git에 없음. 이 스크립트가 `layers/language/_external/`에 받아 옴 (git 제외). 빼먹으면 언어 `make_layer.py`가 `ICOW 없음`으로 멈춤
- 1번이 바뀌면 2~8 전부 다시. 계층 하나만 고쳤으면 그 계층 줄 + 6~8번만 다시
- 가짜 세계는 seed 고정 → 다시 돌려도 CSV가 커밋된 것과 같아야 함 (그림 PNG는 matplotlib 버전 따라 바이트만 다를 수 있음). 달라지면 PR에 적기
- 검증한 버전 (11/22, 커밋된 CSV가 이 환경에서 나옴): Python 3.14, pandas 3.0.3, numpy 2.4.6, networkx 3.6.1, openpyxl 3.1.5, scipy 1.18.0, matplotlib 3.11.0. `requirements.txt`는 최소 버전(>=)만 둠 → 결과가 다르면 먼저 버전부터 맞춰 봄
- 2-1단계・3단계(`analysis/`)는 브랜치 합쳐지면 여기 추가

## 폴더 구조

```
data/
  raw/          원본 그대로. 손대지 않음 (출처: docs/PROJECT_README.md 3장)
  processed/    nodes.csv (A가 생성, 넷 다 이걸 씀. 강건성용 열 income_db, health_obj, budget_year 포함)
src/
  common.py     공통 함수 (투영, 1단계, 강건성, 따라 함 검사, 그룹 곡선, 구조 지표)
  make_nodes.py 전처리 → nodes.csv
layers/
  region/       A  지역(국경・소지역・대륙) + 지역기구
  language/     B  언어 + 식민 종주국 연결
  income/       C  소득 수준
  trade/        D  무역
analysis/       2단계(겹침 표, 각 분야 몫), 2-1단계, 3단계 그림
pilot/          파일럿 코드 (참고용, 수정 X)
figures/        그림
docs/           설계서 사본
```

## 분석 단계와 담당

| 단계 | 내용 | 담당 | 위치 |
|---|---|---|---|
| 전처리 | nodes.csv | A | `src/make_nodes.py` |
| 1단계 | 분야별 같은 그룹 연도 차이 vs 가짜 세계 | 각자 | `layers/<분야>/` |
| 2단계 | 겹침 표, 각 분야 몫, 공유 분야 수 | A | `analysis/stage2.py` |
| 2-1단계 | 다른 대륙 쌍만, 따라 함 검사 | B | `analysis/stage2_1.py` |
| 3단계 | 확산 곡선, 경로 실제 vs 가짜, 지도 | B・C | `analysis/stage3_*.py` |

## 파일럿에서 확인된 것 (본 분석 전 참고)

- 대륙: 같은 대륙 도입국 쌍 평균 8.0년 vs 가짜 9.2년, p 0.001. 소득・예산법 연도・도입 목적을 각각 거른 가짜 세계에서도 p 0.001~0.002로 남음
- 소지역: p 0.04로 약하고, 소득을 거르면 p 0.13으로 더 약해짐 (비슷한 소득 나라가 모여 있어서 생긴 부분 있음)
- 도입 여부도 지역별로 묶임: 같은 대륙 쌍의 도입 여부 일치 54.6% vs 가짜 51.5% (p 0.003), 소지역 59.3% vs 51.5% (p 0.001)
- (위 숫자는 폐지・누락 4개국 보충 후 114개국 기준. 아래 파일럿 숫자는 보충 전 112개국 기준)
- 예산법 연도와 같은 46개국을 빼면 대륙 p 0.03, 지역기구 p 0.085로 약해짐
- 따라 함(1~3년 안 도입)은 어느 분야에서도 가짜와 차이 없음
- 확산 경로 그림은 가짜 연도로 그린 것과 구분 안 됨 (p 0.16)

협업 규칙은 [CONTRIBUTING.md](CONTRIBUTING.md).
