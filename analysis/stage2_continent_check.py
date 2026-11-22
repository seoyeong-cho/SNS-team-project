"""
대륙 효과 점검: 어느 대륙이 받치나, 가중・정의를 바꿔도 남나 (A, 11/22)
실행: python analysis/stage2_continent_check.py   (analysis/stage2.py 다음. stage2_pairs.csv를 읽음)
설명 문서: docs/analysis/stage2.md '대륙 효과 점검'

왜: V4(수정, validation.md 3장)에서 대륙 1단계(p 0.001)가 아프리카를 빼면 p 0.781, 대륙마다 한 표면 p 0.328
    → 이슈 #22. 쌍 가중 탓인지, 아메리카・유럽이 반대로 흩어져서인지, 아프리카 연도 기록 탓인지 나눠 봄

1. 1단계 대륙 통계를 여러 방식으로 → analysis/stage2_continent_check.csv
   stat
     pair          : 같은 대륙 도입국 쌍 평균 연도 차이 (= 1단계, 쌍마다 한 표)
     country       : 나라마다 같은 대륙 도입국과의 평균 차이 → 나라끼리 평균 (나라마다 한 표, 보조 통계)
                     쌍 수는 나라 수의 제곱으로 늘어 큰 대륙(아프리카 40개국 = 35%, 쌍 54%)이 커짐 → 그걸 막음
     continent_equal: 대륙마다 평균 → 대륙끼리 평균 (대륙마다 한 표, V4 group_equal과 같음)
     no_Africa     : 아프리카 쌍만 빼고 pair (가짜 세계는 그대로 114개국 섞기, V4 all_without과 같음)
     <대륙>        : 그 대륙 쌍만
   version (어느 나라를 연도 비교에 넣나. 연결은 그대로)
     all        : 114개국
     unsure46   : 검증에서 '맞음'이 아닌 19개국 빼기 (exclude_checked.py와 같은 목록)
     excl46     : 검증 대상 46개국 다 빼기
     health_obj : 건강 목적 세금(health_obj = 1)만 (정의 점검: 세수용 음료 소비세 빼기, 이슈 #6 4번)
     since2014  : 2014년(멕시코) 이후 도입국만 (정의 점검: 1990년대 도입 빼기)
   shuffle: basic(전체에서 섞기) + all에서만 강건성 3개(income_db, budget_year, health_obj 안에서)
2. 2단계 대륙 몫을 대륙별로 → analysis/stage2_continent_share.csv
   stage2.py 각 분야 몫 회귀에서 continent 한 열을 대륙 5개 열(같은 아프리카 쌍, 같은 아시아 쌍 …)로 나눔
   나머지 5개 분야(igo, language, colony, income, trade)는 그대로. version은 1번과 같음, shuffle basic
   p = 가짜 세계에서 계수가 실제 이하인 비율 (한쪽, 작을수록 '묶임')

3. 그림 → figures/stage2_대륙별_순열분포.png: 대륙 5개 × (전체 / 건강 목적 세금만), 1번과 같은 가짜 세계, x축 모두 같음

- 가짜 세계 seed 42, 1,000개 (common.SEED, common.R). 나라를 빼면 남은 도입국끼리만 섞음
- version・stat을 결과를 보고 늘렸으므로 검사 수가 많음 → 한 칸 p에 큰 의미 두지 않고 방향만 봄
- 해석: '같은 대륙 쌍끼리 시기가 우연보다 가까움'까지. 따라 했다는 뜻 아님
시간: 30초 안팎
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))
from common import R, SEED, STRATA, _shuffles, _strata_labels, analysis_countries, load_nodes, use_font  # noqa: E402

L = ROOT / "layers"
OUT = ROOT / "analysis"
pairs = pd.read_csv(OUT / "stage2_pairs.csv")
cont = pd.read_csv(L / "region" / "layer_continent_groups.csv").set_index("iso3").group
CONTS = sorted(cont.dropna().unique())
OTHERS = ["igo", "language", "colony", "income", "trade"]

base = load_nodes()
t46 = pd.read_csv(L / "income" / "year_check.csv")
VERSIONS = {
    "all": base.index[[False] * len(base)],
    "unsure46": t46[t46.status != "맞음"].iso3,
    "excl46": t46.iso3,
    "health_obj": base.index[base.health_obj != 1],
    "since2014": base.index[base.year_imp < 2014],
}


def version_nodes(ver):
    nd = base.copy()
    nd.loc[list(VERSIONS[ver]), "in_analysis"] = 0
    return nd


def adopter_pairs(nd):
    ad = list(analysis_countries(nd))
    pos = {c: i for i, c in enumerate(ad)}
    sub = pairs[pairs.src.isin(pos) & pairs.dst.isin(pos)].copy()
    same = (sub.continent == 1).to_numpy()
    sub["cont_label"] = np.where(same, sub.src.map(cont), "")
    assert (sub.loc[same, "src"].map(cont) == sub.loc[same, "dst"].map(cont)).all()
    return ad, sub, sub.src.map(pos).to_numpy(), sub.dst.map(pos).to_numpy()


# ---------- 1. 1단계 대륙 통계 여러 방식 ----------
def check(ver, strata=None):
    nd = version_nodes(ver)
    ad, sub, i, j = adopter_pairs(nd)
    same = (sub.continent == 1).to_numpy()
    lab = sub.cont_label.to_numpy()
    ci, cj = i[same], j[same]
    lab_s = lab[same]
    n = len(ad)
    cnt = np.zeros(n)
    np.add.at(cnt, ci, 1)
    np.add.at(cnt, cj, 1)
    has = cnt > 0

    def stats(yy):
        d = np.abs(yy[ci] - yy[cj])
        s = np.zeros(n)
        np.add.at(s, ci, d)
        np.add.at(s, cj, d)
        per = {c: d[lab_s == c].mean() if (lab_s == c).any() else np.nan for c in CONTS}
        out = {"pair": d.mean(), "country": (s[has] / cnt[has]).mean(),
               "continent_equal": np.nanmean(list(per.values())), "no_Africa": d[lab_s != "Africa"].mean()}
        out.update(per)
        return out

    yy = nd.loc[ad, "year_imp"].to_numpy(float)
    real = stats(yy)
    fake = {k: [] for k in real}
    for ys in _shuffles(yy, R, SEED, _strata_labels(nd, ad, strata)):
        for k, v in stats(ys).items():
            fake[k].append(v)
    rows = []
    for k in real:
        f = np.array(fake[k])
        if k in CONTS:
            m = lab_s == k
            n_ad, n_pairs = len(set(ci[m]) | set(cj[m])), int(m.sum())
        elif k == "no_Africa":
            m = lab_s != "Africa"
            n_ad, n_pairs = len(set(ci[m]) | set(cj[m])), int(m.sum())
        else:
            n_ad, n_pairs = int(has.sum()), int(same.sum())
        ok = not np.isnan(real[k])
        rows.append(dict(version=ver, shuffle=strata or "basic", stat=k, n_adopters=n_ad, n_pairs=n_pairs,
                         mean_gap_real=round(real[k], 3) if ok else np.nan,
                         mean_gap_fake_avg=round(np.nanmean(f), 3) if ok else np.nan,
                         p=round((np.sum(f <= real[k]) + 1) / (R + 1), 4) if ok else np.nan))
        DISTS[(ver, strata or "basic", k)] = (real[k], f)
    return rows


DISTS = {}   # (version, shuffle, stat) → (실제, 가짜 1,000개). 그림용
rows = []
for ver in VERSIONS:
    for s in [None, *STRATA] if ver == "all" else [None]:
        rows += check(ver, s)
res = pd.DataFrame(rows)
res.to_csv(OUT / "stage2_continent_check.csv", index=False)

# 1단계 결과와 같은지 확인 (all/basic pair = result_continent.csv ALL, 대륙별 = 그룹별)
r1 = pd.read_csv(L / "region" / "result_continent.csv").set_index("group")
chk = res[(res.version == "all") & (res.shuffle == "basic")].set_index("stat")
assert abs(chk.loc["pair", "p"] - r1.loc["ALL", "p"]) < 1e-9, "pair p가 result_continent.csv와 다름"
for c in CONTS:
    assert abs(chk.loc[c, "p"] - r1.loc[c, "p"]) < 1e-9, f"{c} p가 result_continent.csv와 다름"

print("[1. 대륙 1단계 여러 방식: p]")
wide = res.assign(run=res.version + "/" + res.shuffle).pivot(index="run", columns="stat", values="p")
print(wide.loc[res.assign(run=res.version + "/" + res.shuffle).run.unique(),
               ["pair", "country", "continent_equal", "no_Africa", *CONTS]].to_string())
print("\n[도입국 수]")
print(res[res.stat.isin(CONTS) & (res.shuffle == "basic")].pivot(index="version", columns="stat", values="n_adopters")
      .loc[list(VERSIONS)].to_string())


# ---------- 2. 2단계 대륙 몫을 대륙별로 ----------
def share_split(ver):
    nd = version_nodes(ver)
    ad, sub, i, j = adopter_pairs(nd)
    cols = {f"continent_{c}": (sub.cont_label == c).to_numpy(float) for c in CONTS}
    cols.update({k: sub[k].to_numpy(float) for k in OTHERS})
    keep = [k for k, v in cols.items() if v.sum() > 0]
    X = np.column_stack([np.ones(len(sub))] + [cols[k] for k in keep])
    P = np.linalg.pinv(X)
    yy = nd.loc[ad, "year_imp"].to_numpy(float)
    real = P @ np.abs(yy[i] - yy[j])
    fake = np.array([P @ np.abs(ys[i] - ys[j]) for ys in _shuffles(yy, R, SEED)])
    out = []
    for n, k in enumerate(keep, start=1):
        out.append(dict(version=ver, layer=k, n_adopters=len(ad), n_pairs_linked=int(cols[k].sum()),
                        coef=round(real[n], 3), coef_fake_avg=round(fake[:, n].mean(), 3),
                        p=round((np.sum(fake[:, n] <= real[n]) + 1) / (R + 1), 4)))
    return out


sh = pd.DataFrame([r for ver in VERSIONS for r in share_split(ver)])
sh.to_csv(OUT / "stage2_continent_share.csv", index=False)
print("\n[2. 2단계 몫, 대륙을 대륙별로 나눔: 계수 (p)]")
cell = sh.coef.map("{:+.2f}".format) + " (" + sh.p.map("{:.3f}".format) + ")"
print(sh.assign(cell=cell).pivot(index="layer", columns="version", values="cell")
      .loc[[f"continent_{c}" for c in CONTS] + OTHERS, list(VERSIONS)].to_string())
print("\n저장: analysis/stage2_continent_check.csv, analysis/stage2_continent_share.csv")

# ---------- 3. 그림: 대륙별 순열분포 (전체 / 건강 목적 세금만) ----------
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

use_font()   # 저장소 src/fonts/ Pretendard
INK, INK2, MUTED, FILL, LINE, SURF = "#0b0b0b", "#52514e", "#898781", "#d5d3cc", "#e34948", "#fcfcfb"
KO = {"Africa": "아프리카", "Asia": "아시아", "Oceania": "오세아니아", "Americas": "아메리카", "Europe": "유럽"}
ORDER = ["Africa", "Asia", "Oceania", "Americas", "Europe"]
ROWS = [("all", "전체 도입국"), ("health_obj", "건강 목적 세금만")]
lo = min(min(DISTS[(v, "basic", c)][1].min(), DISTS[(v, "basic", c)][0]) for v, _ in ROWS for c in ORDER)
hi = max(max(DISTS[(v, "basic", c)][1].max(), DISTS[(v, "basic", c)][0]) for v, _ in ROWS for c in ORDER)
bins = np.linspace(np.floor(lo), np.ceil(hi), 49)

fig, axes = plt.subplots(2, 5, figsize=(16, 6.2), sharex=True, facecolor=SURF)
for r, (ver, vlabel) in enumerate(ROWS):
    for k, c in enumerate(ORDER):
        ax = axes[r, k]
        ax.set_facecolor(SURF)
        real, f = DISTS[(ver, "basic", c)]
        row = res[(res.version == ver) & (res.shuffle == "basic") & (res.stat == c)].iloc[0]
        h, _, _ = ax.hist(f, bins=bins, color=FILL, edgecolor=SURF, linewidth=1)
        ax.vlines(real, 0, h.max() * 1.1, color=LINE, lw=2)   # 선은 글자 아래까지만
        ax.set_ylim(0, h.max() * 1.6)       # 글자 자리를 막대 위에 남김
        ax.text(0.02, 0.97, f"{KO[c]}  도입국 {row.n_adopters}, 쌍 {row.n_pairs}", transform=ax.transAxes,
                va="top", fontsize=10.5, color=INK, fontweight="bold")
        word = ("우연보다 가까움" if row.p < 0.05 else "경계" if row.p < 0.1
                else "우연보다 흩어짐" if row.p > 0.95 else "우연과 비슷")
        ax.text(0.02, 0.84, f"실제 {real:.1f}년 vs 가짜 {f.mean():.1f}년 → {word}\np {row.p:.3f}",
                transform=ax.transAxes, va="top", fontsize=9, color=INK2)
        ax.set_yticks([])
        for sp in ["top", "right", "left"]:
            ax.spines[sp].set_visible(False)
        ax.spines["bottom"].set_color(MUTED)
        ax.tick_params(colors=MUTED, labelsize=8.5)
    axes[r, 0].set_ylabel(vlabel, fontsize=11, color=INK, rotation=0, ha="right", va="center", labelpad=12)
fig.supxlabel("같은 대륙 도입국 쌍의 평균 도입 연도 차이 (년)", fontsize=9.5, color=INK2, y=0.045)
fig.suptitle("대륙별로 나누면: 아프리카는 우연보다 가깝고(아시아는 경계), 아메리카와 유럽은 우연보다 흩어짐. "
             "건강 목적 세금만 보면 아프리카는 사라지고 아시아가 남음",
             x=0.01, ha="left", fontsize=12, color=INK)
fig.text(0.01, 0.005, "회색 = 연도만 섞은 가짜 세계 1,000개, 빨간 선 = 실제. 모든 칸 x축 같음. "
         "선이 회색 왼쪽이면 같은 대륙끼리 도입 시기가 우연보다 가까움 (따라 했다는 뜻 아님)",
         fontsize=8.5, color=MUTED)
fig.tight_layout(rect=(0.02, 0.05, 1, 0.94))
fig.savefig(ROOT / "figures" / "stage2_대륙별_순열분포.png", dpi=150, facecolor=SURF)
print("저장: figures/stage2_대륙별_순열분포.png")
