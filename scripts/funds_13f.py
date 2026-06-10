#!/usr/bin/env python3
"""跟踪基金 13F 持仓(免费、SEC 官方)→ feed/funds/<slug>.json。

- 每周由 funds-13f.yml 运行:发现新 13F-HR 即解析并覆盖 JSON(accession 变了才算新)。
- 13F 客观限制:季度披露 + ≤45 天延迟;仅美股多头与期权;无空头/现金明细。
- 仅标准库。Ticker 映射:静态表(13F 只给 CUSIP/名称);映射不到保留 cusip。

新增基金:往 FUNDS 里加一项即可。
"""
from __future__ import annotations

import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "feed" / "funds"
UA = {"User-Agent": "stock-analysis-dashboard admin@example.com"}  # SEC 要求带 UA

FUNDS = [
    {"slug": "situational-awareness", "name": "Situational Awareness LP",
     "manager": "Leopold Aschenbrenner", "cik": "0002045724"},
]

# CUSIP → 看板 symbol(13F 不含 ticker;新持仓映射不到时保留 cusip,人工补一行即可)
CUSIP_MAP = {
    "038169207": "US:APLD", "05614L209": "US:BW", "G11448100": "US:BTDR", "09173B107": "US:BITF",
    "093712107": "US:BE", "17253J106": "US:CIFR", "18452B209": "US:CLSK", "19247G107": "US:COHR",
    "21874A106": "US:CORZ", "21873S108": "US:CRWV", "26884L109": "US:EQT", "44812J104": "US:HUT",
    "Q4982L109": "US:IREN", "456788108": "US:INFY", "458140100": "US:INTC", "49427F108": "US:KRC",
    "53115L104": "US:LBRT", "55024U109": "US:LITE", "73933G202": "US:PSIX", "74347M108": "US:PUMP",
    "767292105": "US:RIOT", "80004C200": "US:SNDK", "83418M103": "US:SEI", "M87915274": "US:TSEM",
    "G96115103": "US:WYFI",
}


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def latest_13f(cik: str):
    sub = json.loads(get(f"https://data.sec.gov/submissions/CIK{cik}.json"))
    r = sub["filings"]["recent"]
    for i, form in enumerate(r["form"]):
        if form == "13F-HR":
            return {"accession": r["accessionNumber"][i], "filed": r["filingDate"][i],
                    "asof": r["reportDate"][i]}
    return None


def info_table_url(cik: str, accession: str) -> str | None:
    acc = accession.replace("-", "")
    base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}"
    idx = json.loads(get(f"{base}/index.json"))
    for item in idx["directory"]["item"]:
        n = item["name"]
        if n.endswith(".xml") and "primary_doc" not in n:
            return f"{base}/{n}"
    return None


def parse_positions(xml_bytes: bytes) -> list[dict]:
    ns = {"n": "http://www.sec.gov/edgar/document/thirteenf/informationtable"}
    root = ET.fromstring(xml_bytes)
    rows = []
    for it in root.findall("n:infoTable", ns):
        def t(tag, d=None):
            el = it.find(f"n:{tag}", ns)
            return el.text.strip() if el is not None and el.text else d
        sh = it.find("n:shrsOrPrnAmt/n:sshPrnamt", ns)
        rows.append({
            "name": t("nameOfIssuer"), "cusip": t("cusip"),
            "value": int(t("value", "0")), "shares": int(sh.text) if sh is not None else 0,
            "putCall": t("putCall"),
        })
    # 同 CUSIP 聚合(正股 + 期权拆行)
    agg: dict[str, dict] = {}
    for r in rows:
        a = agg.setdefault(r["cusip"], {
            "ticker": CUSIP_MAP.get(r["cusip"], r["cusip"]), "name": r["name"],
            "value": 0, "shares": 0, "kinds": set(),
        })
        a["value"] += r["value"]
        a["shares"] += r["shares"]
        a["kinds"].add(r["putCall"] or "股票")
    out = []
    for a in agg.values():
        kinds = sorted(a.pop("kinds"))
        a["type"] = "+".join("Call" if k == "Call" else "Put(看空)" if k == "Put" else "股票" for k in kinds)
        out.append(a)
    out.sort(key=lambda x: -x["value"])
    return out


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    changed = False
    for f in FUNDS:
        out_path = OUT_DIR / f"{f['slug']}.json"
        old = {}
        if out_path.exists():
            try:
                old = json.loads(out_path.read_text())
            except Exception:  # noqa: BLE001
                pass
        meta = latest_13f(f["cik"])
        if not meta:
            print(f"{f['name']}: 无 13F-HR")
            continue
        if old.get("accession") == meta["accession"]:
            print(f"{f['name']}: 无新披露({meta['asof']} 仍是最新)")
            continue
        url = info_table_url(f["cik"], meta["accession"])
        if not url:
            print(f"{f['name']}: 找不到 info table", file=sys.stderr)
            continue
        positions = parse_positions(get(url))
        doc = {
            "fund": f["name"], "manager": f["manager"], "cik": f["cik"],
            "source": "SEC 13F-HR", "accession": meta["accession"],
            "asof": meta["asof"], "filed": meta["filed"],
            "note": "13F 为季度披露+最多45天延迟,仅含美股多头与期权,不含空头/现金/非美仓位。",
            "positions": positions,
            "summary": {"total_value": sum(p["value"] for p in positions), "n_positions": len(positions)},
        }
        out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
        print(f"{f['name']}: 更新 → {meta['asof']}(filed {meta['filed']},{len(positions)} 仓位)")
        changed = True
    return 0 if True else 1  # 始终成功;是否提交由工作流 git diff 决定


if __name__ == "__main__":
    raise SystemExit(main())
