"""
2단계 보충: 지역 분야 안의 겹침 분리 (대륙・지역기구・국경) (A)
실행: python analysis/stage2_region_split.py   (analysis/stage2.py 다음. stage2_pairs.csv를 읽음)
설명 문서: docs/analysis/stage2.md '지역 겹침 분리'

왜: 지역기구 쌍의 대부분, 국경 쌍의 거의 전부가 같은 대륙 쌍 → 1단계에서 지역기구・국경이 유의한 게
    '같은 대륙'이라서인지, 대륙 안에서도 기구・국경이 더 묶는지 따로 봄
    (stage2.md 회귀에서 지역기구는 대륙을 넣으면 사라짐 → 같은 질문을 겹치지 않는 칸으로 나눠 직접 봄)

1. 칸 나누기: 도입국 쌍(114개국)을 대륙 c / 지역기구 i / 국경 b 연결 여부로 겹치지 않게 나눔
   c+i+b, c+i, c+b, c만, i만(다른 대륙), b만(다른 대륙), i+b(다른 대륙), 없음
   칸마다 평균 연도 차이 vs 가짜 세계. p = 가짜 평균이 실제 이하인 비율 (작을수록 그 칸 쌍끼리 시기 가까움)
2. 차이 검사 (같은 대륙 쌍 안에서 비교)
   igo_in_continent    : (같은 대륙 + 지역기구) − (같은 대륙 + 지역기구 없음)
   border_in_continent : (같은 대륙 + 국경) − (같은 대륙 + 국경 없음)
   continent_only      : (같은 대륙만, 기구・국경 없음) − (셋 다 없음)
   음수 = 앞쪽이 더 가까움. p = 가짜 차이가 실제 이하인 비율
- 섞는 방식: basic(전체에서) / continent(같은 대륙 도입국끼리만, V2와 같음. countries.json region, 메모리에서만)
- 나라: all / unsure46 (검증에서 확인 안 된 19개국을 연도 비교에서 뺌, exclude_checked.py와 같은 목록)
- 가짜 세계 seed 42, 1,000개 (common.SEED, common.R)
결과: analysis/stage2_region_split.csv
시간: 몇 초
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))
from common import R, SEED, _shuffles, analysis_countries, load_nodes  # noqa: E402

L = ROOT / "layers"
pairs = pd.read_csv(ROOT / "analysis" / "stage2_pairs.csv")

C = {x["cca3"]: x for x in json.load(open(ROOT / "data" / "raw" / "countries.json", encoding="utf-8"))}
base = load_nodes()
base["continent_label"] = [C[k]["region"] for k in base.index]

t46 = pd.read_csv(L / "income" / "year_check.csv")
VERSIONS = {"all": [], "unsure46": list(t46[t46.status != "맞음"].iso3)}


def cell(r):
    c, i, b = r.continent, r.igo, r.border
    if c:
        return "c+" + ("i+b" if i and b else "i" if i else "b" if b else "only")
    return "i+b(cross)" if i and b else "i(cross)" if i else "b(cross)" if b else "none"


CELLS = ["c+i+b", "c+i", "c+b", "c+only", "i(cross)", "b(cross)", "i+b(cross)", "none"]
pairs["cell"] = pairs.apply(cell, axis=1)
DIFFS = {   # 이름: (앞 칸 조건, 뒤 칸 조건)
    "igo_in_continent": (lambda p: (p.continent == 1) & (p.igo == 1), lambda p: (p.continent == 1) & (p.igo == 0)),
    "border_in_continent": (lambda p: (p.continent == 1) & (p.border == 1), lambda p: (p.continent == 1) & (p.border == 0)),
    "continent_only": (lambda p: p.cell == "c+only", lambda p: p.cell == "none"),
}

rows = []
for ver, drop in VERSIONS.items():
    nd = base.copy()
    nd.loc[drop, "in_analysis"] = 0
    ad = list(analysis_countries(nd))
    pos = {c: k for k, c in enumerate(ad)}
    sub = pairs[pairs.src.isin(pos) & pairs.dst.isin(pos)].reset_index(drop=True)
    i, j = sub.src.map(pos).to_numpy(), sub.dst.map(pos).to_numpy()
    yy = nd.loc[ad, "year_imp"].to_numpy(float)
    masks = {f"cell:{k}": (sub.cell == k).to_numpy() for k in CELLS}
    for name, (fa, fb) in DIFFS.items():
        masks[f"diff:{name}"] = (fa(sub).to_numpy(), fb(sub).to_numpy())

    def stats(ys):
        g = np.abs(ys[i] - ys[j])
        out = {}
        for k, m in masks.items():
            if k.startswith("cell:"):
                out[k] = g[m].mean() if m.any() else np.nan
            else:
                a, b = m
                out[k] = g[a].mean() - g[b].mean()
        return out

    real = stats(yy)
    for shuffle in ["basic", "continent"]:
        labels = None if shuffle == "basic" else nd.loc[ad, "continent_label"].astype(str).to_numpy()
        fake = pd.DataFrame([stats(ys) for ys in _shuffles(yy, R, SEED, labels)])
        for k, m in masks.items():
            kind, name = k.split(":")
            n = int(m.sum()) if kind == "cell" else f"{int(m[0].sum())} vs {int(m[1].sum())}"
            f = fake[k].to_numpy()
            p = np.nan if np.isnan(real[k]) else (np.sum(f <= real[k]) + 1) / (R + 1)
            rows.append(dict(version=ver, n_adopters=len(ad), shuffle=shuffle, kind=kind, name=name, n_pairs=n,
                             real=round(real[k], 3), fake_avg=round(float(np.nanmean(f)), 3), p=round(p, 4)))

out = pd.DataFrame(rows)
out.to_csv(ROOT / "analysis" / "stage2_region_split.csv", index=False)
pd.set_option("display.width", 200)
print(out.to_string(index=False))
print("저장: analysis/stage2_region_split.csv")
