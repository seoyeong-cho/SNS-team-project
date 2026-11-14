"""
설탕세(가당음료세) 도입 시기의 네트워크 검증 — 파일럿 분석 전체
사용법 (Colab): 아래 3개 파일을 같은 폴더에 두고 실행
  SSB-Tax-Database-Aug23.csv, SSB-Tax-Database-Aug22.xlsx, countries.json
결과: 구조 지표, 주 통계 S(같은 해 비교) 순열검정, kNN 범위 곡선, 노출 창(최근/미래), 케스케이드 무작위 비교
"""
import json
import numpy as np
import pandas as pd
import networkx as nx

R = 1000                      # 순열 반복 횟수
T = np.arange(1990, 2024)     # 분석 연도
rng = np.random.default_rng(0)

# ---------- 1. 전처리 ----------
def national_years(path, sheet=None):
    d = pd.read_csv(path, encoding="utf-8-sig") if sheet is None else pd.read_excel(path, sheet_name=sheet)
    d = d.rename(columns={"wb_code": "country_code"}).dropna(subset=["jurisdiction"])
    d["level"] = d["level"].astype(str).str.strip()                 # 'National ' 공백 4건
    d["country_code"] = d["country_code"].replace({"PERU": "PER"})
    return d[d.level == "National"]

ssb = national_years("SSB-Tax-Database-Aug23.csv")
year = ssb.groupby("country_code").year_imp.min()
health = ssb.groupby("country_code").health_obj.max()
C = {x["cca3"]: x for x in json.load(open("countries.json"))}
codes = sorted({k for k, v in C.items() if v.get("unMember")} | set(year.index))
idx = {c: i for i, c in enumerate(codes)}
nodes = pd.DataFrame({
    "iso3": codes,
    "sub": [C[k]["subregion"] or C[k]["region"] for k in codes],
    "reg": [C[k]["region"] for k in codes],
    "lat": [C[k]["latlng"][0] for k in codes],          # 수도가 아니라 나라 대표 좌표
    "lng": [C[k]["latlng"][1] for k in codes],
    "un": [bool(C[k].get("unMember")) for k in codes],
    "year": [year.get(k, np.nan) for k in codes],
    "health": [health.get(k, np.nan) for k in codes],
}).set_index("iso3")
Y0 = nodes.year.values.astype(float)
print(f"분석 단위 {len(codes)}, 도입국 {np.sum(~np.isnan(Y0))}, 1990+ 사건 {np.sum(Y0 >= 1990)}")

# 버전 감사
old = national_years("SSB-Tax-Database-Aug22.xlsx", "SSB Tax Database - Aug22").groupby("country_code").year_imp.min()
audit = pd.concat([old, year], axis=1, keys=["aug22", "aug23"])
print("Aug22→Aug23 연도 변경:", audit.dropna().query("aug22 != aug23").to_dict("index"))

# ---------- 2. 네트워크 ----------
lat, lng = np.radians(nodes.lat.values), np.radians(nodes.lng.values)
D = 2 * 6371 * np.arcsin(np.sqrt(np.sin((lat[:, None] - lat[None, :]) / 2) ** 2
                                 + np.cos(lat[:, None]) * np.cos(lat[None, :]) * np.sin((lng[:, None] - lng[None, :]) / 2) ** 2))

def g_border():
    G = nx.Graph(); G.add_nodes_from(codes)
    G.add_edges_from((k, b) for k in codes for b in C[k]["borders"] if b in idx)
    return G

def g_knn(k):
    G = nx.Graph(); G.add_nodes_from(codes)
    for i, c in enumerate(codes):
        G.add_edges_from((c, codes[j]) for j in np.argsort(D[i])[1:k + 1])
    return G

def g_group(col):                      # 나라–그룹 이분망을 나라끼리 투영
    B = nx.Graph()
    B.add_edges_from((c, "G:" + g) for c, g in nodes[col].items())
    return nx.bipartite.projected_graph(B, codes)

def structure(G):
    cc = max(nx.connected_components(G), key=len); H = G.subgraph(cc)
    return dict(E=G.number_of_edges(), density=round(nx.density(G), 4),
                avg_deg=round(2 * G.number_of_edges() / G.number_of_nodes(), 2),
                isolates=nx.number_of_isolates(G), components=nx.number_connected_components(G),
                LCC=round(len(cc) / len(G), 3), clustering=round(nx.average_clustering(G), 3),
                avg_dist_LCC=round(nx.average_shortest_path_length(H), 2), diameter_LCC=nx.diameter(H))

def adj(G):
    A = np.zeros((len(codes), len(codes)), bool)
    for u, v in G.edges():
        A[idx[u], idx[v]] = A[idx[v], idx[u]] = True
    return A

NETS = {"border": g_border(), "knn3": g_knn(3), "border+knn3": nx.compose(g_border(), g_knn(3)),
        "subregion": g_group("sub")}
for name, G in NETS.items():
    print(name, structure(G))

# ---------- 3. 주 통계 S와 순열검정 (N1: 도입국끼리 연도만 섞음) ----------
def S(Y, A, mask=None, window=None):
    """도입국의 '기도입 이웃 비율' - 같은 해 위험집합 평균. window=('recent'|'future', L)"""
    Yf = np.where(np.isnan(Y), 9999, Y); d = A.sum(1)
    m = np.ones(len(Y), bool) if mask is None else mask
    out = []
    for t in T:
        risk = (Yf >= t) & (d > 0) & m; ev = risk & (Yf == t)
        if not ev.any():
            continue
        src = Yf < t
        if window and window[0] == "recent": src &= Yf >= t - window[1]
        if window and window[0] == "future": src = (Yf > t) & (Yf <= t + window[1])
        f = A[:, src & m].sum(1) / np.maximum(d, 1)
        out += list(f[ev] - f[risk].mean())
    return float(np.mean(out))

def perm_test(stat, Y=Y0, mask=None):
    obs = stat(Y)
    ad = ~np.isnan(Y) & (np.ones(len(Y), bool) if mask is None else mask)
    null = []
    for _ in range(R):
        Ys = Y.copy(); Ys[ad] = rng.permutation(Y[ad]); null.append(stat(Ys))
    null = np.array(null)
    return dict(obs=round(obs, 3), null=round(null.mean(), 3), excess=round(obs - null.mean(), 3),
                z=round((obs - null.mean()) / null.std(), 2), p=round((np.sum(null >= obs) + 1) / (R + 1), 3))

print("\n[RQ2] 주 통계 S")
for name, G in NETS.items():
    A = adj(G); print(name, perm_test(lambda Y: S(Y, A)))

# ---------- 4. 범위 곡선 (RQ3): 평균 이웃 수별 z ----------
print("\n[RQ3] kNN 범위 곡선")
curve = []
for k in [1, 2, 3, 4, 6, 8, 10, 12, 15, 20]:
    G = g_knn(k); A = adj(G); r = perm_test(lambda Y: S(Y, A))
    curve.append(dict(k=k, avg_deg=round(2 * G.number_of_edges() / len(G), 1), **r)); print(curve[-1])
pd.DataFrame(curve).to_csv("range_curve.csv", index=False)

# ---------- 5. 노출 창 (RQ4) ----------
print("\n[RQ4] 노출 창")
for name in ["subregion", "border+knn3"]:
    A = adj(NETS[name])
    for w in [("recent", 3), ("future", 3)]:
        print(name, w, perm_test(lambda Y: S(Y, A, window=w)))

# ---------- 6. 케스케이드: '이웃 선도입 국가 수' 실제 vs 무작위 ----------
def n_prior_neighbor(Y, A):
    Yf = np.where(np.isnan(Y), 9999, Y)
    return sum(bool((A[i] & (Yf < Yf[i])).any()) for i in np.where((Yf >= 1990) & (Yf < 9999))[0])

A = adj(NETS["border+knn3"])
print("\n[RQ4] 케스케이드 이웃 선도입 국가 수", perm_test(lambda Y: n_prior_neighbor(Y, A)))

# ---------- 7. 강건성 예시 ----------
print("\n[강건성] 소지역망")
A = adj(NETS["subregion"]); iso = np.array(codes)
checks = {
    "GCC 제외": ~np.isin(iso, ["ARE", "BHR", "SAU", "QAT", "OMN", "KWT"]),
    "영토 제외": nodes.un.values,
    "건강 목적만": ~((~np.isnan(Y0)) & (nodes.health.values == 0)),
}
for lab, m in checks.items():
    print(lab, perm_test(lambda Y: S(Y, A, mask=m), mask=m))
