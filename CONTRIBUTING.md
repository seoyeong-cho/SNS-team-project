# 협업 규칙

## 브랜치

- `main`은 항상 돌아가는 상태로 둠. 직접 push 하지 않음
- 각자 브랜치에서 작업: `region`, `language`, `income`, `trade`, `analysis`
- 다 되면 Pull Request → 한 명 이상 보고 merge

```bash
git checkout -b language          # 처음 한 번
git add layers/language
git commit -m "언어 계층 1단계"
git push -u origin language       # GitHub에서 PR 만들기
```

작업 시작 전에 항상 최신 main 받기:

```bash
git checkout main && git pull
git checkout language && git merge main
```

## 각자 건드리는 곳

- 자기 폴더 `layers/<분야>/`만 수정. 남의 폴더는 PR 코멘트로 말하기
- `src/common.py`, `data/processed/`는 A만 수정. 함수가 더 필요하면 이슈로 요청
- `data/raw/`의 원본 파일은 받은 그대로 둠. 바꿀 게 있으면 변환 스크립트로

## 계층 파일 형식 (꼭 지킴)

| 파일 | 열 | 규칙 |
|---|---|---|
| `layer_<이름>_groups.csv` | `iso3, group` | 한 나라가 그룹 여러 개면 행 여러 개 |
| `layer_<이름>_edges.csv` | `src, dst, group` | `src < dst`, 중복 없음, 자기 자신 연결 없음 |
| `result_<이름>.csv` | `group, n_adopters, n_pairs, mean_gap_real, mean_gap_fake_avg, p` | `stage1()` 결과 그대로 |

- 그룹으로 묶이는 분야(언어, 소득 등)는 `groups_to_edges()`로 엣지 생성
- 쌍으로 정의되는 분야(국경, 무역 상위 교역국, 식민 종주국-식민지)는 엣지 표를 직접 만들고 `group` 열에 관계 이름(예: `border`, `top5_trade`, `colony_FRA`)
- 제출 전 `check_edges(edges, nodes)` 통과해야 함

## 1단계 계산

- `common.py`의 `stage1()`만 씀. 각자 따로 짜면 넷 결과를 비교할 수 없음
- 가짜 세계 seed는 42, 개수 1,000 고정 (`common.py`에 있음)
- 손으로 고친 매칭(국가명 → iso3 등)은 `layers/<분야>/manual_fixes.csv`에 이유와 함께 적기

## 강건성 검사 (각자 계층마다 같이 냄)

기본 가짜 세계는 '해마다 몇 개국 도입했는지'만 맞추고 나머지는 전부 섞음. 그래서 소득이나 도입 목적처럼 도입 시기에 영향을 주는 나라 성격이 같은 그룹에 몰려 있으면, 따라 한 게 없어도 같은 그룹끼리 연도가 가깝게 나올 수 있음.

→ `robustness(edges, nodes)`로 같은 성격끼리만 섞은 가짜 세계에서 다시 검사. 결과는 `robustness_<이름>.csv`

| shuffle | 섞는 방식 | 거르는 요인 |
|---|---|---|
| `basic` | 도입국 전체에서 섞음 | 세계적 유행 (WHO 2016 등) |
| `income_db` | 같은 소득 등급끼리만 | 소득 수준 |
| `budget_year` | 예산법 연도 의심 여부끼리만 | 기존 소비세가 설탕세로 집계된 경우 |
| `health_obj` | 건강 목적 여부끼리만 | 도입 목적 (건강 vs 세수) |

- 기본에서 작던 p가 어떤 줄에서 커지면 → 그 효과 일부는 그 성격 때문이라고 해석
- 네 줄 다 작으면 → "세계적 유행, 소득, 도입 목적으로 설명되는 것보다 더 묶였다"고 말할 수 있음
- 같은 지역에 한꺼번에 온 외부 충격(예: 지역 단위 세무 개혁 권고)은 어떤 섞기로도 못 거름. 결론에 "따라 했다"고 쓰지 않는 이유
- `follow_test(..., strata="income_db")`처럼 따라 함 검사에도 같은 옵션 있음

## 도입 여부 검사 (각자 계층마다 같이 냄)

1단계는 도입국끼리 '시기'만 봐서 미도입국 87개국이 빠짐. 그런데 '같이 안 한 것'도 패턴임 (예: 한국・일본・중국 모두 미도입)

→ `adoption_test(edges, nodes)`로 204개국 전부의 도입 여부(0/1)를 섞어서 "같은 그룹 쌍 중 도입 여부가 같은 비율"을 가짜 세계와 비교. 결과는 `adoption_<이름>.csv`

- `same_status_real`이 `same_status_fake_avg`보다 크고 p가 작으면 → 같은 그룹끼리 같이 하거나 같이 안 함
- `both_adopted`: 같은 그룹 쌍 중 둘 다 도입한 비율 (참고용)
- 도입 여부는 소득・제도에 시기보다 더 크게 좌우됨 → 강건성 검사가 필요한데, `income_db`・`health_obj`는 도입국만 값이 있어서 여기선 못 씀. C가 204개국 소득 등급(World Bank historical)을 만들면 그 열로 `strata` 지정
- 미도입 = '2023년까지 안 함'이지 '앞으로도 안 함'이 아님. 발표에서 이렇게 표현

## 폐지・누락 국가

설탕세 DB는 '지금 시행 중인 세금' 목록이라 폐지된 세금은 사라짐 → 미도입국처럼 보임. 우리는 '언제 도입했나'를 보니까 폐지했어도 도입한 해에 도입국으로 둠

- `data/raw/manual_adoptions.csv`에 출처와 함께 추가 → `python src/make_nodes.py` 다시 실행
- 지금 4개국: 이스라엘(2022 도입, 2023 폐지), 보츠와나(2021, DB 누락), 덴마크(1930년대, 2014 폐지), 노르웨이(1924, 2021 폐지)
- 더 찾으면 추가 (C 담당, 연도 검증 때 같이)

## 마감

| 날짜 | 할 일 |
|---|---|
| 11/17 (월) | A: nodes.csv, common.py, 대륙 예시 (이 저장소 첫 버전) / D: 무역 데이터 가능 여부 판단 |
| 11/21 (금) | 넷 다 계층 파일 + 1단계・강건성 결과 PR (2단계를 돌리려면 다섯 계층이 다 있어야 함) |
| 11/23 (일) | **2단계까지 완료 (팀 확정)**: A가 겹침 표・각 분야 몫・공유 분야 수 |
| 11/26 (목) | 2-1단계(지리 밖 연결, 따라 함 검사) 결과 + 46개국 뺀 2단계 → 핵심 메시지 A/B 결정 |
| 11/30 (일) | 슬라이드 제출 |
| 12/18 | 최종 제출 (README 재현 순서대로 처음부터 돌아가야 함) |
