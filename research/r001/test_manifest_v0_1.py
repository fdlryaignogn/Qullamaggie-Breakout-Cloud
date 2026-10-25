"""R-001 manifest structural and point-in-time guards; stdlib only."""
import json
from datetime import date
from pathlib import Path

def validate(data):
    errors=[]
    cases=data["cases"]
    if {c["symbol"] for c in cases}!={"MNST","NVDA","AAPL"} or len(cases)!=3:
        errors.append("case universe mismatch")
    if len({c["case_id"] for c in cases})!=3:
        errors.append("duplicate case ID")
    for case in cases:
        if case["breakout_date"] is not None and not case["event_as_of"]:
            errors.append("breakout without cutoff")
        if case["winner_label"] is not None and not case["ohlcv_source"]:
            errors.append("winner without OHLCV")
        for e in case["evidence"]:
            if not e["url"].startswith("https://"):
                errors.append("invalid source URL")
            if e["publication_date"]:
                date.fromisoformat(e["publication_date"])
            if e["eligibility"]=="VERIFIED_PUBLIC_AT_CUTOFF":
                if not (e["publication_date"] and case["event_as_of"] and e["publication_date"]<=case["event_as_of"][:10]):
                    errors.append("lookahead or undated claim")
    if data["quality"]["verified_breakout_cases"]>sum(bool(c["breakout_date"] and c["ohlcv_source"]) for c in cases):
        errors.append("inflated verified count")
    return errors

if __name__=="__main__":
    data=json.loads(Path(__file__).with_name("evidence_manifest_v0_1.json").read_text())
    errors=validate(data)
    assert not errors, errors
    print("PASS: schema, identities, null events, and as-of safeguards; NOT historical breakout verification")
