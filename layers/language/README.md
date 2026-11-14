# 언어 + 식민 종주국 연결 (B)

- [ ] CIA World Factbook 공용어 → `layer_language_groups.csv` (영어・프랑스어・스페인어・아랍어・포르투갈어 그룹별 결과 + 나머지 "기타")
- [ ] ICOW 식민 연결 → `layer_colony_edges.csv` (옛 식민지-종주국 `colony_<종주국>`, 같은 종주국 식민지끼리 `samecol_<종주국>`)
- [ ] 두 계층 1단계 (`stage1`)
- [ ] 언어 vs 식민 겹침: 언어로 묶인 쌍 중 식민 연결과 겹치는 비율
- [ ] 그룹별 확산 곡선 (`group_curve`): 아랍어권 vs 스페인어권

예시는 `layers/region/make_layer.py`.
