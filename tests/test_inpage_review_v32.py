"""Regression checks: public page stays read-only except authenticated Stage 2 approval."""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/"site/index.html").read_text(encoding="utf-8")


def test_public_view_has_review_entry_and_does_not_offer_legacy_editing():
    assert 'id="reviewAuthBtn"' in HTML
    assert 'data-act="review"' in HTML
    assert '#addBtn,#importBtn,#scanBtn,button[data-act]:not([data-act="review"])' in HTML
    assert "if(CLOUD_MODE){if(btn.dataset.act==='review'" in HTML
    assert "openReviewForm(candidate)" in HTML
    assert 'id="count1"' in HTML and 'id="count2"' in HTML and 'id="count3"' in HTML


def test_credentials_stay_in_memory_and_github_verifies_dispatch():
    script=re.search(r"<script>(.*?)</script>",HTML,re.DOTALL).group(1)
    assert "let reviewToken=null, reviewIdentity=null" in script
    assert "reviewToken=token" in script
    assert "githubRequest('/user'" in script
    assert "actions/workflows/'+REVIEW_WORKFLOW+'/dispatches" in script
    assert "method:'POST'" in script
    assert "confirmed_chart_review:String(confirmed)" in script
    assert 'https://api.github.com' in script
    assert "localStorage.setItem('reviewToken'" not in script
    assert 'sessionStorage.setItem(' not in script
    assert 'fetch(\'/api/state\'' not in script.split("function openReviewForm(row)",1)[1].split("byId('reviewAuthBtn')",1)[0]
    assert "reviewToken=null;reviewIdentity=null" in script
    assert "READY_CANDIDATE" in script


def test_server_side_review_workflow_remains_permissioned():
    workflow=(ROOT/".github/workflows/review-stage2.yml").read_text(encoding="utf-8")
    script=(ROOT/"review_setup.py").read_text(encoding="utf-8")
    assert "workflow_dispatch:" in workflow
    assert "GITHUB_ACTOR" in script
    assert 'if decision == "READY" and not confirmed:' in script
    assert 'if row.get("readiness_recommendation") != "READY_CANDIDATE":' in script
    assert "TRIGGERED" not in script  # review never simulates a filled trade
