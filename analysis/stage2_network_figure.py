"""
2단계 네트워크 그림 (A, 11/22): 계층 네트워크를 노드-링크로 (발표 2단계 슬라이드)
실행: python analysis/stage2_network_figure.py   (stage2.py・stage2_continent_check.py・stage2_1.py 다음, 몇 초)
설명: docs/analysis/stage2.md '네트워크 그림'

그림 1  figures/stage2_가중치네트워크.png
  - analysis/stage2_pairs.csv 도입국 쌍(both_adopters = 1) 중 n_shared >= K (6개 분야 중 같은 그룹인 수)
  - 왼쪽 = 실제 네트워크 (구조). 노드 색 2010~2023 + '2010 전' 한 칸. 배치: 대륙마다 원 위 한 자리 + 그 안에서 spring (seed 42)
  - 오른쪽 = 이 쌍들의 평균 도입 연도 차이 순열분포 (결과). common.stage1 + 같은 가짜 세계(SEED, R) 분포
    → analysis/stage2_network_figure.csv (world 0 = 실제, 1~1000 = 가짜), 그림은 이 CSV에서 읽음
  - 확인: 실제 평균 = stage2_shared_count.csv 3개・4개 이상 쌍 수 가중평균 (K = 3일 때, 다르면 멈춤)
  - 아래 한 줄: stage2_shared_count.csv 2개 줄
그림 2  figures/stage2_식민네트워크.png
  - layers/language/layer_colony_edges.csv, 도입국끼리만. 노드 색 = 대륙, 영국 그룹(colony_GBR・samecol_GBR) 선만 진하게
  - 아래 설명 숫자: analysis/stage2_share.csv (main・all・basic, 2단계 본 결과), analysis/stage2_1_results.csv (다른 대륙 쌍만, 영국 빼기),
    analysis/stage2_continent_share.csv (2014년 이후만)

- 기존 결과 CSV는 안 바꿈. 새 CSV는 analysis/stage2_network_figure.csv 하나
- 선은 '같은 그룹'이지 '영향'이 아님
"""
import json
import sys
from pathlib import Path

import matplotlib
import networkx as nx
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))
from common import R, SEED, _pair_index, _shuffles, analysis_countries, load_nodes, stage1, use_font  # noqa: E402

use_font()
FIG = ROOT / "figures"
INK, INK2, MUTED, EDGE = "#1a1a1a", "#52514e", "#6b6b6b", "#9a9893"
K = int(sys.argv[1]) if len(sys.argv) > 1 else 3          # 그림 1에 그릴 n_shared 하한 (4는 너무 휑해서 3, 11/22)
LAYOUT = sys.argv[2] if len(sys.argv) > 2 else "continent"   # "continent" | "spring"
YCMAP = matplotlib.colors.LinearSegmentedColormap.from_list("year", ["#d6e4f7", "#5e8fd8", "#0d366b"])   # 파랑 한 색조, 이를수록 연함
Y0, Y1 = 1990, 2023
CONT = ["Africa", "Asia", "Europe", "Americas", "Oceania"]
CONT_KO = {"Africa": "아프리카", "Asia": "아시아", "Europe": "유럽", "Americas": "아메리카", "Oceania": "오세아니아"}
CONT_COL = {"Africa": "#c2410c", "Asia": "#2a6fdb", "Europe": "#7c5cc4", "Americas": "#1f9e74", "Oceania": "#c99a06"}
LABEL = ["MEX", "GBR", "SAU", "ZAF"]
NUDGE = {"ZAF": (1.0, 0.8), "SAU": (0.9, -0.85)}   # 이름 위치 (점에서 떨어진 거리, 배치 단위)

nodes = load_nodes()
ac = list(analysis_countries(nodes))
year = nodes.year_imp
C = {r["cca3"]: r for r in json.load(open(ROOT / "data" / "raw" / "countries.json", encoding="utf-8"))}
cont = {c: C[c]["region"] for c in nodes.index}
ko = {c: C[c].get("translations", {}).get("kor", {}).get("common", c) for c in nodes.index}
ko.update({"SAU": "사우디", "ZAF": "남아공", "GBR": "영국", "ARE": "UAE"})


def continent_layout(G, seed=SEED, radius=3.0, spread=1.0):
    """대륙마다 원 위 한 자리 + 그 안에서 spring → 덩어리가 엉키지 않게. 덩어리 크기는 나라 수에 비례"""
    if LAYOUT == "spring":
        p = nx.spring_layout(G, seed=seed, k=0.6, iterations=300)
        return {n: (4.2 * x, 4.2 * y) for n, (x, y) in p.items()}
    pos = {}
    for k, ct in enumerate(CONT):
        ns = sorted(n for n in G if cont[n] == ct)            # 순서 고정 (subgraph는 set 순서라 실행마다 배치가 달라짐)
        sub = nx.Graph()
        sub.add_nodes_from(ns)
        sub.add_edges_from(sorted(tuple(sorted(e)) for e in G.subgraph(ns).edges))
        if not len(sub):
            continue
        ang = np.pi / 2 - 2 * np.pi * k / len(CONT)
        cx, cy = radius * np.cos(ang), radius * np.sin(ang)
        p = nx.spring_layout(sub, seed=seed, k=2.5 / np.sqrt(max(len(sub), 1)), iterations=300)
        r = spread * (0.6 + 1.2 * np.sqrt(len(sub) / 40))          # 아프리카(40) ≈ 1.8, 오세아니아 ≈ 1.0
        xy = np.array([p[n] for n in sub])
        xy = xy - np.median(xy, axis=0)
        d = np.linalg.norm(xy, axis=1)
        xy = xy / max(np.percentile(d, 80), 1e-9)                   # 빽빽한 덩어리(걸프 등)도 펴지게: 80% 거리를 1로
        d = np.linalg.norm(xy, axis=1, keepdims=True)
        xy = np.where(d > 1.25, xy / np.maximum(d, 1e-9) * 1.25, xy)                # 멀리 떨어진 나라는 덩어리 가장자리로
        for n, (x, y) in zip(sub, xy):
            pos[n] = (cx + r * x, cy + r * y)
    return pos


def p_txt(p):
    return f"p {p:.3f}" if p >= 0.001 else "p < 0.001"


# ---------- 그림 1. 가중치 네트워크 (왼쪽 구조) + 순열분포 (오른쪽 결과) ----------
pairs = pd.read_csv(ROOT / "analysis" / "stage2_pairs.csv")
E = pairs[(pairs.both_adopters == 1) & (pairs.n_shared >= K)]
G = nx.Graph()
G.add_weighted_edges_from(E[["src", "dst", "n_shared"]].itertuples(index=False))
pos = continent_layout(G)
real = dict(zip(ac, year.loc[ac].to_numpy()))

# 숫자: common.stage1 (쌍 전체 한 묶음) + 같은 가짜 세계(SEED, R, 도입국끼리 연도 섞기)의 분포 → CSV
edges = E[["src", "dst"]].assign(group=f"n_shared>={K}")
s1 = stage1(edges, nodes, by_group=False).iloc[0]
ac_i, pidx, e_i = _pair_index(edges, nodes)
i, j = e_i.src.map(pidx).to_numpy(), e_i.dst.map(pidx).to_numpy()
y = nodes.loc[ac_i, "year_imp"].to_numpy(float)
gap_real = float(np.abs(y[i] - y[j]).mean())
dist = np.array([np.abs(ys[i] - ys[j]).mean() for ys in _shuffles(y, R, SEED)])
p_dist = (np.sum(dist <= gap_real) + 1) / (R + 1)
assert round(gap_real, 2) == s1.mean_gap_real and round(dist.mean(), 2) == s1.mean_gap_fake_avg and round(p_dist, 4) == s1.p, \
    "순열분포가 stage1과 다름"
sc = pd.read_csv(ROOT / "analysis" / "stage2_shared_count.csv")
sc = sc[sc.version == "all"].set_index("n_shared")
if K == 3:   # 확인: 3개(387쌍)・4개 이상(232쌍) 줄의 쌍 수 가중평균과 같아야 함
    w = sc.loc[["3", "4+"]]
    chk = float((w.n_pairs * w.mean_gap_real).sum() / w.n_pairs.sum())
    assert int(w.n_pairs.sum()) == len(i) and abs(chk - gap_real) < 0.01, f"실제 평균 {gap_real:.3f} ≠ 가중평균 {chk:.3f}"
out_csv = ROOT / "analysis" / "stage2_network_figure.csv"
pd.concat([
    pd.DataFrame(dict(world=[0], kind="real", n_pairs=len(i), n_countries=G.number_of_nodes(), mean_gap=[round(gap_real, 4)],
                      mean_gap_fake_avg=[round(dist.mean(), 4)], p=[round(p_dist, 4)])),
    pd.DataFrame(dict(world=np.arange(1, R + 1), kind="fake", n_pairs=len(i), n_countries=G.number_of_nodes(),
                      mean_gap=np.round(dist, 4))),
]).to_csv(out_csv, index=False)

# 그림은 CSV에서 읽음
fc = pd.read_csv(out_csv)
rr = fc[fc.kind == "real"].iloc[0]
fk = fc.loc[fc.kind == "fake", "mean_gap"].to_numpy()

# 노드 색: 2010 전 한 칸 + 2010~2023 해마다 (도입국 절반이 2015~2018에 몰려서 범위를 좁힘)
YRS = list(range(2010, 2024))
cols = ["#e4e2dc"] + [matplotlib.colors.to_hex(c) for c in
                      matplotlib.colors.LinearSegmentedColormap.from_list("y", ["#b9cff0", "#4f86d6", "#0b2e5e"])(np.linspace(0, 1, len(YRS)))]
YC = matplotlib.colors.ListedColormap(cols)
YN = matplotlib.colors.BoundaryNorm([2006.5] + [v - 0.5 for v in YRS] + [2023.5], YC.N)   # '2010 전' 칸은 3년 폭으로 넓게
ycol = {n: 2008 if real[n] < 2010 else min(real[n], 2023) for n in G}

fig = plt.figure(figsize=(14, 7.4), facecolor="white")
gs = fig.add_gridspec(1, 2, width_ratios=[1.45, 1], left=0.01, right=0.985, top=0.83, bottom=0.16, wspace=0.06)
ax = fig.add_subplot(gs[0])
ax.set_facecolor("white")
for a_, b_, d in G.edges(data=True):
    (x1, y1), (x2, y2) = pos[a_], pos[b_]
    ax.plot([x1, x2], [y1, y2], color=EDGE, alpha=0.4, lw=0.5 + 0.45 * (d["weight"] - K), zorder=1, solid_capstyle="round")
xs, ys_ = zip(*[pos[n] for n in G])
ax.scatter(xs, ys_, s=46, c=[ycol[n] for n in G], cmap=YC, norm=YN, lw=0.4, edgecolors="white", zorder=3)
for c in LABEL:          # 이름은 덩어리 바깥 옆으로 빼고 가는 지시선
    if c in pos:
        xs_c = [pos[n][0] for n in G if cont[n] == cont[c]]
        cx = np.mean(xs_c)
        side = np.sign(cx) if abs(cx) > 0.5 else np.sign(pos[c][0] - cx)
        tx = (max(xs_c) if side > 0 else min(xs_c)) + 0.35 * side
        ty = pos[c][1]
        if c in NUDGE:
            tx, ty = pos[c][0] + NUDGE[c][0], pos[c][1] + NUDGE[c][1]
            side = np.sign(NUDGE[c][0])
        ax.annotate(ko[c], pos[c], xytext=(tx, ty), textcoords="data", fontsize=10, color=INK, zorder=4,
                    ha="left" if side > 0 else "right", va="center",
                    arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6, shrinkA=0, shrinkB=2))
allxy = np.array([pos[n] for n in G])
mid = allxy.mean(axis=0)
lab_xy = []
for ct in CONT:          # 대륙 글자: 그 대륙 노드 무게중심에서 전체 중심 반대쪽(바깥)으로, 덩어리 끝 + 여백
    xy = np.array([pos[n] for n in G if cont[n] == ct])
    if not len(xy):
        continue
    cen = xy.mean(axis=0)
    u = (cen - mid) / max(np.linalg.norm(cen - mid), 1e-9)
    reach = max(float(((xy - cen) @ u).max()), 0.3)
    lx, ly = cen + u * (reach + 0.75)
    ax.text(lx, ly, CONT_KO[ct], ha="center", va="center", fontsize=11, color=MUTED, fontweight="bold")
    lab_xy.append((lx, ly))
bb = np.vstack([allxy, lab_xy])
ax.set_aspect("equal")
ax.axis("off")
ax.set_xlim(bb[:, 0].min() - 0.9, bb[:, 0].max() + 0.9)
ax.set_ylim(bb[:, 1].min() - 0.4, bb[:, 1].max() + 0.4)
ax.set_title(f"실제 네트워크: 도입국 {G.number_of_nodes()}개국, 쌍 {G.number_of_edges()}개 (선 굵기 = 같은 그룹인 분야 수)",
             loc="left", fontsize=11, color=INK, pad=10)
cax = fig.add_axes([0.16, 0.085, 0.27, 0.018])
cb = fig.colorbar(matplotlib.cm.ScalarMappable(norm=YN, cmap=YC), cax=cax, orientation="horizontal", spacing="proportional")
cb.outline.set_visible(False)
cb.set_ticks([2008, 2010, 2015, 2020, 2023])
cb.set_ticklabels(["2010 전", "2010", "2015", "2020", "2023"])
cb.ax.tick_params(labelsize=8.5, colors=INK2, length=0)
cax.set_title("도입 연도 (진할수록 늦게)", fontsize=9, color=INK2, pad=4)

# 오른쪽: 순열분포 (stage2_대륙별_순열분포.png와 같은 색・선)
FILL, LINE = "#d5d3cc", "#e34948"
bx = fig.add_subplot(gs[1])
bx.set_facecolor("white")
lo, hi = min(fk.min(), rr.mean_gap), max(fk.max(), rr.mean_gap)
bins = np.linspace(np.floor(lo * 2) / 2, np.ceil(hi * 2) / 2, 41)
h, _, _ = bx.hist(fk, bins=bins, color=FILL, edgecolor="white", linewidth=1)
bx.vlines(rr.mean_gap, 0, h.max() * 1.1, color=LINE, lw=2.2)
bx.set_ylim(0, h.max() * 1.55)
bx.text(rr.mean_gap, h.max() * 1.13, f"실제 {rr.mean_gap:.2f}년", color=LINE, fontsize=11, fontweight="bold", ha="center", va="bottom")
bx.text(0.98, 0.97, f"가짜 세계 1,000개 평균 {rr.mean_gap_fake_avg:.2f}년\n{p_txt(rr.p)} → 우연보다 가까움" if rr.p < 0.05 else
        f"가짜 세계 1,000개 평균 {rr.mean_gap_fake_avg:.2f}년\n{p_txt(rr.p)}",
        transform=bx.transAxes, ha="right", va="top", fontsize=10, color=INK2, linespacing=1.5)
bx.set_title(f"이 {int(rr.n_pairs)}쌍의 평균 도입 연도 차이: 실제 vs 가짜", loc="left", fontsize=11, color=INK, pad=6)
bx.set_xlabel("평균 도입 연도 차이 (년)  ·  회색 = 연도만 섞은 가짜 세계 1,000개, 빨간 선 = 실제", fontsize=9, color=INK2, labelpad=8)
bx.set_yticks([])
for sp in ["top", "right", "left"]:
    bx.spines[sp].set_visible(False)
bx.spines["bottom"].set_color(MUTED)
bx.tick_params(colors=MUTED, labelsize=9)

r2 = sc.loc["2"]
fig.text(0.015, 0.965, "여러 분야에서 같은 그룹인 나라끼리는 도입 시기가 우연보다 가까웠음", fontsize=14, fontweight="bold", color=INK, va="top")
fig.text(0.015, 0.92, f"왼쪽: 선 = 6개 분야 중 {K}개 이상 같은 그룹  /  오른쪽: 이 쌍들의 도입 연도 차이, 실제 vs 가짜 세계 1,000개",
         fontsize=10.5, color=INK2, va="top")
fig.text(0.015, 0.018, f"같은 그룹 분야가 2개 이상이면 우연보다 도입 시기가 가까움 (2개 {r2.mean_gap_real:.2f}년 vs {r2.mean_gap_fake_avg:.2f}년, {p_txt(r2.p)})",
         fontsize=9.5, color=MUTED, va="bottom")
out1 = FIG / "stage2_가중치네트워크.png"
fig.savefig(out1, dpi=200, facecolor="white")
plt.close(fig)
print(f"그림 1: n_shared >= {K}, {len(i)}쌍 {G.number_of_nodes()}개국, 실제 {gap_real:.3f} vs 가짜 평균 {dist.mean():.3f}, p {p_dist:.4f}"
      f" → {out1.relative_to(ROOT)}, {out_csv.relative_to(ROOT)}")

# ---------- 그림 2. 식민 계층 ----------
col = pd.read_csv(ROOT / "layers" / "language" / "layer_colony_edges.csv")
acs = set(ac)
col = col[col.src.isin(acs) & col.dst.isin(acs)].copy()
col["gbr"] = col.group.str.endswith("_GBR")
gbr_pairs = {tuple(sorted(p)) for p in col.loc[col.gbr, ["src", "dst"]].itertuples(index=False)}
H = nx.Graph()
H.add_edges_from(col[["src", "dst"]].itertuples(index=False))
# 원형 배치: 대륙별로 원 둘레에 나란히 (같은 종주국 그룹은 서로 다 이어져 있어 spring이면 한 점으로 겹침)
grp = {}
for r in col.itertuples(index=False):
    for c in (r.src, r.dst):
        grp.setdefault(c, r.group.split("_", 1)[1])
order = sorted(H, key=lambda c: (CONT.index(cont[c]), grp[c] != "GBR", grp[c], c))
gap = 2.0                                                   # 대륙 사이 빈칸 (나라 몇 칸)
slots, t = {}, 0.0
for i, c in enumerate(order):
    if i and cont[c] != cont[order[i - 1]]:
        t += gap
    slots[c] = t
    t += 1
ang = {c: np.pi / 2 - 2 * np.pi * v / t for c, v in slots.items()}
hpos = {c: (4.0 * np.cos(a), 4.0 * np.sin(a)) for c, a in ang.items()}
n_cross_gbr = sum(cont[a] != cont[b] for a, b in gbr_pairs)

s21 = pd.read_csv(ROOT / "analysis" / "stage2_1_results.csv")
nogbr = s21[(s21.layer == "language/colony") & (s21.variant == "no_gbr") & (s21.test == "stage1_basic")].iloc[0]
main = pd.read_csv(ROOT / "analysis" / "stage2_share.csv")
c_all = main[(main.model == "main") & (main.version == "all") & (main.shuffle == "basic") & (main.layer == "colony")].iloc[0]
share = pd.read_csv(ROOT / "analysis" / "stage2_continent_share.csv").set_index(["version", "layer"])
c_14 = share.loc[("since2014", "colony")]

GBR_COL = "#e11d1d"     # 영국 그룹 선: 진한 빨강 (11/22)
OTHER_COL = "#1e3a8a"   # 다른 종주국 선: 빨강과 대비되는 남색, 흐리게 (11/22)
fig, ax = plt.subplots(figsize=(10.5, 8.2), facecolor="white")
ax.set_facecolor("white")
for a, b in H.edges:
    g = tuple(sorted((a, b))) in gbr_pairs
    (x1, y1), (x2, y2) = hpos[a], hpos[b]
    ax.plot([x1, x2], [y1, y2], color=GBR_COL if g else OTHER_COL, alpha=0.32 if g else 0.22,
            lw=0.7 if g else 0.6, zorder=2 if g else 1, solid_capstyle="round")
for ct in CONT:
    ns = [n for n in H if cont[n] == ct]
    xs, ys = zip(*[hpos[n] for n in ns])
    ax.scatter(xs, ys, s=38, color=CONT_COL[ct], lw=0, zorder=3)
for c in ["GBR", "FRA", "ESP", "PRT", "IND", "ZAF", "MEX", "SAU"]:
    if c in hpos:
        a = ang[c]
        ax.text(4.3 * np.cos(a), 4.3 * np.sin(a), ko[c], fontsize=9, color=INK, zorder=4, va="center",
                ha="left" if np.cos(a) >= 0 else "right")
for ct in CONT:
    a = np.mean([ang[c] for c in H if cont[c] == ct])
    ax.text(5.15 * np.cos(a), 5.15 * np.sin(a), CONT_KO[ct], fontsize=11, color=CONT_COL[ct], fontweight="bold",
            ha="center", va="center")
ax.set_aspect("equal")
ax.axis("off")
ax.set_xlim(-5.8, 5.8)
ax.set_ylim(-5.6, 5.6)
handles = [Line2D([], [], color=GBR_COL, lw=1.6, alpha=0.8, label="영국 그룹 (영국과 옛 식민지, 옛 식민지끼리)"),
            Line2D([], [], color=OTHER_COL, lw=1.4, alpha=0.4, label="다른 종주국 그룹")]
fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.1), ncol=2, frameon=False, fontsize=9.5,
           columnspacing=1.4, handletextpad=0.4)
fig.text(0.015, 0.965, f"식민 계층: 도입국 {H.number_of_nodes()}개국, 쌍 {H.number_of_edges()}개 중 영국 그룹 {len(gbr_pairs)}개",
         fontsize=14, fontweight="bold", color=INK, va="top")
fig.text(0.015, 0.925, f"원 둘레 = 대륙별로 모은 도입국 (색 = 대륙). 영국 그룹 선 {len(gbr_pairs)}개 중 {n_cross_gbr}개가 대륙을 넘음 → 영국 옛 식민지끼리 대륙을 넘어 묶임",
         fontsize=10, color=INK2, va="top")
fig.text(0.015, 0.012,
         f"2단계 식민 몫 {c_all.coef:+.2f}년 ({p_txt(c_all.p)}, stage2_share.csv). 영국 그룹을 빼면 다른 대륙 쌍만(2-1단계, {int(nogbr.n_adopter_pairs)}쌍) {nogbr.gap_real:.2f}년 vs 가짜 {nogbr.gap_fake_avg:.2f}년 ({p_txt(nogbr.p)}, stage2_1_results.csv) → 식민 묶임은 영국 그룹에 기댐\n"
         f"2014년 이후 도입국만 보면 식민 몫 {c_14.coef:+.2f}년 ({p_txt(c_14.p)}, stage2_continent_share.csv) → 2014년 전 도입국까지 넣어야 나옴. "
         "같은 그룹끼리 도입 시기가 비슷했다는 뜻이지 따라 했다는 뜻이 아님",
         fontsize=8, color=MUTED, va="bottom", linespacing=1.6)
fig.subplots_adjust(left=0.01, right=0.99, top=0.89, bottom=0.15)
out2 = FIG / "stage2_식민네트워크.png"
fig.savefig(out2, dpi=200, facecolor="white")
plt.close(fig)
print(f"그림 2: {H.number_of_nodes()}개국, 쌍 {H.number_of_edges()}개, 영국 그룹 {len(gbr_pairs)}개 (대륙 넘음 {n_cross_gbr}) → {out2.relative_to(ROOT)}")
