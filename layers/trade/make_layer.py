"""
무역 계층 (D 담당). 순서는 layers/region/make_layer.py 예시를 따름
실행: python layers/trade/make_layer.py
설명 문서: docs/layers/trade.md

원본 (HS 2202 가당・향 첨가 음료, 2010~2020년, 연간, UN Comtrade)
  수입(M): data/raw/UNComtrade-trade-statistics-official-CAHS-20261118-0323.csv
  수출(X): data/raw/UNComtrade-trade-statistics-official-CAHS-20261121-0104.csv

전처리
1. 나라 간 행만 남김: partner World(W00), 특수 코드(X1, S19 등), nodes.csv에 없는 지역(HKG, MAC 등) 제외
2. 방향(수입국 m ← 수출국 x)마다 출처 하나를 정해서 11년 내내 그 출처만 씀 (해마다 출처가 바뀌면
   값 변화가 실제 무역 변화가 아니라 보고 주체가 바뀐 효과일 수 있어서)
   ① m이 11년 다 수입 보고 → 수입 기록
   ② 아니면 x가 11년 다 수출 보고 → 수출 기록
   ③ 둘 다 빈 해 있으면 보고한 해가 많은 쪽 (같으면 수입)
   ④ 둘 다 보고 0년 → 모름, 0으로 둠
   '보고했다' = 그해 HS 2202 기록을 하나라도 냄 (그 상대국 기록이 있다는 뜻은 아님)
3. 방향별 연평균 = 고른 출처가 보고한 해들의 평균. 보고는 했는데 그 상대국 기록이 없는 해는 0
4. 쌍 교역액 = 두 방향 연평균의 합 → layer_trade_pairs.csv (src, dst, value_usd)
   ※ 교역 기록 없는 3개국 IMN(맨섬)・LIE(리히텐슈타인)・MCO(모나코)는 보충하지 않고 고립국으로 둠
     (각각 영국・스위스・프랑스 관세 영역에 묶여 집계되는 것으로 추정, 출처 확인 필요)

계층
5. 나라마다 교역액 상위 k개국, **서로** 상위 k위 안일 때만 연결 → layer_trade_edges.csv (group = top5_trade)
   민감도: k = 3, 10도 같이 만듦 → layer_trade3_edges.csv, layer_trade10_edges.csv
"""
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.append(str(ROOT / "src"))
from common import (adoption_test, check_edges, layer_graph, load_nodes,  # noqa: E402
                    robustness, stage1, structure)

RAW = ROOT / "data" / "raw"
IMP = RAW / "UNComtrade-trade-statistics-official-CAHS-20261118-0323.csv"   # 수입(M)
EXP = RAW / "UNComtrade-trade-statistics-official-CAHS-20261121-0104.csv"   # 수출(X)
N_YEARS = 11      # 2010~2020
KS = [3, 5, 10]   # 상위 몇 개국. 5가 기본, 3・10은 민감도

nodes = load_nodes()


# ---------- 전처리 ----------
def load_flow(path, flow):
    """원본 하나 → (나라 간 행, 나라별 보고 연도 집합)"""
    df = pd.read_csv(path, low_memory=False,
                     usecols=["refYear", "flowCode", "cmdCode", "reporterISO", "partnerISO", "primaryValue"])
    assert (df.flowCode == flow).all() and (df.cmdCode == 2202).all(), f"{path.name}: {flow} / HS 2202 아님"
    df["reporterISO"] = df.reporterISO.str.strip()
    df["partnerISO"] = df.partnerISO.str.strip()
    # 보고 연도는 상대국 상관없이 (World, nodes 밖 지역 포함) 그해 행이 하나라도 있으면
    reported = df.groupby("reporterISO").refYear.apply(set).to_dict()
    ok = set(nodes.index)
    n0 = len(df)
    df = df[df.reporterISO.isin(ok) & df.partnerISO.isin(ok) & (df.reporterISO != df.partnerISO)]
    print(f"{'수입' if flow == 'M' else '수출'}: 원본 {n0}행 → 나라 간 {len(df)}행")
    return df, reported


def choose_source(m, x, imp_rep, exp_rep):
    """방향 m ← x 의 출처 ('M' 수입 / 'X' 수출 / None 모름)와 그 출처의 보고 연도"""
    yi, ye = imp_rep.get(m, set()), exp_rep.get(x, set())
    if len(yi) == N_YEARS:
        return "M", yi
    if len(ye) == N_YEARS:
        return "X", ye
    if not yi and not ye:
        return None, set()
    return ("M", yi) if len(yi) >= len(ye) else ("X", ye)


def load_pairs():
    """원본 수입・수출 → 나라 쌍별 연평균 교역액 (달러)"""
    imp, imp_rep = load_flow(IMP, "M")
    exp, exp_rep = load_flow(EXP, "X")

    # 방향 (수입국 m, 수출국 x, 연도) → 금액
    v_imp = imp.groupby(["reporterISO", "partnerISO", "refYear"]).primaryValue.sum().to_dict()
    v_exp = exp.groupby(["partnerISO", "reporterISO", "refYear"]).primaryValue.sum().to_dict()

    pairs = {tuple(sorted(p)) for p in zip(imp.reporterISO, imp.partnerISO)} | \
            {tuple(sorted(p)) for p in zip(exp.reporterISO, exp.partnerISO)}

    rows, src_count = [], Counter()
    for a, b in sorted(pairs):
        total = 0.0
        for m, x in ((a, b), (b, a)):
            src, years = choose_source(m, x, imp_rep, exp_rep)
            src_count[src or "모름"] += 1
            if src is None:
                continue
            vals = v_imp if src == "M" else v_exp
            total += sum(vals.get((m, x, t), 0.0) for t in years) / len(years)
        rows.append((a, b, round(total)))

    print("방향별 출처:", {"수입" if k == "M" else "수출" if k == "X" else k: v for k, v in src_count.items()})
    out = pd.DataFrame(rows, columns=["src", "dst", "value_usd"])
    return out[out.value_usd > 0].reset_index(drop=True)


# ---------- 계층 ----------
def mutual_topk(pairs, k):
    """나라마다 상위 k개 교역국 → 서로 상위 k위 안인 쌍만 엣지 (src < dst)"""
    both = pd.concat([pairs.rename(columns={"src": "me", "dst": "other"}),
                      pairs.rename(columns={"dst": "me", "src": "other"})])
    # 동점이면 iso3 알파벳순으로 정해서 결과가 항상 같게
    both = both.sort_values(["me", "value_usd", "other"], ascending=[True, False, True])
    top = both.groupby("me").head(k)
    chosen = set(zip(top.me, top.other))
    keep = [(s, d) for s, d in zip(pairs.src, pairs.dst) if (s, d) in chosen and (d, s) in chosen]
    return pd.DataFrame(keep, columns=["src", "dst"]).assign(group=f"top{k}_trade")


if __name__ == "__main__":
    pairs = load_pairs()
    pairs.to_csv(HERE / "layer_trade_pairs.csv", index=False)
    covered = set(pairs.src) | set(pairs.dst)
    print(f"교역 쌍 {len(pairs)}개, 기록 있는 나라 {len(covered)}/{len(nodes)}")
    print("기록 없는 나라:", sorted(set(nodes.index) - covered))

    for k in KS:
        edges = mutual_topk(pairs, k)
        check_edges(edges, nodes)
        name = "trade" if k == 5 else f"trade{k}"
        edges.to_csv(HERE / f"layer_{name}_edges.csv", index=False)
        print(f"[{name}] top{k}", structure(layer_graph(edges, nodes)))

        # 1단계 → result_<이름>.csv
        res = stage1(edges, nodes)
        res.to_csv(HERE / f"result_{name}.csv", index=False)
        print(res.to_string(index=False))
        # 강건성 → robustness_<이름>.csv
        rob = robustness(edges, nodes)
        rob.to_csv(HERE / f"robustness_{name}.csv", index=False)
        print(rob.to_string(index=False))
        # 도입 여부 → adoption_<이름>.csv
        adopt = pd.DataFrame([adoption_test(edges, nodes)])
        adopt.to_csv(HERE / f"adoption_{name}.csv", index=False)
        print(adopt.to_string(index=False), "\n")
