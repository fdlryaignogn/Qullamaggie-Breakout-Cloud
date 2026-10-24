"""Stage 4 SEC public fundamentals: facts, provenance, no fake ownership signals."""
from datetime import date

import pytest

import stage4_sec_fundamentals as stage4


def latest(*statuses):
    return {"metadata": {"phase": "success", "as_of_date": "2026-10-23"},
            "state": {"3": [{"symbol": s, "status": status}
                            for s, status in statuses]}}


def fact(value, end, filed, accn="0000000123-26-000456", start=None):
    start = start or (str(int(end[:4]) - 1) + end[4:])
    # For normal Jan-Dec company years, start is Jan 1 of end year.
    start = end[:4] + "-01-01"
    return {"start": start, "end": end, "filed": filed,
            "val": value, "form": "10-K", "fp": "FY",
            "accn": accn}


def financial_facts():
    revenue = [fact(200_000_000, "2024-12-31", "2025-02-20",
                    "0000000123-25-000111"),
               fact(250_000_000, "2025-12-31", "2026-02-20")]
    return {"entityName": "ABC COMPANY", "facts": {"us-gaap": {
        "RevenueFromContractWithCustomerExcludingAssessedTax": {
            "units": {"USD": revenue}},
        "NetIncomeLoss": {"units": {"USD": [
            fact(40_000_000, "2025-12-31", "2026-02-20")]}},
        "EarningsPerShareDiluted": {"units": {"USD/shares": [
            fact(1.25, "2025-12-31", "2026-02-20")]}},
    }}}


def test_stage4_scope_only_human_confirmed_trigger_not_watch_or_cross():
    snapshot = latest(("ABC", "TRIGGERED"), ("XYZ", "WATCH"), ("BAD/", "TRIGGERED"))
    assert stage4.selected_symbols(snapshot) == ["ABC"]


def test_annual_xbrl_source_and_yoy_use_same_tag_only():
    result = stage4.annual_fundamentals(financial_facts(), 123)
    assert result["revenue_fy"]["value"] == 250_000_000
    assert result["revenue_fy"]["period_end"] == "2025-12-31"
    assert result["revenue_fy"]["filed"] == "2026-02-20"
    assert result["revenue_fy"]["source_url"].startswith("https://www.sec.gov/Archives/")
    assert result["net_income_fy"]["value"] == 40_000_000
    assert result["eps_diluted_fy"]["value"] == 1.25
    assert result["revenue_yoy_pct"]["value"] == 25.0
    assert "institutional_buying" not in result
    assert "insider_buying" not in result


def test_no_revenue_does_not_turn_missing_into_zero():
    facts = {"facts": {"us-gaap": {"NetIncomeLoss": {
        "units": {"USD": [fact(-2_000_000, "2025-12-31", "2026-02-20")]}}}}}
    result = stage4.annual_fundamentals(facts, 123)
    assert result["net_income_fy"]["value"] == -2_000_000
    assert "revenue_fy" not in result
    assert "revenue_yoy_pct" not in result


def test_partial_or_ytd_cashflow_not_labelled_as_annual():
    facts = financial_facts()
    tag = facts["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"]
    tag["units"]["USD"].append({"start": "2026-01-01", "end": "2026-03-31",
                                   "filed": "2026-05-10", "val": 90_000_000,
                                   "form": "10-K", "fp": "FY",
                                   "accn": "0000000123-26-000789"})
    result = stage4.annual_fundamentals(facts, 123)
    assert result["revenue_fy"]["period_end"] == "2025-12-31"


def test_generate_reads_sec_only_for_triggered_with_contact_and_provenance(monkeypatch):
    monkeypatch.setattr(stage4.time, "sleep", lambda *_: None)
    called = []
    def fetch(url, *, user_agent):
        called.append(url)
        assert user_agent == "Example Research research@example.com"
        if url == stage4.TICKERS_URL:
            return {"0": {"ticker": "ABC", "cik_str": 123, "title": "ABC CO"}}
        if "companyfacts" in url:
            return financial_facts()
        if "/submissions/" in url:
            return {"filings": {"recent": {"form": ["4", "4/A", "10-Q", "4"],
                                           "filingDate": ["2026-10-12", "2026-08-14",
                                                          "2026-10-22", "2026-01-08"]}}}
        raise ValueError(url)
    out = stage4.generate(latest(("ABC", "TRIGGERED"), ("XYZ", "WATCH")),
                          user_agent="Example Research research@example.com",
                          fetch=fetch, today=date(2026, 10, 25))
    assert out["source_status"] == "ok_with_possible_missing_issuer_data"
    assert out["triggered_count"] == 1
    assert len(called) == 3
    assert list(out["records"]) == ["ABC"]
    row = out["records"]["ABC"]
    assert row["revenue_fy"]["value"] == 250_000_000
    assert row["form4"]["recent_count"] == 2
    assert row["form4"]["filing_only_not_purchase_confirmation"] is True
    assert row["insider_purchase_status"] == "UNVERIFIED"
    assert row["institutional_buying_status"] == "UNVERIFIED"
    assert out["insider_buying_verified"] is False
    assert out["institutional_buying_verified"] is False
    assert "research@example.com" not in str(out)


def test_no_triggers_or_missing_sec_identity_never_requests(monkeypatch):
    def no_fetch(*_args, **_kwargs):
        raise AssertionError("Should not call SEC")
    no_signals = stage4.generate(latest(("ABC", "WATCH")), user_agent="", fetch=no_fetch)
    assert no_signals["source_status"] == "no_confirmed_triggers"
    assert no_signals["records"] == {}
    not_configured = stage4.generate(latest(("ABC", "TRIGGERED")), user_agent="",
                                     fetch=no_fetch)
    assert not_configured["source_status"] == "not_configured"
    assert not_configured["records"]["ABC"]["status"] == "not_configured"


def test_a_form4_is_not_automatically_an_insider_purchase():
    out = stage4.recent_form4_summary({
        "filings": {"recent": {"form": ["4", "4"], "filingDate": ["2026-10-11", "2026-02-01"]}}
    }, today=date(2026, 10, 25))
    assert out["recent_count"] == 1
    assert out["filing_only_not_purchase_confirmation"] is True


def test_ticker_lookup_and_cap_fail_closed():
    mapping = stage4.ticker_cik_map({
        "0": {"ticker": "GOOD", "cik_str": 123},
        "1": {"ticker": "X/../", "cik_str": 456},
        "2": {"ticker": "BAD", "cik_str": "-1"}})
    assert mapping == {"GOOD": 123}
    with pytest.raises(ValueError, match="Too many"):
        stage4.generate(latest(("GOOD", "TRIGGERED"), ("TEST", "TRIGGERED")),
                        user_agent="", cap=1)
    with pytest.raises(ValueError, match="successful"):
        stage4.generate({"metadata": {"phase": "running"}, "state": {"3": []}},
                        user_agent="")


def test_sec_network_requires_explicit_identifiable_user_agent():
    with pytest.raises(ValueError, match="SEC_USER_AGENT"):
        stage4.sec_get_json(stage4.TICKERS_URL, user_agent="")
    with pytest.raises(ValueError, match="Unsupported"):
        stage4.sec_get_json("https://not-sec.example.org/x",
                            user_agent="Example Research research@example.com")
