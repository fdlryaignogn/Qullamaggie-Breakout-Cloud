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


def test_pat_stays_in_memory_and_github_app_nonce_is_not_a_credential():
    script=re.search(r"<script>(.*?)</script>",HTML,re.DOTALL).group(1)
    assert "let reviewToken=null, reviewIdentity=null" in script
    assert "reviewToken=token" in script
    assert "githubRequest('/user'" in script
    assert "actions/workflows/'+REVIEW_WORKFLOW+'/dispatches" in script
    assert "method:'POST'" in script
    assert "confirmed_chart_review:String(confirmed)" in script
    assert 'https://api.github.com' in script
    assert "localStorage.setItem('reviewToken'" not in script
    # OAuth stores a random anti-CSRF nonce, not the raw GitHub credential.
    assert 'sessionStorage.setItem(OAUTH_PENDING_STATE_KEY,nonce)' in script
    assert "sessionStorage.setItem('reviewToken'" not in script
    assert "localStorage.setItem(OAUTH_SESSION_STORAGE_KEY" in script
    assert "oauthRequest('/reviews/dispatch','POST'" in script
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


def test_review_publication_updates_github_pages_without_waiting_for_new_scan():
    review=(ROOT/".github/workflows/review-stage2.yml").read_text(encoding="utf-8")
    site_workflow=(ROOT/".github/workflows/publish-site.yml").read_text(encoding="utf-8")
    assert "git push" in review
    assert "uses: actions/configure-pages@v5" in review
    assert "uses: actions/upload-pages-artifact@v4" in review
    assert "uses: actions/deploy-pages@v4" in review
    assert "path: site" in review
    assert "pages: write" in review
    assert "id-token: write" in review
    assert "name: github-pages" in review
    assert "push:" in site_workflow
    # GITHUB_TOKEN pushes cannot trigger site_workflow's ordinary push job.


def test_review_submit_reports_pending_and_published_stage3_watch_to_user():
    assert "GitHub 已接受 " in HTML
    assert "已提交，正在等候 GitHub 發布" in HTML
    assert "已加入第三輪 WATCH" in HTML
    assert "addedToWatch=decision==='READY'" in HTML
    assert "toast(addedToWatch?" in HTML
    assert "githubRequest('/repos/'+REVIEW_REPO" in HTML
