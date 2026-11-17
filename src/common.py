"""
공통 함수. 넷 다 이 파일을 import해서 씀 → 계산 방식이 같아야 분야끼리 비교됨.
1단계 계산 코드를 각자 따로 짜지 말 것.

사용 예 (layers/region/make_layer.py 참고):
    import sys; sys.path.append("../../src")
    from common import *
    nodes = load_nodes()
    groups = pd.DataFrame({"iso3": [...], "group": [...]})
    edges = groups_to_edges(groups, nodes)
    res = stage1(edges, nodes)
"""
from itertools import combinations
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
NODES_PATH = ROOT / "data" / "processed" / "nodes.csv"

SEED = 42          # 가짜 세계 재현용. 바꾸지 말 것
R = 1000           # 가짜 세계 개수
Y_MIN, Y_MAX = 1990, 2023   # 연도 비교 대상: 이 기간 도입국 (112개국)


# ---------- 노드 ----------
def load_nodes(path=NODES_PATH):
    """204개국 표. 열: iso3, name, un_member, adopter, year_imp, in_analysis"""
    return pd.read_csv(path).set_index("iso3")


def analysis_countries(nodes):
    """연도 비교에 들어가는 나라 (1990~2023 도입국)"""
    return nodes.index[nodes.in_analysis == 1]


# ---------- 계층 만들기 ----------
def groups_to_edges(groups, nodes):
    """나라-그룹 표 → 나라-나라 엣지 표 (이분 네트워크 투영)

    groups: 열 iso3, group. 한 나라가 그룹 여러 개면 행 여러 개
    반환: 열 src, dst, group. src < dst, 같은 쌍이 그룹 두 개를 공유하면 행 두 개
    """
    g = groups.dropna().drop_duplicates()
    bad = set(g.iso3) - set(nodes.index)
    if bad:
        raise ValueError(f"nodes.csv에 없는 코드: {sorted(bad)}")
    rows = []
    for name, sub in g.groupby("group"):
        for a, b in combinations(sorted(sub.iso3.unique()), 2):
            rows.append((a, b, name))
    return pd.DataFrame(rows, columns=["src", "dst", "group"])


def check_edges(edges, nodes):
    """제출 전 체크. 문제 있으면 에러"""
    assert set(edges.columns) >= {"src", "dst", "group"}, "열 이름 src, dst, group"
    assert (edges.src < edges.dst).all(), "src < dst (알파벳순) 아님"
    assert not edges.duplicated().any(), "중복 엣지"
    bad = (set(edges.src) | set(edges.dst)) - set(nodes.index)
    assert not bad, f"nodes.csv에 없는 코드: {sorted(bad)}"
    return True


def layer_graph(edges, nodes):
    """엣지 표 → networkx 그래프. 그룹 여러 개 공유해도 연결 하나"""
    G = nx.Graph()
    G.add_nodes_from(nodes.index)
    G.add_edges_from(zip(edges.src, edges.dst))
    return G


def structure(G):
    """계층 비교표 한 줄: 노드, 엣지, 밀도, 평균 degree, 컴포넌트, 고립, 군집계수"""
    n, e = G.number_of_nodes(), G.number_of_edges()
    return dict(nodes=n, edges=e, density=round(nx.density(G), 4),
                avg_degree=round(2 * e / n, 2),
                components=nx.number_connected_components(G),
                isolates=nx.number_of_isolates(G),
                clustering=round(nx.average_clustering(G), 3))


# ---------- 1단계: 같은 그룹끼리 도입 연도 차이 vs 가짜 세계 ----------
def _pair_index(edges, nodes):
    """분석 대상 도입국끼리의 쌍만 (i, j) 인덱스로"""
    ac = list(analysis_countries(nodes))
    pos = {c: i for i, c in enumerate(ac)}
    e = edges[edges.src.isin(pos) & edges.dst.isin(pos)]
    return ac, pos, e


STRATA = ["income_db", "budget_year", "health_obj"]   # 강건성 검사에 쓰는 나라 성격 (nodes.csv 열)


def _strata_labels(nodes, ac, strata):
    if strata is None:
        return None
    if strata not in nodes.columns:
        raise ValueError(f"nodes.csv에 '{strata}' 열 없음. 쓸 수 있는 것: {STRATA}")
    return nodes.loc[ac, strata].astype(str).to_numpy()   # 값 없는 나라는 'nan' 한 묶음


def _shuffles(y, r=R, seed=SEED, labels=None):
    """가짜 세계: 도입국끼리 연도만 섞음 (누가 도입했는지, 해마다 몇 개국인지는 그대로)

    labels가 있으면 같은 성격(예: 같은 소득 등급)끼리만 섞음
    → 그 성격 때문에 생긴 시기 차이는 가짜 세계에도 남아서 걸러짐
    """
    rng = np.random.default_rng(seed)
    groups = None if labels is None else [np.where(labels == v)[0] for v in np.unique(labels)]
    for _ in range(r):
        if groups is None:
            yield rng.permutation(y)
        else:
            ys = y.copy()
            for g in groups:
                ys[g] = y[rng.permutation(g)]
            yield ys


def stage1(edges, nodes, by_group=True, r=R, seed=SEED, strata=None):
    """같은 그룹 도입국 쌍의 평균 연도 차이를 가짜 세계 r개와 비교

    strata: None이면 기본(전체에서 섞음). 'income_db' 등 nodes.csv 열 이름이면 그 성격 안에서만 섞음
    반환 표 열: group, n_adopters, n_pairs, mean_gap_real, mean_gap_fake_avg, p
    첫 줄 group='ALL'은 계층 전체 (쌍 중복 제거)
    p = 가짜가 실제보다 작거나 같은 비율 → 작을수록 '같이 움직임'
    """
    ac, pos, e = _pair_index(edges, nodes)
    y = nodes.loc[ac, "year_imp"].to_numpy(float)
    labels = _strata_labels(nodes, ac, strata)

    sets = {"ALL": e[["src", "dst"]].drop_duplicates()}
    if by_group:
        for name, sub in e.groupby("group"):
            sets[name] = sub
    idx = {k: (v.src.map(pos).to_numpy(), v.dst.map(pos).to_numpy()) for k, v in sets.items()}

    def gaps(yy):
        return {k: np.abs(yy[i] - yy[j]).mean() if len(i) else np.nan for k, (i, j) in idx.items()}

    real = gaps(y)
    fake = {k: [] for k in idx}
    for ys in _shuffles(y, r, seed, labels):
        for k, v in gaps(ys).items():
            fake[k].append(v)

    out = []
    for k in idx:
        f = np.array(fake[k])
        i, j = idx[k]
        n_ad = len(set(i) | set(j))
        p = (np.sum(f <= real[k]) + 1) / (r + 1) if len(i) else np.nan
        out.append(dict(group=k, n_adopters=n_ad, n_pairs=len(i),
                        mean_gap_real=round(real[k], 2), mean_gap_fake_avg=round(np.nanmean(f), 2),
                        p=round(p, 4)))
    return pd.DataFrame(out)


# ---------- 2-1단계: 따라 함 검사 ----------
def follow_test(edges, nodes, lo=1, hi=3, r=R, seed=SEED, strata=None):
    """같은 그룹 나라가 도입한 뒤 lo~hi년 안에 도입한 나라 비율을 가짜 세계와 비교

    strata: stage1과 같음
    p = 가짜가 실제보다 크거나 같은 비율 → 작을수록 '따라 함' 흔적
    """
    ac, pos, e = _pair_index(edges, nodes)
    y = nodes.loc[ac, "year_imp"].to_numpy(float)
    labels = _strata_labels(nodes, ac, strata)
    n = len(ac)
    A = np.zeros((n, n), bool)
    i, j = e.src.map(pos).to_numpy(), e.dst.map(pos).to_numpy()
    A[i, j] = A[j, i] = True

    def share(yy):
        d = yy[:, None] - yy[None, :]          # d[a, b] = a가 b보다 몇 년 늦게
        return (A & (d >= lo) & (d <= hi)).any(1).mean()

    real = share(y)
    f = np.array([share(ys) for ys in _shuffles(y, r, seed, labels)])
    return dict(window=f"{lo}-{hi}y", share_real=round(float(real), 3), share_fake_avg=round(float(f.mean()), 3),
                p=round(float((np.sum(f >= real) + 1) / (r + 1)), 4))


# ---------- 강건성: 다른 요인을 거른 가짜 세계로 다시 ----------
def robustness(edges, nodes, strata_list=STRATA, r=R, seed=SEED):
    """계층 전체(ALL) 1단계를 기본 + 성격별로 섞은 가짜 세계로 반복

    반환 표 열: shuffle, mean_gap_real, mean_gap_fake_avg, p
    기본에서 작던 p가 어떤 성격 안에서 섞었을 때 커지면 → 그 효과 일부는 그 성격 때문
    """
    rows = []
    for s in [None, *strata_list]:
        a = stage1(edges, nodes, by_group=False, r=r, seed=seed, strata=s).iloc[0]
        rows.append(dict(shuffle=s or "basic", mean_gap_real=a.mean_gap_real,
                         mean_gap_fake_avg=a.mean_gap_fake_avg, p=a.p))
    return pd.DataFrame(rows)


# ---------- 3단계: 그룹별 확산 곡선 ----------
def group_curve(groups, nodes, group):
    """그룹 하나의 연도별 누적 도입 비율(%). 분모 = 그룹 전체 나라 수 (미도입 포함)"""
    members = groups.loc[groups.group == group, "iso3"].unique()
    yrs = nodes.loc[nodes.index.isin(members), "year_imp"]
    years = np.arange(Y_MIN, Y_MAX + 1)
    cum = [(yrs <= t).sum() / len(members) * 100 for t in years]
    return pd.DataFrame({"year": years, "cum_pct": np.round(cum, 1)})
