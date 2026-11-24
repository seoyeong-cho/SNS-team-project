"""
투영・멀티플렉스 예시 그림 (D, 11/24): 4개국(프랑스・사우디・세네갈・모로코)으로 네트워크 만드는 과정을 한 장에
실행: python layers/trade/example_figure.py   (2~5와 analysis/stage2.py 다음, 몇 초)
결과: figures/method_투영멀티플렉스_예시.png (발표 '네트워크 만들기' 슬라이드)

① 이분 네트워크: 나라 ↔ 공용어 (layers/language/layer_language_groups.csv)
② 이분 투영: 같은 언어를 쓰면 연결 (common.groups_to_edges) + 인접행렬
③ 멀티플렉스: 같은 나라 위에 언어 층・식민 층 (layers/language/layer_colony_edges.csv)
④ 가중치 네트워크: 선 굵기 = 6개 분야 중 같은 그룹인 수 n_shared (analysis/stage2_pairs.csv, 서영 2단계 그림과 같은 기준)

- 숫자・연결은 전부 파일에서 읽음. 손으로 적은 건 나라・언어・분야의 한글 이름과 그림 배치뿐
- 확인: ②의 투영 결과 = 언어 계층 엣지 파일의 4개국 부분, ④의 언어・식민 열 = ②・③ (다르면 멈춤)
- 무역(k = 5)은 이 4개국 사이에 연결 없음 → ④에 그대로 0으로 둠 (11/24 승아 결정)
- 분야 색: 대륙・지역기구・언어・식민・소득・무역 순서로 고정 (dataviz 기본 팔레트 1~6번, 색각이상 검사 통과).
  대비가 낮은 색이 있어서 선마다 분야 이름을 직접 적음
- 선은 '같은 그룹'이지 '영향'이 아님
"""
import sys
from pathlib import Path

import matplotlib
import networkx as nx
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Polygon  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "src"))
from common import groups_to_edges, load_nodes, use_font  # noqa: E402

L = ROOT / "layers"
OUT = ROOT / "figures" / "method_투영멀티플렉스_예시.png"

C4 = ["FRA", "SAU", "SEN", "MAR"]
KO = {"FRA": "프랑스", "SAU": "사우디", "SEN": "세네갈", "MAR": "모로코"}
LANG_KO = {"French": "프랑스어", "Arabic": "아랍어", "Tamazight": "타마지트어"}
FIELDS = ["continent", "igo", "language", "colony", "income", "trade"]     # stage2.py MAIN 순서
FIELD_KO = dict(continent="대륙", igo="지역기구", language="언어", colony="식민", income="소득", trade="무역")
FIELD_COL = dict(continent="#2a78d6", igo="#eb6834", language="#1baf7a",
                 colony="#eda100", income="#e87ba4", trade="#008300")
INK, INK2, MUTED, LINE, SURF, NODE = "#1a1a1a", "#52514e", "#898781", "#c9c8c2", "#fcfcfb", "#f1f0ec"

# 나라 자리: 사각형. 연결 없는 사우디–세네갈을 마주 보는 꼭짓점에 둬서 선이 안 겹치게
POS = {"FRA": (0.0, 1.0), "SAU": (1.0, 1.0), "SEN": (0.0, 0.0), "MAR": (1.0, 0.0)}


def pair(a, b):
    return tuple(sorted((a, b)))


# ---------- 데이터 ----------
nodes = load_nodes()
groups = pd.read_csv(L / "language" / "layer_language_groups.csv")
g4 = groups[groups.iso3.isin(C4)].sort_values(["group", "iso3"])
lang_edges = groups_to_edges(g4, nodes)                               # ② 이분 투영
lang_pairs = {pair(a, b) for a, b in zip(lang_edges.src, lang_edges.dst)}

full = pd.read_csv(L / "language" / "layer_language_edges.csv")
full4 = {pair(a, b) for a, b in zip(full.src, full.dst) if a in C4 and b in C4}
assert lang_pairs == full4, f"투영 결과가 언어 계층 파일과 다름: {lang_pairs} vs {full4}"

col = pd.read_csv(L / "language" / "layer_colony_edges.csv")
col4 = col[col.src.isin(C4) & col.dst.isin(C4)]
col_pairs = {pair(a, b) for a, b in zip(col4.src, col4.dst)}

sp = pd.read_csv(ROOT / "analysis" / "stage2_pairs.csv")
sp4 = sp[sp.src.isin(C4) & sp.dst.isin(C4)].copy()
assert len(sp4) == 6, "4개국 쌍 6개가 stage2_pairs.csv에 다 있어야 함"
assert {pair(a, b) for a, b, v in zip(sp4.src, sp4.dst, sp4.language) if v} == lang_pairs, "④ 언어 열이 ②와 다름"
assert {pair(a, b) for a, b, v in zip(sp4.src, sp4.dst, sp4.colony) if v} == col_pairs, "④ 식민 열이 ③과 다름"
assert (sp4[FIELDS].sum(axis=1) == sp4.n_shared).all(), "n_shared = 6개 분야 합이어야 함"

G = nx.Graph()
G.add_nodes_from(C4)
G.add_edges_from(lang_pairs)
A = nx.to_numpy_array(G, nodelist=C4, dtype=int)

print("언어 그룹:", g4.groupby("group").iso3.apply(list).to_dict())
print("언어 투영:", sorted(lang_pairs))
print("식민:", sorted(col_pairs))
print(sp4[["src", "dst"] + FIELDS + ["n_shared"]].to_string(index=False))

# ---------- 그림 ----------
use_font()
plt.rcParams.update({"font.size": 10, "text.color": INK})
fig, axes = plt.subplots(1, 4, figsize=(17, 5.4), facecolor=SURF)
for ax in axes:
    ax.set_facecolor(SURF)
    ax.set_axis_off()


def title(ax, num, text, sub):
    ax.text(0.0, 1.10, f"{num} {text}", transform=ax.transAxes, fontsize=13.5, fontweight="bold", va="bottom")
    ax.text(0.0, 1.035, sub, transform=ax.transAxes, fontsize=9.5, color=INK2, va="bottom")


def node(ax, xy, label, r=0.13, fs=10.5):
    ax.add_patch(plt.Circle(xy, r, facecolor=NODE, edgecolor=INK2, lw=1.2, zorder=3))
    ax.text(*xy, label, ha="center", va="center", fontsize=fs, fontweight="bold", zorder=4)


def edge(ax, a, b, color, lw=2.5, z=1, ls="-"):
    ax.plot([a[0], b[0]], [a[1], b[1]], color=color, lw=lw, solid_capstyle="round", ls=ls, zorder=z)


def mid_label(ax, a, b, text, dx=0.0, dy=0.0, fs=9):
    x, y = (a[0] + b[0]) / 2 + dx, (a[1] + b[1]) / 2 + dy
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, color=INK2, zorder=5,
            bbox=dict(boxstyle="round,pad=0.2", fc=SURF, ec="none"))


# ① 이분 네트워크
ax = axes[0]
title(ax, "①", "이분 네트워크", "나라 ↔ 공용어 (두 종류 노드)")
order_c = ["FRA", "SEN", "MAR", "SAU"]
lang_order = ["French", "Tamazight", "Arabic"]
cy = dict(zip(order_c, [0.92, 0.64, 0.36, 0.08]))
ly = dict(zip(lang_order, [0.78, 0.40, 0.18]))
for c, lg in zip(g4.iso3, g4.group):
    edge(ax, (0.12, cy[c]), (0.82, ly[lg]), LINE, lw=1.8)
for c in order_c:
    node(ax, (0.12, cy[c]), KO[c], r=0.105, fs=9.5)
for lg in lang_order:
    ax.add_patch(plt.Rectangle((0.69, ly[lg] - 0.055), 0.27, 0.11, facecolor="#e6f6ef", edgecolor=FIELD_COL["language"],
                               lw=1.2, zorder=3))
    ax.text(0.825, ly[lg], LANG_KO[lg], ha="center", va="center", fontsize=9.5, zorder=4)
ax.text(0.12, -0.08, "나라", ha="center", fontsize=9, color=MUTED)
ax.text(0.825, -0.08, "언어 그룹", ha="center", fontsize=9, color=MUTED)
ax.set_xlim(-0.05, 1.02)
ax.set_ylim(-0.12, 1.02)
ax.set_aspect("equal")

# ② 이분 투영 + 인접행렬
ax = axes[1]
title(ax, "②", "이분 투영", "같은 언어 그룹이면 나라끼리 연결")
S, OX, OY = 0.62, 0.19, 0.60          # 사각형 크기・위치 (위쪽)
P2 = {c: (OX + x * S, OY + y * 0.32) for c, (x, y) in POS.items()}
for a, b in sorted(lang_pairs):
    edge(ax, P2[a], P2[b], FIELD_COL["language"], lw=3)
lang_name = {pair(a, b): LANG_KO[g] for a, b, g in zip(lang_edges.src, lang_edges.dst, lang_edges.group)}
for (a, b), t in lang_name.items():
    mid_label(ax, P2[a], P2[b], t, dy=0.0)
for c in C4:
    node(ax, P2[c], KO[c], r=0.085, fs=9)
# 인접행렬
cell, mx, my = 0.09, 0.40, -0.10
ax.text(mx + 2 * cell, my + 4 * cell + 0.10, "인접행렬 (1 = 연결)", ha="center", fontsize=9, color=MUTED)
for i, a in enumerate(C4):
    ax.text(mx - 0.02, my + (3.5 - i) * cell, KO[a], ha="right", va="center", fontsize=8.5, color=INK2)
    ax.text(mx + (i + 0.5) * cell, my + 4 * cell + 0.012, KO[a], ha="center", va="bottom", fontsize=7, color=INK2,
            rotation=0)
    for j, b in enumerate(C4):
        v = A[i, j]
        ax.add_patch(plt.Rectangle((mx + j * cell, my + (3 - i) * cell), cell, cell,
                                   facecolor=FIELD_COL["language"] if v else SURF, alpha=0.85 if v else 1,
                                   edgecolor=LINE, lw=0.8))
        ax.text(mx + (j + 0.5) * cell, my + (3.5 - i) * cell, str(v), ha="center", va="center", fontsize=9,
                color="white" if v else MUTED, fontweight="bold" if v else "normal")
ax.set_xlim(-0.05, 1.02)
ax.set_ylim(-0.12, 1.02)
ax.set_aspect("equal")

# ③ 멀티플렉스 (층 2개)
ax = axes[2]
title(ax, "③", "멀티플렉스", "같은 나라 위에 분야마다 층 하나")


def sheet(c):
    """평행사변형 층 위 좌표: 사각형을 기울여 겹친 층처럼"""
    return lambda x, y: (0.08 + 0.60 * x + 0.20 * y, c + 0.26 * y)


layers3 = [("language", lang_pairs, 0.60), ("colony", col_pairs, 0.08)]
proj = {}
for f, pairs, base in layers3:
    tf = sheet(base)
    corners = [tf(-0.12, -0.18), tf(1.12, -0.18), tf(1.12, 1.18), tf(-0.12, 1.18)]
    ax.add_patch(Polygon(corners, closed=True, facecolor=FIELD_COL[f], alpha=0.07, edgecolor=FIELD_COL[f], lw=1.2,
                         zorder=0))
    ax.text(-0.03, corners[3][1] + 0.015, f"{FIELD_KO[f]} 층", fontsize=10.5, fontweight="bold",
            color=INK, va="bottom")
    proj[f] = {c: tf(*POS[c]) for c in C4}
for c in C4:                                       # 같은 나라끼리 층 사이 점선
    edge(ax, proj["language"][c], proj["colony"][c], LINE, lw=1, z=0.5, ls=(0, (2, 2)))
for f, pairs, _ in layers3:
    for a, b in sorted(pairs):
        edge(ax, proj[f][a], proj[f][b], FIELD_COL[f], lw=2.6)
    for c in C4:
        node(ax, proj[f][c], KO[c], r=0.062, fs=7.5)
ax.text(0.5, -0.08, "점선 = 같은 나라. 프랑스–세네갈은 두 층 모두 연결", ha="center", fontsize=9, color=MUTED)
ax.set_xlim(-0.05, 1.02)
ax.set_ylim(-0.12, 1.02)
ax.set_aspect("equal")

# ④ 가중치 네트워크
ax = axes[3]
title(ax, "④", "가중치 네트워크", "선 굵기 = 6개 분야 중 같은 그룹인 수")
S4, O4x, O4y = 0.70, 0.15, 0.22
P4 = {c: (O4x + x * S4, O4y + y * S4) for c, (x, y) in POS.items()}
for r in sp4.itertuples():
    if r.n_shared == 0:
        continue
    fl = [FIELD_KO[f] for f in FIELDS if getattr(r, f)]
    edge(ax, P4[r.src], P4[r.dst], INK2, lw=2.2 * r.n_shared)
    a, b = P4[r.src], P4[r.dst]
    vertical = abs(a[0] - b[0]) < 1e-9
    mid_label(ax, a, b, f"{r.n_shared}  ({'・'.join(fl)})", dx=0.0 if not vertical else 0.0, fs=8.5)
for c in C4:
    node(ax, P4[c], KO[c], r=0.085, fs=9)
zero = [f"{KO[r.src]}–{KO[r.dst]}" for r in sp4.itertuples() if r.n_shared == 0]
ax.text(0.5, 0.02, f"{', '.join(zero)}: 0 (같은 그룹 없음)", ha="center", fontsize=9, color=MUTED)
ax.text(0.5, -0.08, "6개 분야 = 대륙・지역기구・언어・식민・소득・무역 (무역은 이 4개국 사이 0)", ha="center", fontsize=8.5,
        color=MUTED)
ax.set_xlim(-0.05, 1.02)
ax.set_ylim(-0.12, 1.02)
ax.set_aspect("equal")

for i in range(3):                                   # 칸 사이 화살표
    fig.patches.append(matplotlib.patches.FancyArrowPatch(
        (0.255 + i * 0.2425, 0.47), (0.275 + i * 0.2425, 0.47), transform=fig.transFigure,
        arrowstyle="-|>", mutation_scale=16, color=MUTED))

fig.text(0.5, 0.015, "선은 '같은 그룹'이라는 뜻이지 '영향'이 아님. 자료: 언어 CIA World Factbook, 식민 ICOW, 6개 분야 analysis/stage2_pairs.csv",
         ha="center", fontsize=8.5, color=MUTED)
plt.subplots_adjust(left=0.02, right=0.99, top=0.80, bottom=0.07, wspace=0.12)
OUT.parent.mkdir(exist_ok=True)
fig.savefig(OUT, dpi=200, facecolor=SURF)
print("저장:", OUT.relative_to(ROOT))
