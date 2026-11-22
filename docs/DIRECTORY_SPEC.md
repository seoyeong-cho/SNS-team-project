# 📁 디렉토리 명세서

저장소 폴더마다 무엇을 두는지, 문서(`.md`)는 어디에 두는지 정한 규칙 (2026-11-18).
**앞으로 새로 만드는 `.md` 파일은 전부 `docs/` 안에 둠** (예외: 루트 `README.md`, `CONTRIBUTING.md`, `CLAUDE.md`). 코드 폴더(`layers/`, `analysis/`, `src/` 등)에는 `.md`를 만들지 않음.

## 1. 전체 구조

```
sns_team_project/
├─ README.md            프로젝트 소개 (예외: 루트 유지)
├─ CONTRIBUTING.md      협업 규칙 (예외: 루트 유지)
├─ CLAUDE.md            Claude Code가 세션마다 자동으로 읽는 규칙 (예외: 루트에 있어야 읽힘)
├─ requirements.txt
├─ data/
│  ├─ raw/              원본 그대로. 손대지 않음
│  └─ processed/        nodes.csv 등 전처리 결과 (A만 수정)
├─ src/                 공통 코드 (common.py, make_nodes.py), fonts/ 그림 글꼴 Pretendard (common.use_font())
├─ layers/
│  ├─ region/           A  지역 + 지역기구
│  ├─ language/         B  언어 + 식민
│  ├─ income/           C  소득
│  └─ trade/            D  무역
├─ analysis/            2단계・2-1단계・3단계 코드와 결과
├─ pilot/               파일럿 코드 (참고용, 수정 X)
├─ figures/             그림 (.png)
└─ docs/                모든 문서 (.md)
```

## 2. 폴더별로 두는 것

| 폴더 | 두는 것 | 두지 않는 것 |
|---|---|---|
| `data/raw/` | 받은 원본 (`.csv`, `.xlsx`, `.json`) | 가공한 파일, 문서 |
| `data/processed/` | 전처리 결과 `.csv` | 원본, 문서 |
| `src/` | 공통 `.py` | 분야별 코드, 문서 |
| `layers/<분야>/` | `make_layer.py`, `layer_*`・`result_*`・`robustness_*`・`adoption_*`・`manual_fixes.csv` | 문서 → `docs/layers/<분야>.md` |
| `analysis/` | 단계별 `.py`, 결과 `.csv` | 문서 → `docs/analysis/` |
| `pilot/` | 파일럿 `.py` | 새 파일 (수정 X) |
| `figures/` | 발표・보고서용 그림 | 코드, 문서 |
| `docs/` | 모든 `.md` 문서 | 코드, 데이터 |

빈 폴더를 커밋해야 할 때는 `.gitkeep`만 둠.

## 3. docs/ 안 구조

코드 폴더 구조를 그대로 따라감. 어느 폴더에 대한 문서인지 위치만 보고 알 수 있게.

```
docs/
├─ DIRECTORY_SPEC.md    이 문서
├─ PROJECT_README.md    통합 README (폴더별 README를 모은 것)
├─ ROLES.md             역할 분담・할 일・진행 상황 (누가 무엇을 하는지는 이 파일이 원본)
├─ data/
│  └─ raw.md            원본 데이터 출처・설명
├─ layers/
│  ├─ region.md         A
│  ├─ language.md       B
│  ├─ income.md         C
│  └─ trade.md          D
├─ analysis/
│  ├─ stage2.md
│  ├─ validation.md
│  └─ key_message.md     핵심 메시지 A/B 정의・판단 근거 (11/26 회의용)
└─ meeting/             회의록 (필요하면)
   └─ 2026-11-18.md
```

- 하위 폴더는 처음 문서를 넣을 때 만들면 됨 (미리 만들 필요 없음)
- 이미 `PROJECT_README.md`에 들어간 내용(3~10장)은 그대로 두고, 새로 쓰는 문서부터 위 구조를 따름

## 4. 파일 이름 규칙

| 종류 | 규칙 | 예 |
|---|---|---|
| 폴더 설명 | 그 폴더 이름 그대로, 소문자 | `docs/layers/income.md` |
| 회의록・날짜 문서 | `YYYY-MM-DD.md` | `docs/meeting/2026-11-21.md` |
| 저장소 전체 문서 | 대문자 + `_` | `DIRECTORY_SPEC.md`, `PROJECT_README.md` |

- 영문 이름만 씀 (한글 파일명은 git에서 깨져 보임)
- 띄어쓰기 대신 `_`

## 5. 예외

| 파일 | 이유 |
|---|---|
| `README.md` (루트) | GitHub 첫 화면에 자동으로 보임 |
| `CONTRIBUTING.md` (루트) | GitHub PR 화면에 자동으로 링크됨 |
| `.venv/` 안의 `.md` | 라이브러리 파일. git에 안 올라감 |

이 둘 말고 루트나 코드 폴더에 `.md`가 생기면 `docs/`로 옮김.

## 6. PR 올리기 전 확인

```bash
git ls-files "*.md"
```

`README.md`, `CONTRIBUTING.md`, `docs/...` 말고 다른 경로가 나오면 `docs/` 아래 맞는 곳으로 옮기고 올림.
