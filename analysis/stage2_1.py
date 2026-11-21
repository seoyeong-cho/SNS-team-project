"""Stage 2-1: cross-continent timing and follow-up tests for layer networks.

Reads only primary ``layers/<domain>/layer_*_edges.csv`` files. Supplementary
networks are intentionally excluded. As new primary layers are added, they are
picked up automatically; layers without cross-continent adopter pairs are
reported as ineligible and left out of the multiple-testing families.

Run from any directory with: python analysis/stage2_1.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from common import R, SEED, follow_test, load_nodes, stage1  # noqa: E402

OUT = ROOT / "analysis" / "stage2_1_results.csv"
FOLLOW_WINDOWS = ((1, 1), (1, 2), (1, 3))
GBR_GROUPS = {"colony_GBR", "samecol_GBR"}


def load_continents(nodes):
    countries = json.loads((ROOT / "data" / "raw" / "countries.json").read_text(encoding="utf-8"))
    continent = {row["cca3"]: row["region"] for row in countries}
    missing = sorted(set(nodes.index) - set(continent))
    if missing:
        raise ValueError(f"countries.json에 대륙 정보가 없는 ISO3: {missing}")
    out = nodes.copy()
    out["continent"] = out.index.map(continent)
    return out, continent


def discover_layers():
    """Find primary layer files only; nested supplementary files are not read."""
    paths = sorted((ROOT / "layers").glob("*/layer_*_edges.csv"))
    if not paths:
        raise FileNotFoundError("layers/<domain>/layer_*_edges.csv 파일을 찾지 못했습니다")
    return paths


def add_test(rows, layer, variant, test, family, stats, counts):
    rows.append({
        "layer": layer,
        "variant": variant,
        "test": test,
        "window": stats.get("window"),
        "test_family": family,
        "n_cross_edge_rows": counts["edge_rows"],
        "n_cross_pairs": counts["cross_pairs"],
        "n_adopter_pairs": stats.get("n_pairs", counts["adopter_pairs"]),
        "n_adopters": stats.get("n_adopters", counts["adopters"]),
        "gap_real": stats.get("mean_gap_real"),
        "gap_fake_avg": stats.get("mean_gap_fake_avg"),
        "share_real": stats.get("share_real"),
        "share_fake_avg": stats.get("share_fake_avg"),
        "p": stats.get("p"),
        "family_n": None,
        "alpha_bonferroni": None,
        "p_bonferroni": None,
        "status": "tested",
    })


def analyze_variant(edges, nodes, layer, variant, rows):
    cross = cross_continent_edges_from_frame(edges, nodes)
    cross_pairs = cross[["src", "dst"]].drop_duplicates()
    counts = {"edge_rows": len(cross), "cross_pairs": len(cross_pairs)}
    adopters = set(nodes.index[nodes.in_analysis == 1])
    adopter_pairs = cross.loc[cross.src.isin(adopters) & cross.dst.isin(adopters), ["src", "dst"]].drop_duplicates()
    counts["adopter_pairs"] = len(adopter_pairs)
    counts["adopters"] = len(set(adopter_pairs.src) | set(adopter_pairs.dst))
    if not counts["adopter_pairs"]:
        rows.append({
            "layer": layer, "variant": variant, "test": "not_run",
            "test_family": None, "n_cross_edge_rows": len(cross),
            "n_cross_pairs": len(cross_pairs), "n_adopter_pairs": 0,
            "n_adopters": 0, "status": "excluded: no cross-continent adopter pairs",
        })
        return

    for strata, family_suffix in ((None, "basic"), ("continent", "continent")):
        stage = stage1(cross, nodes, by_group=False, strata=strata).iloc[0]
        add_test(rows, layer, variant, f"stage1_{family_suffix}",
                 f"{variant}_stage1_{family_suffix}", stage.to_dict(), counts)
        for lo, hi in FOLLOW_WINDOWS:
            follow = follow_test(cross, nodes, lo=lo, hi=hi, strata=strata)
            add_test(rows, layer, variant, f"follow_{family_suffix}",
                     f"{variant}_follow_{family_suffix}", follow, counts)


def cross_continent_edges_from_frame(edges, nodes):
    """Filter already-read edges using the in-memory continent column."""
    required = {"src", "dst", "group"}
    if not required.issubset(edges.columns):
        raise ValueError(f"계층 엣지에 필요한 열이 없습니다: {sorted(required)}")
    labels = nodes["continent"]
    missing = sorted((set(edges.src) | set(edges.dst)) - set(labels.index))
    if missing:
        raise ValueError(f"nodes.csv에 없는 ISO3: {missing}")
    mask = [labels[src] != labels[dst] for src, dst in zip(edges.src, edges.dst)]
    return edges.loc[mask].copy()


def adjust_families(rows):
    """Apply Bonferroni separately to each prespecified test family.

    Basic and continent-conditioned tests are separate families. The British
    exclusion sensitivity analyses are also separate from the main networks.
    The family sizes are calculated from eligible inputs on every run.
    """
    result = pd.DataFrame(rows)
    tested = result[result.status == "tested"].copy()
    for family, ix in tested.groupby("test_family").groups.items():
        p = pd.to_numeric(result.loc[ix, "p"], errors="coerce")
        m = int(p.notna().sum())
        result.loc[ix, "family_n"] = m
        result.loc[ix, "alpha_bonferroni"] = 0.05 / m if m else None
        result.loc[ix, "p_bonferroni"] = (p * m).clip(upper=1.0)
    return result


def main():
    nodes, _ = load_continents(load_nodes())
    paths = discover_layers()
    rows = []

    for path in paths:
        layer = f"{path.parent.name}/{path.stem.removeprefix('layer_').removesuffix('_edges')}"
        edges = pd.read_csv(path)
        analyze_variant(edges, nodes, layer, "main", rows)

        # Compare the colony network with British-group edges removed. Rows
        # sharing another group remain connected through that other group.
        if path.parent.name == "language" and path.stem == "layer_colony_edges":
            no_gbr = edges.loc[~edges.group.isin(GBR_GROUPS)].copy()
            analyze_variant(no_gbr, nodes, layer, "no_gbr", rows)

    result = adjust_families(rows)
    result.to_csv(OUT, index=False)
    print(f"분석 반복 수 R={R}, seed={SEED}")
    print(f"Bonferroni 보정: test_family별 별도 적용; eligible layer 수와 창 수로 매 실행 계산")
    print(result.to_string(index=False))
    print(f"저장: {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
