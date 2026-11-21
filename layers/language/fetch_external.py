"""
언어・식민 계층 (B 담당) 외부 자료 받기
실행: python layers/language/fetch_external.py

받는 것
1. ICOW Colonial History v1.1 (Hensel)  → layers/language/_external/icow/   (재배포 안 함, git 제외)
2. countrycode 변환표 (COW → ISO3)        → layers/language/_external/       (GPL-3, 재배포 안 함, git 제외)
3. CIA World Factbook 아카이브 (CC0)      → data/raw/factbook_languages.csv  (언어 항목만 원문 그대로, 커밋함)
   --factbook 옵션을 줄 때만 다시 만듦 (아카이브 전체 ≈ 수십 MB)

버전 고정: 아래 URL・커밋을 바꾸면 결과가 달라질 수 있음 → 바꾸면 docs/layers/language.md도 같이 고칠 것
"""
import hashlib
import io
import json
import re
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EXT = HERE / "_external"

ICOW_URL = "https://www.paulhensel.org/Data/colhist.zip"
COUNTRYCODE_COMMIT = "9546912ab023a6445cbe7b5620f5103446d84e52"
COUNTRYCODE_URL = ("https://raw.githubusercontent.com/vincentarelbundock/countrycode/"
                   f"{COUNTRYCODE_COMMIT}/dictionary/codelist_without_cldr.csv")
FACTBOOK_COMMIT = "144d6977b2b01ac1cbd220de754c0a005616760b"   # 마지막 데이터 자동 갱신 2026-01-22 이후 README만 바뀐 커밋
FACTBOOK_URL = f"https://codeload.github.com/factbook/factbook.json/tar.gz/{FACTBOOK_COMMIT}"
FACTBOOK_OUT = ROOT / "data" / "raw" / "factbook_languages.csv"


def get(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()


def fetch_icow():
    b = get(ICOW_URL)
    print("ICOW zip sha256:", hashlib.sha256(b).hexdigest())
    out = EXT / "icow"
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(b)) as z:
        for name in z.namelist():
            if name.endswith(("coldata110.csv", "colcode.pdf")):
                (out / Path(name).name).write_bytes(z.read(name))
    print("→", out)


def fetch_countrycode():
    EXT.mkdir(parents=True, exist_ok=True)
    (EXT / "countrycode_codelist.csv").write_bytes(get(COUNTRYCODE_URL))
    print("→", EXT / "countrycode_codelist.csv")


def fetch_factbook():
    """아카이브의 국가 프로필에서 언어 항목과 인터넷 도메인(.kr 등, ISO 매칭용)만 원문 그대로 뽑음"""
    rows = []
    with tarfile.open(fileobj=io.BytesIO(get(FACTBOOK_URL)), mode="r:gz") as t:
        for m in t.getmembers():
            p = m.name.split("/")
            if len(p) != 3 or not p[2].endswith(".json") or p[1] in ("meta", "oceans", "antarctica"):
                continue
            d = json.load(t.extractfile(m))
            tld = (d.get("Communications", {}).get("Internet country code") or {}).get("text", "")
            lang = (d.get("People and Society") or {}).get("Languages") or {}
            inner = lang.get("Languages", lang)            # 형식이 두 가지 섞여 있음
            note = lang.get("note") or inner.get("note") or ""
            lang = {"text": inner.get("text", ""), "note": note.get("text", "") if isinstance(note, dict) else note}
            rows.append(dict(gec=p[2][:-5], region_folder=p[1],
                             name=(d.get("Government", {}).get("Country name", {})
                                   .get("conventional short form", {}).get("text", "")),
                             tld=" ".join(re.findall(r"\.[a-z]{2}", tld)),
                             languages_text=lang.get("text", ""), languages_note=lang.get("note", "")))
    df = pd.DataFrame(rows).sort_values("gec")
    df.insert(0, "source", f"factbook/factbook.json@{FACTBOOK_COMMIT[:7]}")
    df.to_csv(FACTBOOK_OUT, index=False, encoding="utf-8")
    print("→", FACTBOOK_OUT, len(df), "profiles")


if __name__ == "__main__":
    fetch_icow()
    fetch_countrycode()
    if "--factbook" in sys.argv or not FACTBOOK_OUT.exists():
        fetch_factbook()
