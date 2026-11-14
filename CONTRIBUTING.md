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

## 마감

| 날짜 | 할 일 |
|---|---|
| 11/17 (월) | A: nodes.csv, common.py, 대륙 예시 (이 저장소 첫 버전) / D: 무역 데이터 가능 여부 판단 |
| 11/23 (일) | 넷 다 계층 파일 + 1단계 결과 PR |
| 11/26 (목) | 2단계・2-1단계 결과 → 핵심 메시지 A/B 결정 |
| 11/30 (일) | 슬라이드 제출 |
| 12/18 | 최종 제출 (README 재현 순서대로 처음부터 돌아가야 함) |
