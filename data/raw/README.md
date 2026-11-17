# 원본 데이터

받은 그대로 둠. 새 원본을 넣으면 이 표에 한 줄 추가.

| 파일 | 내용 | 출처 | 받은 날 | 담당 |
|---|---|---|---|---|
| `SSB-Tax-Database-Aug23.csv` / `.xlsx` | 설탕세 도입 연도 (분석 기준판) | World Bank Global SSB Tax Database, 2023년 8월판 | 2026-11 | A |
| `SSB-Tax-Database-Feb23.xlsx` | 같은 DB 이전판 (버전 비교용) | World Bank, 2023년 2월판 | 2026-11 | A |
| `SSB-Tax-Database-Aug22.xlsx` | 같은 DB 이전판 (버전 비교용) | World Bank, 2022년 8월판 | 2026-11 | A |
| `countries.json` | 국가 코드, 대륙, 소지역, 국경 | github.com/mledoze/countries | 2026-11 | A |
| `manual_adoptions.csv` | 현행 DB에 없는 도입국 (폐지 3, 누락 1) | 행마다 출처 URL | 2026-11 | A (추가는 C) |

## 추가 예정

| 데이터 | 출처 | 담당 | 메모 |
|---|---|---|---|
| 지역기구 가입 | Correlates of War IGO v3 | A | 2014년까지라 2015년 이후 가입은 기구 공식 회원국 목록으로 보충. UN・WHO 같은 전 세계 기구는 제외 |
| 공용어 | CIA World Factbook (Languages) | B | 공용어 표시된 것만. countries.json `languages`로 교차 확인 |
| 식민 종주국 | ICOW Colonial History v1.1 | B | 매칭 어려우면 CEPII GeoDist `colony`, `comcol` |
| 소득 등급 | World Bank Country and Lending Groups (historical) | C | 도입한 해의 등급 사용 |
| 음료 무역 | UN Comtrade HS 2202 | D | 안 되면 CEPII BACI, 그것도 안 되면 대륙 넘는 기구(OECD・APEC 등) 회원 목록 |
| 비만・당뇨 (선택) | WHO Global Health Observatory | - | 2단계 통제변수로만 |
