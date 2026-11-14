# 무역 (D)

- [ ] 11/17까지: Comtrade(또는 CEPII BACI)로 204개국 음료(HS 2202) 양국 교역액 받아지는지 판단 → 이슈로 공유
- [ ] 나라마다 상위 5개 교역국, **서로** 상위 5위 안일 때만 연결 → `layer_trade_edges.csv` (group = `top5_trade`)
- [ ] 상위 3・5・10으로 바꿔도 결과 비슷한지 확인
- [ ] 1단계 (`stage1`)
- [ ] 계층 비교표 `analysis/layer_table.csv` (`structure()` 결과 모으기)

쌍으로 정의되는 계층이라 `groups_to_edges` 대신 엣지 표를 직접 만듦. `check_edges` 통과 필수.
