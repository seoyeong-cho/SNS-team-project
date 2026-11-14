"""
확산 그래프 & 확산 경로 샘플 (Colab에서 그대로 실행 가능)
필요 파일: SSB-Tax-Database-Aug23.csv, countries.json (같은 폴더)
"""
import json, numpy as np, pandas as pd, networkx as nx
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

# ---- 한글 글꼴 (Colab: !apt -qq install fonts-nanum 후 'NanumGothic') ----
for name in ["Apple SD Gothic Neo", "Noto Sans CJK KR", "NanumGothic"]:
    if any(name in f.name for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = name; break
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#86868b", "axes.labelcolor": "#424245",
                     "xtick.color": "#6e6e73", "ytick.color": "#6e6e73", "font.size": 10})
INK, MID, LIGHT, ACCENT = "#1d1d1f", "#86868b", "#d2d2d7", "#2a6fdb"

# ---- 1. 데이터: 나라별 최초 도입 연도 ----
d = pd.read_csv("SSB-Tax-Database-Aug23.csv", encoding="utf-8-sig").dropna(subset=["jurisdiction"])
d = d[d.level.str.strip() == "National"].replace({"country_code": {"PERU": "PER"}})
year = d.groupby("country_code").year_imp.min()
C = {x["cca3"]: x for x in json.load(open("countries.json"))}
name_ko = {"SAU":"사우디","ARE":"UAE","BHR":"바레인","QAT":"카타르","OMN":"오만","EGY":"이집트","MAR":"모로코",
           "TUN":"튀니지","MRT":"모리타니","TCD":"차드","DJI":"지부티","KWT":"쿠웨이트","SOM":"소말리아","ERI":"에리트레아"}
def lang_group(lang):
    return {c: y for c, y in year.items() if y >= 1990 and c in C and lang in (C[c].get("languages") or {}).values()}

# ---- 그림 1. 전체 확산 곡선 ----
y90 = year[year >= 1990]
yrs = np.arange(1990, 2024); cum = [(y90 <= t).sum() for t in yrs]
fig, ax = plt.subplots(figsize=(8, 4))
ax.axvspan(2016.5, 2019.5, color=LIGHT, alpha=.5, lw=0)
ax.plot(yrs, cum, color=INK, lw=2)
ax.text(2018, 20, "2017~2019\n3년간 38개국", ha="center", color=INK, fontsize=9.5)
ax.annotate(f"{cum[-1]}개국", (2023, cum[-1]), xytext=(-4, 6), textcoords="offset points", ha="right", color=INK, fontsize=9.5)
ax.set_title("설탕세 확산 곡선: 2017~2019년에 급격히 늘었다", loc="left", fontsize=12.5, fontweight="bold", color=INK)
ax.set_xlabel("연도"); ax.set_ylabel("누적 도입 국가 수 (개국)"); ax.set_ylim(0, 120); ax.set_xlim(1990, 2023.5)
ax.grid(axis="y", color="#e8e8ed", lw=.8); ax.set_axisbelow(True)
fig.text(0.01, 0.01, "자료: World Bank Global SSB Tax Database (2023.8), 1990~2023년 도입 112개국", fontsize=8, color=MID)
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig("fig1_전체_확산곡선.png", dpi=200); plt.close(fig)

# ---- 그림 2. 그룹별 확산 곡선 (급격형 vs 점진형) ----
fig, ax = plt.subplots(figsize=(8, 4))
for lang, ko, col in [("Arabic", "아랍어권", ACCENT), ("Spanish", "스페인어권", MID)]:
    g = pd.Series(lang_group(lang)); share = [100 * (g <= t).mean() for t in yrs]
    ax.plot(yrs, share, color=col, lw=2, label=f"{ko} ({len(g)}개국)")
ax.annotate("2014~2019년\n6년 만에 대부분 도입 (급격형)", (2017, 54.5), xytext=(2003.5, 66), color=INK, fontsize=9,
            arrowprops=dict(arrowstyle="-", color=MID, lw=.8))
ax.annotate("1990년부터 30년에 걸쳐\n천천히 도입 (점진형)", (1999, 35), xytext=(1991, 76), color=INK, fontsize=9,
            arrowprops=dict(arrowstyle="-", color=MID, lw=.8))
ax.set_title("같은 언어권 안에서도 퍼진 모양이 다르다", loc="left", fontsize=12.5, fontweight="bold", color=INK)
ax.set_xlabel("연도"); ax.set_ylabel("그룹 안 누적 도입 비율 (%)"); ax.set_ylim(0, 105); ax.set_xlim(1990, 2024)
ax.grid(axis="y", color="#e8e8ed", lw=.8); ax.set_axisbelow(True); ax.legend(frameon=False, loc="lower right")
fig.text(0.01, 0.01, "자료: World Bank Global SSB Tax Database (2023.8), 언어: countries.json 공용어", fontsize=8, color=MID)
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig("fig2_그룹별_확산곡선.png", dpi=200); plt.close(fig)

# ---- 그림 3. 확산 경로(캐스케이드): 실제 vs 가짜 ----
def cascade(g):
    """각 나라 ← 같은 그룹에서 가장 최근에 '먼저' 도입한 나라 (방향 그래프 = 확산 나무)"""
    T = nx.DiGraph(); T.add_nodes_from(g)
    for c, y in g.items():
        prev = [(yy, p) for p, yy in g.items() if yy < y]
        if prev: T.add_edge(max(prev)[1], c)
    return T

def draw(ax, g, title):
    T = cascade(g); order = sorted(g, key=lambda c: (g[c], c)); pos = {c: (g[c], i) for i, c in enumerate(order)}
    for u, v in T.edges():
        ax.annotate("", xy=pos[v], xytext=pos[u], arrowprops=dict(arrowstyle="-|>", color=MID, lw=1, shrinkA=5, shrinkB=5,
                    connectionstyle="arc3,rad=-0.25"))
    roots = [c for c in T if T.in_degree(c) == 0]
    for c, (x, y) in pos.items():
        ax.scatter(x, y, s=46, color=ACCENT if c in roots else INK, zorder=3)
        ax.text(x + .35, y, name_ko.get(c, c), va="center", fontsize=8.5, color=INK)
    gap = np.mean([g[v] - g[u] for u, v in T.edges()]) if T.number_of_edges() else 0
    ax.set_title(f"{title}\n화살표 {T.number_of_edges()}개 · 평균 {gap:.1f}년 뒤에 따라옴", loc="left", fontsize=10.5, color=INK)
    ax.set_yticks([]); ax.spines["left"].set_visible(False); ax.set_xlabel("도입 연도")
    ax.set_xlim(min(g.values()) - 1, max(g.values()) + 3)
    ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))

g = lang_group("Arabic")
rng = np.random.default_rng(7)
fake = dict(zip(g, rng.permutation(list(year[year >= 1990].values))[:len(g)]))  # 전체 도입 연도에서 무작위로 다시 뽑기
def mean_gap(gg):
    T = cascade(gg); return np.mean([gg[v] - gg[u] for u, v in T.edges()])
all_years = year[year >= 1990].values
fake_gaps = [mean_gap(dict(zip(g, rng.permutation(all_years)[:len(g)]))) for _ in range(1000)]
real_gap = mean_gap(g); p = (np.sum(np.array(fake_gaps) <= real_gap) + 1) / 1001
print(f"실제 {real_gap:.1f}년, 가짜 1,000개 평균 {np.mean(fake_gaps):.1f}년, p={p:.3f}")
fig, axes = plt.subplots(1, 2, figsize=(10, 5), sharey=True)
draw(axes[0], g, "실제 (아랍어권 11개국)")
draw(axes[1], fake, "가짜 세계 하나 (연도를 섞음)")
fig.suptitle("확산 경로는 '순서'일 뿐: 실제가 가짜보다 촘촘한지 비교해야 한다", x=0.01, ha="left", fontsize=12.5, fontweight="bold", color=INK)
fig.text(0.01, 0.05, f"가짜 세계 1,000개의 평균은 {np.mean(fake_gaps):.1f}년. 실제 {real_gap:.1f}년이 더 촘촘해 보이지만 우연 범위 안 (p = {p:.2f})", fontsize=9, color=INK)
fig.text(0.01, 0.012, "화살표: 같은 언어권에서 가장 최근에 먼저 도입한 나라 → 나중 나라. 순서일 뿐, 영향을 줬다는 증거는 아님.  파란 점: 그룹 안 첫 도입국", fontsize=8, color=MID)
fig.tight_layout(rect=(0, 0.09, 1, 0.94)); fig.savefig("fig3_확산경로_실제vs가짜.png", dpi=200, bbox_inches="tight", pad_inches=0.15); plt.close(fig)
print("saved")
