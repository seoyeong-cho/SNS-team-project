"""
확산 그래프 조건 확인: 그룹 곡선이 '전체가 시간에 따라 늘어난 것'과 다른가?
- 가짜 띠: 그룹과 같은 수의 나라를 전체 도입국(1990~2023, 112개국)에서 무작위로 뽑아 그린 곡선 1,000개의 95% 범위
- 실제 곡선이 띠 안에 있으면 = 전체 추세를 따라간 것뿐 / 띠 밖이면 = 그 그룹만의 시기가 있음
필요 파일: SSB-Tax-Database-Aug23.csv, countries.json
"""
import json, numpy as np, pandas as pd, networkx as nx
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
for name in ["Apple SD Gothic Neo", "Noto Sans CJK KR", "NanumGothic"]:
    if any(name in f.name for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = name; break
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#86868b",
                     "axes.labelcolor": "#424245", "xtick.color": "#6e6e73", "ytick.color": "#6e6e73", "font.size": 9.5})
INK, MID, BAND, ACCENT = "#1d1d1f", "#86868b", "#e3e3e8", "#2a6fdb"

d = pd.read_csv("SSB-Tax-Database-Aug23.csv", encoding="utf-8-sig").dropna(subset=["jurisdiction"])
d["level"] = d.level.str.strip(); d = d[d.level == "National"].replace({"country_code": {"PERU": "PER"}})
info = d.sort_values("year_imp").groupby("country_code").agg(year=("year_imp", "min"), inc=("income_group", "first"))
C = {x["cca3"]: x for x in json.load(open("countries.json"))}
a = info[info.year >= 1990].copy()
a["대륙"] = [C[c]["region"] for c in a.index]
a["소지역"] = [C[c]["subregion"] or C[c]["region"] for c in a.index]
ALL = a.year.values; YRS = np.arange(1990, 2024); rng = np.random.default_rng(0); R = 1000

def cum_pct(ys): ys = np.asarray(ys); return np.array([100 * (ys <= t).mean() for t in YRS])
def span(ys): return np.percentile(ys, 90) - np.percentile(ys, 10)          # 10%→90% 도입에 걸린 연수
def median(ys): return np.median(ys)

def check(ys):
    n = len(ys); fakes = [rng.choice(ALL, n, replace=False) for _ in range(R)]
    curves = np.array([cum_pct(f) for f in fakes])
    lo, hi = np.percentile(curves, 2.5, 0), np.percentile(curves, 97.5, 0)
    real = cum_pct(ys); out = ((real < lo) | (real > hi)).sum()
    fs = np.array([span(f) for f in fakes]); fm_ = np.array([median(f) for f in fakes])
    return dict(curve=real, lo=lo, hi=hi, out_years=int(out),
                span=span(ys), span_fake=float(np.mean(fs)), p_span=(np.sum(fs <= span(ys)) + 1) / (R + 1),
                med=median(ys), p_med=min(1, 2 * min((np.sum(fm_ <= median(ys)) + 1), (np.sum(fm_ >= median(ys)) + 1)) / (R + 1)))

def panel(col, groups, labels, fname, title):
    rows = []
    fig, axes = plt.subplots(1, len(groups), figsize=(2.55 * len(groups), 3.1), sharey=True)
    for ax, g, lab in zip(axes, groups, labels):
        ys = a[a[col] == g].year.values; r = check(ys)
        ax.fill_between(YRS, r["lo"], r["hi"], color=BAND, lw=0, label="가짜 띠 (95%)")
        stand_out = r["out_years"] >= 3
        ax.plot(YRS, r["curve"], color=ACCENT if stand_out else INK, lw=2, label="실제")
        ax.set_title(f"{lab} ({len(ys)}개국)", fontsize=10, color=INK, loc="left")
        ax.text(1991, 92, f"띠 밖 {r['out_years']}년", fontsize=8.5, color=ACCENT if stand_out else MID)
        ax.set_xticks([1990, 2005, 2020]); ax.set_ylim(0, 102); ax.grid(axis="y", color="#efeff3", lw=.8)
        rows.append(dict(기준=col, 그룹=lab, 나라수=len(ys), 띠밖_연수=r["out_years"],
                         중간도입연도=r["med"], 중간연도_p=round(r["p_med"], 3),
                         몰린기간_10to90=round(r["span"], 1), 가짜_몰린기간=round(r["span_fake"], 1), 몰림_p=round(r["p_span"], 3)))
    axes[0].set_ylabel("그룹 안 누적 도입 비율 (%)"); axes[0].legend(frameon=False, loc="center left", fontsize=8)
    fig.suptitle(title, x=0.01, ha="left", fontsize=12, fontweight="bold", color=INK)
    fig.text(0.01, 0.01, "회색 띠: 같은 수의 나라를 전체 도입국 112개에서 무작위로 1,000번 뽑았을 때 곡선의 95% 범위. 띠 안 = 전체 추세를 따라간 것뿐", fontsize=7.8, color=MID)
    fig.tight_layout(rect=(0, 0.05, 1, 0.9)); fig.savefig(fname, dpi=200, bbox_inches="tight", pad_inches=0.12); plt.close(fig)
    return rows

rows = []
rows += panel("대륙", ["Africa", "Americas", "Asia", "Europe", "Oceania"], ["아프리카", "아메리카", "아시아", "유럽", "오세아니아"],
              "fig4_대륙별_확산곡선_vs_가짜띠.png", "대륙별: 아프리카는 가짜 띠 밖으로 몰려서 도입, 유럽은 전체 추세 그대로")
rows += panel("inc", ["HIC", "UMIC", "LMIC", "LIC"], ["고소득", "중상소득", "중하소득", "저소득"],
              "fig5_소득별_확산곡선_vs_가짜띠.png", "소득별: 네 그룹 모두 가짜 띠 안 — 전체가 늘어난 것을 따라갔을 뿐")
tab = pd.DataFrame(rows); print(tab.to_string(index=False)); tab.to_csv("group_check_table.csv", index=False, encoding="utf-8-sig")

# ---- 그룹 안 확산 경로(화살표)도 가짜와 비교 ----
def cascade_gap(ys):
    ys = np.sort(ys); prev = [ys[ys < y].max() for y in ys if (ys < y).any()]
    return np.mean([y - p for y, p in zip([y for y in ys if (ys < y).any()], prev)])
print("\n[확산 경로: 평균 몇 년 뒤에 따라왔나]")
for col, gs in [("대륙", ["Africa","Americas","Asia","Europe","Oceania"]), ("inc", ["HIC","UMIC","LMIC","LIC"])]:
    for g in gs:
        ys = a[a[col] == g].year.values; real = cascade_gap(ys)
        fk = np.array([cascade_gap(rng.choice(ALL, len(ys), replace=False)) for _ in range(R)])
        print(col, g, round(real,2), round(fk.mean(),2), (np.sum(fk <= real)+1)/(R+1))
