"""Read-only SEC EDGAR fundamental snapshots for *human-confirmed* Stage 3 triggers.

No price quotes, forecasts, institutional buy assertions or insider buy assertions.
SEC facts show public historical filings only. A Form 4 filing is not itself
a purchase; a 13F filing represents delayed holdings, not same-day flows.

To make SEC automated access accountable, SEC_USER_AGENT must be explicitly
configured with a project contact identifier (repository secret).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
DEFAULT_LATEST = ROOT / "site" / "data" / "latest.json"
DEFAULT_OUT = ROOT / "site" / "data" / "stage4_fundamentals.json"
SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9.-]{0,11}$")
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FUNDAMENTAL_TAGS = {
    "revenue_fy": (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues", "SalesRevenueNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueGoodsNet",
    ),
    "net_income_fy": ("NetIncomeLoss",),
    "eps_diluted_fy": ("EarningsPerShareDiluted",),
}


def sec_get_json(url: str, *, user_agent: str) -> dict:
    if not user_agent or len(user_agent.strip()) < 12 or "@" not in user_agent:
        raise ValueError("SEC_USER_AGENT must identify a real project contact")
    if not url.startswith(("https://www.sec.gov/", "https://data.sec.gov/")):
        raise ValueError("Unsupported SEC data source")
    request = Request(url, headers={
        "User-Agent": user_agent,
        "Accept": "application/json",
        "Accept-Encoding": "identity",
    })
    try:
        with urlopen(request, timeout=18) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError("SEC fetch unavailable: " + type(exc).__name__) from exc


def ticker_cik_map(payload: dict) -> dict[str, int]:
    out = {}
    if not isinstance(payload, dict):
        return out
    for row in payload.values():
        if isinstance(row, dict) and SYMBOL_RE.fullmatch(str(row.get("ticker", ""))):
            try:
                cik = int(row["cik_str"])
                if cik > 0:
                    out[row["ticker"]] = cik
            except (ValueError, TypeError, KeyError):
                pass
    return out


def _annual_values(facts: dict, tag: str, unit: str) -> list[dict]:
    values = (facts.get("facts") or {}).get("us-gaap", {}).get(tag, {}).get(
        "units", {}).get(unit, [])
    found = []
    for row in values:
        if not isinstance(row, dict) or row.get("form") != "10-K" or row.get("fp") != "FY":
            continue
        try:
            start = date.fromisoformat(row["start"])
            end = date.fromisoformat(row["end"])
            filed = date.fromisoformat(row["filed"])
            n = float(row["val"])
            if not (320 <= (end - start).days <= 380) or not math.isfinite(n):
                continue
            accn = str(row.get("accn", ""))
            if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accn):
                continue
            found.append({"value": n, "start": start.isoformat(),
                          "period_end": end.isoformat(), "filed": filed.isoformat(),
                          "form": "10-K", "accn": accn, "tag": tag, "unit": unit})
        except (KeyError, ValueError, TypeError, OverflowError):
            continue
    # Amended/latest filings may duplicate the same annual period; keep the
    # latest publicly filed version of that same period.
    by_end = {}
    for row in found:
        end = row["period_end"]
        if end not in by_end or row["filed"] > by_end[end]["filed"]:
            by_end[end] = row
    return sorted(by_end.values(), key=lambda x: (x["period_end"], x["filed"]), reverse=True)


def _filing_url(cik: int, accn: str) -> str:
    return ("https://www.sec.gov/Archives/edgar/data/" + str(cik) + "/" +
            accn.replace("-", "") + "/" + accn + "-index.htm")


def annual_fundamentals(facts: dict, cik: int) -> dict:
    result = {}
    selected_revenue = None
    for key, tags in FUNDAMENTAL_TAGS.items():
        unit = "USD/shares" if key == "eps_diluted_fy" else "USD"
        candidates = []
        for preference, tag in enumerate(tags):
            for row in _annual_values(facts, tag, unit):
                candidates.append((row["period_end"], row["filed"], -preference, row))
        if not candidates:
            continue
        chosen = max(candidates, key=lambda c: c[:3])[3]
        result[key] = {
            "value": chosen["value"], "unit": unit, "period_end": chosen["period_end"],
            "filed": chosen["filed"], "form": chosen["form"],
            "source_url": _filing_url(cik, chosen["accn"]),
            "us_gaap_tag": chosen["tag"],
        }
        if key == "revenue_fy":
            selected_revenue = chosen
    if selected_revenue:
        same_tag = _annual_values(facts, selected_revenue["tag"], "USD")
        older = [row for row in same_tag if
                 330 <= (date.fromisoformat(selected_revenue["period_end"]) -
                         date.fromisoformat(row["period_end"])).days <= 400]
        if older and older[0]["value"] != 0:
            growth = 100 * (selected_revenue["value"] / older[0]["value"] - 1)
            if math.isfinite(growth):
                result["revenue_yoy_pct"] = {
                    "value": round(growth, 3),
                    "period_end": selected_revenue["period_end"],
                    "filed": selected_revenue["filed"],
                    "compared_period_end": older[0]["period_end"],
                    "source_url": _filing_url(cik, selected_revenue["accn"]),
                    "unit": "percent",
                }
    return result


def recent_form4_summary(submissions: dict, *, today: date) -> dict | None:
    rows = ((submissions.get("filings") or {}).get("recent") or {})
    forms, filed = rows.get("form"), rows.get("filingDate")
    if not isinstance(forms, list) or not isinstance(filed, list):
        return None
    relevant = []
    earliest = today - timedelta(days=90)
    for form, filed_at in zip(forms, filed):
        if form not in ("4", "4/A"):
            continue
        try:
            day = date.fromisoformat(filed_at)
            if earliest <= day <= today:
                relevant.append(day.isoformat())
        except (TypeError, ValueError):
            pass
    return {"recent_count": len(relevant),
            "latest_filed": max(relevant) if relevant else None,
            "window_days": 90,
            "filing_only_not_purchase_confirmation": True}


def selected_symbols(latest: dict) -> list[str]:
    state = latest.get("state") or {}
    items = state.get("3") or []
    return sorted({r["symbol"] for r in items if isinstance(r, dict)
                   and r.get("status") == "TRIGGERED"
                   and isinstance(r.get("symbol"), str)
                   and SYMBOL_RE.fullmatch(r["symbol"])})


def generate(latest: dict, *, user_agent: str, fetch=sec_get_json,
             today: date | None = None, cap: int = 60) -> dict:
    today = today or datetime.now(timezone.utc).date()
    symbols = selected_symbols(latest)
    metadata = latest.get("metadata") or {}
    if metadata.get("phase") != "success":
        raise ValueError("A successful Stage 3 snapshot is required")
    if len(symbols) > cap:
        raise ValueError("Too many triggers for a single SEC refresh; split refresh rather than silently omit tickers")
    result = {
        "schema_version": 1, "source": "US SEC EDGAR companyfacts / submissions",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "snapshot_as_of": metadata.get("as_of_date"), "triggered_count": len(symbols),
        "records": {}, "institutional_buying_verified": False,
        "insider_buying_verified": False,
    }
    if not symbols:
        result["source_status"] = "no_confirmed_triggers"
        return result
    if not user_agent or "@" not in user_agent:
        result["source_status"] = "not_configured"
        for symbol in symbols:
            result["records"][symbol] = {"status": "not_configured",
                                         "note": "SEC_USER_AGENT not configured"}
        return result
    mapping = ticker_cik_map(fetch(TICKERS_URL, user_agent=user_agent))
    for symbol in symbols:
        cik = mapping.get(symbol)
        if not cik:
            result["records"][symbol] = {"status": "unavailable",
                                         "note": "Ticker not mapped to a SEC CIK"}
            continue
        try:
            facts = fetch("https://data.sec.gov/api/xbrl/companyfacts/CIK" +
                          str(cik).zfill(10) + ".json", user_agent=user_agent)
            time.sleep(0.24)
            submissions = fetch("https://data.sec.gov/submissions/CIK" +
                                str(cik).zfill(10) + ".json", user_agent=user_agent)
            time.sleep(0.24)
            result["records"][symbol] = {
                "status": "ok", "cik": str(cik), "company": str(facts.get("entityName") or symbol)[:140],
                "form4": recent_form4_summary(submissions, today=today),
                **annual_fundamentals(facts, cik),
                "institutional_buying_status": "UNVERIFIED",
                "insider_purchase_status": "UNVERIFIED",
            }
        except (RuntimeError, ValueError, KeyError, TypeError) as exc:
            result["records"][symbol] = {
                "status": "unavailable", "cik": str(cik),
                "note": "SEC data unavailable (" + type(exc).__name__ + ")",
            }
    result["source_status"] = "ok_with_possible_missing_issuer_data"
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_LATEST)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--cap", type=int, default=60)
    args = parser.parse_args()
    latest = json.loads(args.snapshot.read_text(encoding="utf-8"))
    result = generate(latest, user_agent=os.environ.get("SEC_USER_AGENT", ""),
                      cap=args.cap)
    # Never write API secrets or personal account equity to public data.
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print("Stage 4 SEC: " + result["source_status"] + "; triggers=" +
          str(result["triggered_count"]) + "; records=" + str(len(result["records"])))


if __name__ == "__main__":
    main()
