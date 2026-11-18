"""Compare temporal paths in the current language and colony networks.

Path edges are directed only from an earlier adopter to a later adopter. The
network stays fixed while adoption years are permuted among the same 1990–2023
adopters, preserving the observed year distribution. Results are descriptive
temporal patterns, not evidence of causal diffusion.

Run: python analysis/stage3_paths.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from common import R, SEED, follow_test, load_nodes  # noqa: E402

ANALYSIS_DIR = ROOT / "analysis"
LAYER_FILES = {
    "language/language": ROOT / "layers/language/layer_language_edges.csv",
    "language/colony": ROOT / "layers/language/layer_colony_edges.csv",
}
MIN_GROUP_ADOPTERS = 5
MAX_LAG = 3


def load_continents(nodes):
    countries = json.loads((ROOT / "data/raw/countries.json").read_text(encoding="utf-8"))
    by_iso = {row["cca3"]: row["region"] for row in countries}
    missing = sorted(set(nodes.index) - set(by_iso))
    if missing:
        raise ValueError(f"countries.json에 대륙 정보가 없는 ISO3: {missing}")
    out = nodes.copy()
    out["continent"] = out.index.map(by_iso)
    return out


def load_layer(path, adopter_codes):
    edges = pd.read_csv(path)
    required = {"src", "dst", "group"}
    if not required.issubset(edges.columns):
        raise ValueError(f"{path.relative_to(ROOT)}에 필요한 열이 없습니다: {sorted(required)}")
    # Keep only pairs among the 1990–2023 analysis adopters. The full network
    # still remains available in the original layer file for maps and context.
    edges = edges[edges.src.isin(adopter_codes) & edges.dst.isin(adopter_codes)].copy()
    return edges


def matrix_from_edges(edges, codes):
    pos = {code: i for i, code in enumerate(codes)}
    adj = np.zeros((len(codes), len(codes)), dtype=bool)
    for src, dst in edges[["src", "dst"]].drop_duplicates().itertuples(index=False, name=None):
        i, j = pos[src], pos[dst]
        adj[i, j] = adj[j, i] = True
    return adj, pos


def path_metrics(adj, years, possible_structures=None):
    """Counts ordered A→B→C paths; each of the two links is a real layer edge."""
    delta = years[None, :] - years[:, None]  # delta[i, j] = year(j) - year(i)
    directed = adj & (delta > 0)
    constrained = adj & (delta >= 1) & (delta <= MAX_LAG)
    simple_by_middle = directed.sum(axis=0) * directed.sum(axis=1)
    constrained_by_middle = constrained.sum(axis=0) * constrained.sum(axis=1)
    simple = int(simple_by_middle.sum())
    constrained_count = int(constrained_by_middle.sum())
    if possible_structures is None:
        degree = adj.sum(axis=1)
        possible_structures = int(np.sum(degree * np.maximum(degree - 1, 0)))
    constrained_rate = constrained_count / possible_structures if possible_structures else np.nan
    simple_rate = simple / possible_structures if possible_structures else np.nan
    follow_share = float(constrained.any(axis=0).mean()) if len(years) else np.nan
    return {
        "simple_paths": simple,
        "simple_rate": simple_rate,
        "constrained_paths": constrained_count,
        "constrained_rate": constrained_rate,
        "follow_share_1_3": follow_share,
        "possible_structures": int(possible_structures),
    }


def year_permutations(years, labels=None, r=R, seed=SEED):
    """Match common._shuffles: keep adopters/year multiset, optionally stratified."""
    rng = np.random.default_rng(seed)
    strata = None if labels is None else [np.where(labels == v)[0] for v in np.unique(labels)]
    for _ in range(r):
        if strata is None:
            yield rng.permutation(years)
        else:
            fake = years.copy()
            for ix in strata:
                fake[ix] = years[rng.permutation(ix)]
            yield fake


def path_records(layer, edges, codes, years):
    """Return actual directed 1–3 year edges and distinct A→B→C path rows for C."""
    pos = {code: i for i, code in enumerate(codes)}
    pair_groups = {}
    for row in edges.itertuples(index=False):
        pair = tuple(sorted((row.src, row.dst)))
        pair_groups.setdefault(pair, set()).add(row.group)
    adj, _ = matrix_from_edges(edges, codes)
    edge_rows, outgoing, incoming = [], [set() for _ in codes], [set() for _ in codes]

    for i, j in zip(*np.where(np.triu(adj, 1))):
        a, b = codes[i], codes[j]
        lag = int(abs(years[i] - years[j]))
        earlier, later = (a, b) if years[i] < years[j] else (b, a) if years[j] < years[i] else (None, None)
        directed = earlier is not None
        if directed:
            src_i, dst_i = pos[earlier], pos[later]
            outgoing[src_i].add(dst_i)
            incoming[dst_i].add(src_i)
        edge_rows.append({
            "layer": layer,
            "src": earlier if directed else a,
            "dst": later if directed else b,
            "src_year": int(years[pos[earlier]]) if directed else int(years[i]),
            "dst_year": int(years[pos[later]]) if directed else int(years[j]),
            "lag_years": lag,
            "directed_by_time": directed,
            "within_1_3_years": bool(directed and lag <= MAX_LAG),
            "groups": "|".join(sorted(pair_groups[(a, b)])),
        })

    path_rows = []
    for middle_i, predecessors in enumerate(incoming):
        for first_i in predecessors:
            lag1 = int(years[middle_i] - years[first_i])
            if not 1 <= lag1 <= MAX_LAG:
                continue
            for last_i in outgoing[middle_i]:
                lag2 = int(years[last_i] - years[middle_i])
                if not 1 <= lag2 <= MAX_LAG or len({first_i, middle_i, last_i}) != 3:
                    continue
                a, b, c = codes[first_i], codes[middle_i], codes[last_i]
                path_rows.append({
                    "layer": layer,
                    "src": a,
                    "via": b,
                    "dst": c,
                    "year_src": int(years[first_i]),
                    "year_via": int(years[middle_i]),
                    "year_dst": int(years[last_i]),
                    "lag_src_via": lag1,
                    "lag_via_dst": lag2,
                    "groups_src_via": "|".join(sorted(pair_groups[tuple(sorted((a, b)))])),
                    "groups_via_dst": "|".join(sorted(pair_groups[tuple(sorted((b, c)))])),
                })
    return edge_rows, path_rows


def group_diagnostics(layer, edges, codes, years, layer_adj):
    rows = []
    base = path_metrics(layer_adj, years)
    for group, sub in edges.groupby("group"):
        members = set(sub.src) | set(sub.dst)
        group_codes = [c for c in codes if c in members]
        if len(group_codes) < MIN_GROUP_ADOPTERS:
            continue
        group_edges = sub[["src", "dst"]].drop_duplicates()
        group_adj, _ = matrix_from_edges(group_edges, group_codes)
        group_years = np.array([years[codes.index(c)] for c in group_codes])
        group_result = path_metrics(group_adj, group_years)

        without = edges[edges.group != group]
        without_adj, _ = matrix_from_edges(without, codes)
        without_result = path_metrics(without_adj, years)
        rows.append({
            "layer": layer,
            "group": group,
            "group_adopters": len(group_codes),
            "group_pairs": len(group_edges),
            "group_possible_structures": group_result["possible_structures"],
            "group_paths_1_3": group_result["constrained_paths"],
            "group_rate_1_3": group_result["constrained_rate"],
            "layer_paths_1_3": base["constrained_paths"],
            "layer_paths_without_group_1_3": without_result["constrained_paths"],
            "leave_group_out_drop": base["constrained_paths"] - without_result["constrained_paths"],
        })
    return rows


def analyze_layer(layer, edges, nodes):
    codes = list(nodes.index[nodes.in_analysis == 1])
    years = nodes.loc[codes, "year_imp"].to_numpy(int)
    labels = nodes.loc[codes, "continent"].astype(str).to_numpy()
    adj, _ = matrix_from_edges(edges, codes)
    possible = int(np.sum(adj.sum(axis=1) * np.maximum(adj.sum(axis=1) - 1, 0)))
    real = path_metrics(adj, years, possible)
    edge_rows, path_rows = path_records(layer, edges, codes, years)
    group_rows = group_diagnostics(layer, edges, codes, years, adj)

    summary_rows, null_rows = [], []
    for scheme, strata_labels in (("basic", None), ("continent", labels)):
        follow_reference = follow_test(
            edges, nodes, lo=1, hi=MAX_LAG,
            strata="continent" if scheme == "continent" else None,
        )
        fake_metrics = []
        for i, fake_years in enumerate(year_permutations(years, strata_labels), start=1):
            m = path_metrics(adj, fake_years, possible)
            fake_metrics.append(m)
            null_rows.append({"layer": layer, "scheme": scheme, "replicate": i, **m})
        fake = pd.DataFrame(fake_metrics)
        for metric in ("simple_paths", "constrained_paths"):
            value = real[metric]
            null_values = fake[metric].to_numpy(int)
            p = (np.count_nonzero(null_values >= value) + 1) / (R + 1)
            summary_rows.append({
                "layer": layer,
                "scheme": scheme,
                "metric": metric,
                "n_adopters": len(codes),
                "n_unique_edges": int(np.triu(adj, 1).sum()),
                "possible_two_step_structures": possible,
                "actual_paths": value,
                "actual_path_rate": real["simple_rate"] if metric == "simple_paths" else real["constrained_rate"],
                "fake_paths_mean": float(null_values.mean()),
                "fake_path_rate_mean": float(fake["simple_rate" if metric == "simple_paths" else "constrained_rate"].mean()),
                "fake_paths_p025": float(np.quantile(null_values, 0.025)),
                "fake_paths_p975": float(np.quantile(null_values, 0.975)),
                "p_upper": float(p),
                "n_current_layers": len(LAYER_FILES),
                "p_bonferroni_current_layers": min(1.0, float(p) * len(LAYER_FILES)),
                "follow_share_actual_1_3": real["follow_share_1_3"],
                "follow_share_fake_mean_1_3": float(fake.follow_share_1_3.mean()),
                "follow_test_p_1_3": follow_reference["p"],
                "follow_test_share_real_1_3": follow_reference["share_real"],
                "follow_test_share_fake_mean_1_3": follow_reference["share_fake_avg"],
                "corr_null_path_follow": float(fake[metric].corr(fake.follow_share_1_3)),
                "R": R,
                "seed": SEED,
            })
    return summary_rows, null_rows, edge_rows, path_rows, group_rows


def main():
    nodes = load_continents(load_nodes())
    adopters = set(nodes.index[nodes.in_analysis == 1])
    summaries, nulls, directed_edges, path_rows, groups = [], [], [], [], []
    for layer, path in LAYER_FILES.items():
        edges = load_layer(path, adopters)
        if edges.empty:
            raise ValueError(f"{layer}: 1990–2023 도입국 사이 엣지가 없습니다")
        result = analyze_layer(layer, edges, nodes)
        summaries.extend(result[0])
        nulls.extend(result[1])
        directed_edges.extend(result[2])
        path_rows.extend(result[3])
        groups.extend(result[4])

    outputs = {
        "stage3_path_comparison.csv": pd.DataFrame(summaries),
        "stage3_path_nulls.csv": pd.DataFrame(nulls),
        "stage3_path_directed_edges.csv": pd.DataFrame(directed_edges),
        "stage3_paths_1_3.csv": pd.DataFrame(path_rows),
        "stage3_group_path_diagnostics.csv": pd.DataFrame(groups),
    }
    for name, frame in outputs.items():
        frame.to_csv(ANALYSIS_DIR / name, index=False)
    print(f"R={R}, seed={SEED}; fixed network, adopter years permuted globally or within continent")
    print(pd.DataFrame(summaries).to_string(index=False))
    print("\n주요 그룹 (도입국 5개국 이상), 실제 1~3년 경로가 많은 순")
    group_table = pd.DataFrame(groups)
    if not group_table.empty:
        print(group_table.sort_values(["layer", "group_paths_1_3"], ascending=[True, False])
              .groupby("layer", group_keys=False).head(8).to_string(index=False))
    for name, frame in outputs.items():
        print(f"저장: analysis/{name} ({len(frame)}행)")


if __name__ == "__main__":
    main()
