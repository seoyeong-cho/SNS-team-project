"""
언어 + 식민 계층 (B 담당)
실행: python layers/language/fetch_external.py   (처음 한 번: ICOW・코드 변환표 받기)
      python layers/language/make_layer.py

기준・출처는 docs/layers/language.md. 순서는 layers/region/make_layer.py와 같음
1. 나라-그룹(또는 쌍) 표 → layer_<이름>_groups.csv / layer_<이름>_edges.csv
2. check_edges → structure → stage1 → robustness → adoption_test
3. 보조 검증: 대륙 안에서만 섞기(V2), 언어-식민 겹침, 선택별 결과 비교표

기본 분석은 이 폴더(layers/language/)에, 보조 분석은 supplementary/에 저장
→ 2단계 스크립트가 layers/*/layer_*_edges.csv를 읽어도 보조 계층이 섞이지 않게
"""
import html
import json
import re
import sys
from itertools import combinations
from pathlib import Path

import networkx as nx
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SUP = HERE / "supplementary"
EXT = HERE / "_external"
sys.path.append(str(ROOT / "src"))
from common import (adoption_test, analysis_countries, check_edges, groups_to_edges,  # noqa: E402
                    layer_graph, load_nodes, robustness, stage1, structure)

nodes = load_nodes()
C = {x["cca3"]: x for x in json.load(open(ROOT / "data" / "raw" / "countries.json", encoding="utf-8"))}
MIN_ADOPTERS = 5   # 해석 기준: 도입국 5개 이상인 그룹만 본문에서 해석


# =====================================================================
# 1. 언어
# =====================================================================
# 이름만 다른 같은 언어 → 하나로 (근거는 docs/layers/language.md 표)
LANG_ALIAS = {
    "English only": "English", "Castilian Spanish": "Spanish",
    "Afghan Persian or Dari": "Persian", "Dari": "Persian", "Persian Farsi": "Persian",
    "Moldovan/Romanian": "Romanian",
    "Bahasa Malaysia": "Malay", "Malay": "Malay",
    "Bahasa Indonesia": "Indonesian",
    "Standard Chinese or Mandarin": "Chinese (Mandarin)", "Mandarin": "Chinese (Mandarin)",
    "Kiswahili": "Swahili", "Kiswahili or Swahili": "Swahili", "Swahili/Kiswahili": "Swahili",
    "Bangla": "Bengali",
    "Bokmal Norwegian": "Norwegian", "Nynorsk Norwegian": "Norwegian",
    "Sesotho": "Sotho", "Sesotho or Sotho": "Sotho", "Setswana or Tswana": "Tswana",
    "isiZulu or Zulu": "Zulu", "isiXhosa or Xhosa": "Xhosa", "Sepedi or Pedi": "Pedi",
    "Xitsonga or Tsonga": "Tsonga", "siSwati or Swati": "Swati", "siSwati": "Swati",
    "Tshivenda or Venda": "Venda",
    "isiNdebele or Ndebele": "Ndebele (Southern)",   # 남아공 = 남부 은데벨레어
    "Ndebele": "Ndebele (Northern)",                 # 짐바브웨 = 북부 은데벨레어 (별개 언어)
    "Tamazight languages": "Tamazight",
    "Samoan": "Samoan", "Creole": "Haitian Creole",
    "Tigrigna": "Tigrinya",
    "Moldavian": "Romanian", "Persian (Farsi)": "Persian", "Filipino": "Filipino",
}
# 지역・소수 단위 공용어 표시 → 기본 네트워크에서 제외 (L2)
REGIONAL = re.compile(r"official (in|regional|minority)|only in municipalities|where native speakers"
                      r"|but locally used|official language in", re.I)

# Factbook 본문을 규칙으로 못 읽는 나라: 같은 본문・note에서 손으로 읽은 것 (origin = factbook_*)
FB_MANUAL = [
    # iso3, language, origin, 근거 (Factbook 원문 인용)
    ("GHA", "English", "factbook_note", "note: English is the official language"),
    ("PAK", "English", "factbook_note", "note: English (official; lingua franca ...)"),
    ("PHL", "Filipino", "factbook_note", "note: Filipino (based on Tagalog) and English are official languages"),
    ("PHL", "English", "factbook_note", "note: Filipino (based on Tagalog) and English are official languages"),
    ("TLS", "Tetum", "factbook_note", "note: Tetun and Portuguese are official languages"),
    ("TLS", "Portuguese", "factbook_note", "note: Tetun and Portuguese are official languages"),
    ("KGZ", "Kyrgyz", "factbook_text", "Kyrgyz (state language) → 국가어를 공용어로 봄"),
    ("GNQ", "French", "factbook_text", "other (includes ..., Portuguese (official), French (official) ...)"),
    ("GNQ", "Portuguese", "factbook_text", "other (includes ..., Portuguese (official), French (official) ...)"),
    ("MUS", "English", "factbook_text", "includes English, one of the two official languages of the National Assembly"),
    ("IND", "English", "factbook_text", "English is the subsidiary official language"),
] + [("ZWE", l, "factbook_text", "13 minority languages (official; includes ...)")
     for l in ["Chewa", "Chibarwe", "Kalanga", "Koisan", "Nambya", "Ndau", "Shangani", "Sotho",
               "Tonga (Zambia/Zimbabwe)", "Tswana", "Venda", "Xhosa"]]

# Factbook에 공용어가 전혀 없는 나라 → countries.json으로 보충 (L1). 공용어가 아닌 언어는 뺌
CJ_EXCLUDE = {("AZE", "Russian"): "아제르바이잔 헌법상 국가어는 아제르바이잔어뿐 (러시아어는 공용어 아님)",
              ("JAM", "Jamaican Patois"): "자메이카 공용어는 영어뿐 (파토아는 공용어 아님)"}
# Factbook 본문・note 어디에도 없지만 헌법상 공용어가 분명한 것 (origin = supplement_manual)
MANUAL_SUPPLEMENT = [
    ("IND", "Hindi", "인도 헌법 343조: 연방 공용어는 데바나가리 문자 힌디어 (Factbook 본문엔 비율만 있음)"),
    ("PAK", "Urdu", "파키스탄 헌법 251조: 국어는 우르두어 (Factbook note엔 영어만 공용어로 적힘)"),
]


def _clean(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(str(s or "")))).replace("\xa0", " ").strip()


def _split_top(s, seps=",;"):
    out, depth, cur = [], 0, ""
    for ch in s:
        depth += (ch == "(") - (ch == ")")
        if ch in seps and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    return [x.strip() for x in out + [cur] if x.strip()]


def parse_factbook(text):
    """본문에서 '(official)' 표시된 언어를 나라 단위 / 지역 단위로 나눠 뽑음"""
    national, dropped = [], []
    for seg in _split_top(_clean(text)):
        if not re.search(r"\bofficial\b", seg, re.I):
            continue
        parts = [p for p in re.split(r"\s+and\s+(?![^()]*\))", seg)] if seg.count("official") > 1 else [seg]
        for p in parts:
            if REGIONAL.search(p):
                dropped.append((p, "지역・소수 단위 공용어"))
                continue
            m = re.match(r"^(\w+) is the .*official language", p)
            name = m.group(1) if m else re.split(r"[(\d]", p)[0].strip(" ,")
            if not name or re.match(r"^(other|note|and|\d)", name, re.I):
                dropped.append((p, "언어 이름 아님 (묶음・주석) → 필요하면 FB_MANUAL"))
                continue
            name = re.sub(r"\s+only$", "", name)
            national.append((LANG_ALIAS.get(name, name), p))
    return national, dropped


def build_language_table():
    fb = pd.read_csv(ROOT / "data" / "raw" / "factbook_languages.csv")
    rows, audit = [], []
    for _, r in fb.iterrows():
        isos = {i for t in str(r.tld).split() for k, x in C.items() if t in (x.get("tld") or []) for i in [k]}
        for iso in isos & set(nodes.index):
            nat, drop = parse_factbook(r.languages_text)
            for lang, raw in nat:
                rows.append((iso, lang, "factbook_text", raw))
            for raw, why in drop:
                audit.append(dict(iso3=iso, raw=raw, action="drop", reason=why))
    df = pd.DataFrame(rows, columns=["iso3", "language", "origin", "basis"])
    df = pd.concat([df, pd.DataFrame(FB_MANUAL, columns=df.columns)])
    missing = sorted(set(nodes.index) - set(df.iso3))
    # countries.json 보충 (L1)
    for iso in missing:
        for lang in (C[iso].get("languages") or {}).values():
            lang = LANG_ALIAS.get(lang, lang)
            if (iso, lang) in CJ_EXCLUDE:
                audit.append(dict(iso3=iso, raw=lang, action="drop", reason=CJ_EXCLUDE[(iso, lang)]))
                continue
            df.loc[len(df)] = (iso, lang, "countries_json", "Factbook에 공용어 표시 없음 → countries.json languages")
    df = pd.concat([df, pd.DataFrame([(i, l, "supplement_manual", b) for i, l, b in MANUAL_SUPPLEMENT],
                                     columns=df.columns)])
    df = df.drop_duplicates(["iso3", "language"]).sort_values(["iso3", "language"]).reset_index(drop=True)
    assert set(df.iso3) == set(nodes.index), sorted(set(nodes.index) - set(df.iso3))
    df["origin_class"] = df.origin.map(lambda o: "factbook" if o.startswith("factbook") else "supplement")
    return df, pd.DataFrame(audit), missing


def lang_groups(table):
    """2개국 이상이 공유하는 공용어만 그룹 ('기타' 묶음 없음)"""
    cnt = table.groupby("language").iso3.nunique()
    keep = cnt[cnt >= 2].index
    return table[table.language.isin(keep)][["iso3", "language"]].rename(columns={"language": "group"}) \
        .drop_duplicates().sort_values(["group", "iso3"]).reset_index(drop=True)


# =====================================================================
# 2. 식민
# =====================================================================
# 종주국 코드(ICOW ColRuler / IndFrom) 정리
#   same_state: 지금도 같은 국가로 이어짐 → 종주국-식민지 직접 연결(colony_<ISO3>) 만듦
#   historical: 사라진 제국・전신 국가 → 같은 지배국 공유 연결(samecol_)만. 현대 국가 연결은 보조(colony_successor)에서만
RULERS = {
    2: ("USA", "same_state", ["USA"]), 200: ("GBR", "same_state", ["GBR"]), 210: ("NLD", "same_state", ["NLD"]),
    211: ("BEL", "same_state", ["BEL"]), 220: ("FRA", "same_state", ["FRA"]), 230: ("ESP", "same_state", ["ESP"]),
    235: ("PRT", "same_state", ["PRT"]), 325: ("ITA", "same_state", ["ITA"]), 740: ("JPN", "same_state", ["JPN"]),
    900: ("AUS", "same_state", ["AUS"]), 920: ("NZL", "same_state", ["NZL"]),
    640: ("OTTOMAN", "historical", ["TUR"]), 365: ("RUSSIA_USSR", "historical", ["RUS"]),
    300: ("AUSTRIA_HUNGARY", "historical", ["AUT", "HUN"]), 255: ("PRUSSIA_GERMANY", "historical", ["DEU"]),
    710: ("QING_CHINA", "historical", ["CHN"]),
}
# 보조(C4): 사라진 제국 → 현대 국가 직접 연결. 근거가 있는 것만
SUCCESSOR = {640: ("TUR", "터키공화국 = 오스만 제국의 승계국 (로잔 조약 1923)"),
             365: ("RUS", "러시아 = 소련의 계속국가 (1991 CIS 알마아타 의정서, 유엔 안보리 의석 승계)"),
             255: ("DEU", "ICOW가 프로이센과 독일을 같은 COW 국가(255)로 코딩"),
             710: ("CHN", "ICOW가 청과 중화인민공화국을 같은 COW 국가(710)로 코딩")}
# ICOW에 없는 현재 속령・자유연합국・왕실 직할령 (C3). 과거 식민 관계로 보지 않고 별도 관계 이름
TERRITORIES = [
    ("ASM", "USA", "dep_US_insular_area", "미국 비편입 영토 (unincorporated territory)"),
    ("MNP", "USA", "dep_US_insular_area", "미국 자치령 (commonwealth in political union with the US)"),
    ("BMU", "GBR", "dep_UK_overseas_territory", "영국 해외영토 (British Overseas Territory)"),
    ("SHN", "GBR", "dep_UK_overseas_territory", "영국 해외영토 (British Overseas Territory)"),
    ("IMN", "GBR", "dep_UK_crown_dependency", "영국 왕실 직할령 (Crown Dependency, 영국・해외영토 아님)"),
    ("NCL", "FRA", "dep_FR_overseas", "프랑스 특별 공동체 (sui generis collectivity)"),
    ("PYF", "FRA", "dep_FR_overseas", "프랑스 해외 집합체 (overseas collectivity / pays d'outre-mer)"),
    ("WLF", "FRA", "dep_FR_overseas", "프랑스 해외 집합체 (overseas collectivity)"),
    ("COK", "NZL", "dep_NZ_free_association", "뉴질랜드와 자유연합 (self-governing in free association)"),
    ("NIU", "NZL", "dep_NZ_free_association", "뉴질랜드와 자유연합 (self-governing in free association)"),
]
COW_FIX = {345: "SRB"}   # countrycode에 345(Serbia/Yugoslavia) → ISO3 없음. nodes의 SRB가 이 행


def load_icow():
    p = EXT / "icow" / "coldata110.csv"
    if not p.exists():
        raise SystemExit("ICOW 없음 → 먼저 python layers/language/fetch_external.py")
    ic = pd.read_csv(p, encoding="utf-8-sig")
    cl = pd.read_csv(EXT / "countrycode_codelist.csv", low_memory=False).dropna(subset=["cown"])
    cow2iso = {**dict(zip(cl.cown.astype(int), cl.iso3c)), **COW_FIX}
    ic["iso3"] = ic.State.map(cow2iso)
    name = dict(zip(ic.State, ic.Name))
    match = pd.DataFrame({"iso3": nodes.index})
    match["in_icow"] = match.iso3.isin(ic.iso3).astype(int)
    match["cow_code"] = match.iso3.map(dict(zip(ic.iso3, ic.State))).astype("Int64")
    match["note"] = match.apply(lambda r: "COW 345 → SRB 수동 매칭" if r.iso3 == "SRB" else
                                ("ICOW 대상 아님 (독립국 아님) → 보조 colony_with_dependencies에서 별도 관계"
                                 if r.iso3 in {t[0] for t in TERRITORIES} else ""), axis=1)
    ic = ic[ic.iso3.isin(nodes.index)].copy()
    assert not ic.iso3.duplicated().any()
    return ic, name, match


# IndFrom에만 나오는 사라진 연방・국가 이름 (ICOW 이름이 없거나 현재 국가 이름과 헷갈리는 것)
HIST_LABEL = {89: "CENTRAL_AMERICA_FED", 315: "CZECHOSLOVAKIA", 345: "YUGOSLAVIA", 432: "MALI_FEDERATION",
              678: "NORTH_YEMEN", 730: "KOREA_UNIFIED"}


def _ruler_label(code, name):
    if code in RULERS:
        return RULERS[code][0]
    return HIST_LABEL.get(code) or re.sub(r"\W+", "_", name.get(code, str(code))).strip("_").upper()


def colony_edges(ic, name, col="ColRuler", keep=None, successor=False):
    """종주국별: 같은 지배국 공유 쌍(samecol_<지배국>) + 지금도 이어지는 지배국과의 직접 쌍(colony_<ISO3>)

    col: 'ColRuler'(기본, 주요 식민 지배국) 또는 'IndFrom'(보조, 독립 상대국)
    keep: 이 iso3만 남김 (해외 식민 보조)
    """
    d = ic[(ic[col] > 0) & (ic[col] != ic.State)]
    if keep is not None:
        d = d[d.iso3.isin(keep)]
    rows = []
    for code, sub in d.groupby(col):
        lab = _ruler_label(code, name)
        for a, b in combinations(sorted(sub.iso3), 2):
            rows.append((a, b, f"samecol_{lab}"))
        direct = None
        if code in RULERS and RULERS[code][1] == "same_state":
            direct = RULERS[code][0]
        elif code not in RULERS and col == "IndFrom":
            cand = ic.loc[ic.State == code, "iso3"]           # 독립 상대가 지금 있는 나라 (예: 콜롬비아)
            # 사라진 연방・국가(중미연방, 체코슬로바키아, 유고, 말리연방, 북예멘, 통일 한국)는 현대 국가와 안 이음
            direct = cand.iloc[0] if len(cand) and code not in (89, 315, 345, 432, 678, 730) else None
        elif successor and code in SUCCESSOR:
            direct = SUCCESSOR[code][0]
        if direct:
            for c in sub.iso3:
                if c != direct:
                    rows.append((*sorted([c, direct]), f"colony_{direct}"))
    e = pd.DataFrame(rows, columns=["src", "dst", "group"]).drop_duplicates()
    return e.sort_values(["group", "src", "dst"]).reset_index(drop=True)


def overseas_set(ic):
    """관계 유형으로 '해외 식민'만 고름 (특정 제국을 통째로 빼지 않음)

    육상 연속 지배: 식민지가 지배국 본토와, 같은 지배국 아래 있던 나라들을 거쳐 육로(countries.json borders)로 이어짐
    해외 식민: 그런 육로가 없음 (바다 건너 지배)
    """
    out, kind = [], {}
    for code, sub in ic[ic.ColRuler > 0].groupby("ColRuler"):
        core = RULERS.get(code, (None, None, []))[2]
        S = set(sub.iso3) | set(core)
        G = nx.Graph()
        G.add_nodes_from(S)
        G.add_edges_from((a, b) for a in S for b in (C.get(a, {}).get("borders") or []) if b in S)
        for c in sub.iso3:
            land = any(nx.has_path(G, c, k) for k in core if k in G)
            kind[c] = "contiguous" if land else "overseas"
            if not land:
                out.append(c)
    return out, kind


def territory_edges():
    rows = []
    for iso, sov, grp, _ in TERRITORIES:
        rows.append((*sorted([iso, sov]), grp))
    t = pd.DataFrame(TERRITORIES, columns=["iso3", "sov", "group", "status"])
    for (grp, sov), sub in t.groupby(["group", "sov"]):
        for a, b in combinations(sorted(sub.iso3), 2):
            rows.append((a, b, grp))
    return pd.DataFrame(rows, columns=["src", "dst", "group"]).drop_duplicates()


# =====================================================================
# 3. 분석
# =====================================================================
def nodes_with_continent():
    n = nodes.copy()
    n["continent"] = [C[k]["region"] for k in n.index]   # 메모리에서만 붙임 (data/processed 안 바꿈)
    return n


def run(name, edges, out_dir, groups=None, v2=False):
    out_dir.mkdir(exist_ok=True)
    edges = edges.drop_duplicates().sort_values(["group", "src", "dst"]).reset_index(drop=True)
    check_edges(edges, nodes)
    if groups is not None:
        groups.to_csv(out_dir / f"layer_{name}_groups.csv", index=False)
    edges.to_csv(out_dir / f"layer_{name}_edges.csv", index=False)
    st = structure(layer_graph(edges, nodes))
    res = stage1(edges, nodes)
    res.to_csv(out_dir / f"result_{name}.csv", index=False)
    rob = robustness(edges, nodes)
    rob.to_csv(out_dir / f"robustness_{name}.csv", index=False)
    ad = adoption_test(edges, nodes)
    pd.DataFrame([ad]).to_csv(out_dir / f"adoption_{name}.csv", index=False)
    allr = res.iloc[0]
    summ = dict(layer=name, **st, unique_pairs=len(edges[["src", "dst"]].drop_duplicates()),
                adopter_pairs=int(allr.n_pairs), adopters_linked=int(allr.n_adopters),
                gap_real=allr.mean_gap_real, gap_fake=allr.mean_gap_fake_avg,
                gap_diff=round(allr.mean_gap_fake_avg - allr.mean_gap_real, 2), p=allr.p,
                **{f"p_{r.shuffle}": r.p for r in rob.itertuples() if r.shuffle != "basic"},
                adopt_same_real=ad["same_status_real"], adopt_same_fake=ad["same_status_fake_avg"], adopt_p=ad["p"])
    if v2:
        nc = nodes_with_continent()
        cres = stage1(edges, nc, strata="continent")
        v = res.merge(cres[["group", "mean_gap_fake_avg", "p"]], on="group", suffixes=("_basic", "_continent"))
        v.insert(len(v.columns), "interpret", v.n_adopters >= MIN_ADOPTERS)
        v.to_csv(out_dir / f"v2_continent_{name}.csv", index=False)
        summ["p_continent"] = v.iloc[0].p_continent
        summ["gap_fake_continent"] = v.iloc[0].mean_gap_fake_avg_continent
    print(f"[{name}] edges={summ['unique_pairs']} adopter_pairs={summ['adopter_pairs']} "
          f"real={summ['gap_real']} fake={summ['gap_fake']} p={summ['p']}")
    return summ


def pair_set(edges, only_adopters=False):
    s = set(map(tuple, edges[["src", "dst"]].drop_duplicates().to_numpy()))
    if only_adopters:
        ac = set(analysis_countries(nodes))
        s = {p for p in s if p[0] in ac and p[1] in ac}
    return s


def overlap(a_name, a, b_name, b):
    rows = []
    for base, only in [("all_204", False), ("adopters_114", True)]:
        A, B = pair_set(a, only), pair_set(b, only)
        inter = len(A & B)
        rows.append(dict(universe=base, pairs_a=len(A), pairs_b=len(B), both=inter,
                         share_of_a=round(inter / len(A), 3) if A else None,
                         share_of_b=round(inter / len(B), 3) if B else None,
                         jaccard=round(inter / len(A | B), 3) if A | B else None,
                         a=a_name, b=b_name))
    return rows


if __name__ == "__main__":
    SUP.mkdir(exist_ok=True)
    summary = []

    # ---------- 언어 ----------
    table, lang_audit, lang_missing = build_language_table()
    table.to_csv(HERE / "language_country_table.csv", index=False)
    lang_audit.to_csv(HERE / "language_dropped.csv", index=False)
    g_all = lang_groups(table)
    g_fb = lang_groups(table[table.origin_class == "factbook"])
    print("Factbook 공용어 없음 → 보충:", lang_missing)
    e_lang = groups_to_edges(g_all, nodes)
    summary.append(run("language", e_lang, HERE, g_all, v2=True))
    summary.append(run("language_factbook_only", groups_to_edges(g_fb, nodes), SUP, g_fb))

    # ---------- 식민 ----------
    ic, cname, match = load_icow()
    match.to_csv(HERE / "colony_matching.csv", index=False)
    e_col = colony_edges(ic, cname)
    summary.append(run("colony", e_col, HERE, v2=True))
    summary.append(run("colony_indfrom", colony_edges(ic, cname, col="IndFrom"), SUP))
    ov, kind = overseas_set(ic)
    pd.DataFrame(sorted(kind.items()), columns=["iso3", "relation_type"]).to_csv(SUP / "colony_relation_type.csv", index=False)
    summary.append(run("colony_overseas", colony_edges(ic, cname, keep=ov), SUP))
    summary.append(run("colony_with_dependencies", pd.concat([e_col, territory_edges()]), SUP))
    summary.append(run("colony_successor", colony_edges(ic, cname, successor=True), SUP))

    # ---------- 겹침 ----------
    ov_rows = overlap("language", e_lang, "colony", e_col)
    for g_lang, g_col in [("English", "samecol_GBR"), ("French", "samecol_FRA"), ("Spanish", "samecol_ESP"),
                          ("Portuguese", "samecol_PRT"), ("Arabic", "samecol_OTTOMAN"), ("Russian", "samecol_RUSSIA_USSR")]:
        ov_rows += overlap(g_lang, e_lang[e_lang.group == g_lang], g_col, e_col[e_col.group == g_col])
    pd.DataFrame(ov_rows).to_csv(HERE / "overlap_language_colony.csv", index=False)

    s = pd.DataFrame(summary)
    s.insert(1, "analysis", s.layer.map(lambda x: "기본" if x in ("language", "colony") else "보조"))
    s.to_csv(HERE / "summary_language_colony.csv", index=False)
    print(s.to_string(index=False))
    print(pd.DataFrame(ov_rows).to_string(index=False))
