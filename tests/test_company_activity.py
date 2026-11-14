from copy import deepcopy
from datetime import datetime, timezone
import pytest
from norway_company_agent.company_activity import extract_activity

NOW = datetime(2026, 11, 14, tzinfo=timezone.utc)

def profile(kind="NewsArticle"):
    item = {"@type": kind, "headline": "New factory", "title": "Engineer", "datePublished": "2026-11-10", "datePosted": "2026-11-10", "validThrough": "2026-12-01", "hiringOrganization": {"name": "Example Manufacturing AS"}}
    return {"name": "Example Manufacturing AS", "organisation_number": "123456789", "evidence": {"website": {"status": "available", "retrieved_at": "2026-11-14T00:00:00Z", "value": {"final_url": "https://example.no/", "identity_assessment": {"publishable": True}, "pages": [{"url": "https://example.no/news/factory", "title": "Example Manufacturing AS", "main_text_excerpt": "Company-owned announcement", "content_sha256": "a"*64, "structured_data": {"json-ld": [item]}}]}}}}

def page(p):
    return p["evidence"]["website"]["value"]["pages"][0]

def item(p):
    return page(p)["structured_data"]["json-ld"][0]

def extract(p, field="company_news"):
    return extract_activity(p, now=NOW)[field]["value"]

def test_dated_exact_news_and_open_job():
    assert len(extract(profile())) == 1
    assert len(extract(profile("JobPosting"), "company_jobs")) == 1

@pytest.mark.parametrize("mutation", ["wrong_page_entity", "foreign_host", "invalid_hash", "future", "undated", "unverified_site", "archive_only", "invalid_type"])
def test_reject_unsupported_news(mutation):
    p = profile()
    if mutation == "wrong_page_entity": page(p)["title"] = "Another Company AS"
    if mutation == "foreign_host": page(p)["url"] = "https://attacker.no/news"
    if mutation == "invalid_hash": page(p)["content_sha256"] = "z"*64
    if mutation == "future": item(p)["datePublished"] = "2027-01-01"
    if mutation == "undated": item(p).pop("datePublished"); item(p).pop("datePosted")
    if mutation == "unverified_site": p["evidence"]["website"]["value"]["identity_assessment"]["publishable"] = False
    if mutation == "archive_only": page(p)["structured_data"] = {}
    if mutation == "invalid_type": item(p)["@type"] = {"bad": "type"}
    assert extract(p) == []

@pytest.mark.parametrize("mutation", ["expired", "missing_expiry", "wrong_employer", "missing_employer", "future_post"])
def test_jobs_require_current_exact_employer(mutation):
    p = profile("JobPosting")
    if mutation == "expired": item(p)["validThrough"] = "2026-01-01"
    if mutation == "missing_expiry": item(p).pop("validThrough")
    if mutation == "wrong_employer": item(p)["hiringOrganization"]["name"] = "Example Manufacturing AS Other"
    if mutation == "missing_employer": item(p).pop("hiringOrganization")
    if mutation == "future_post": item(p)["datePosted"] = "2027-01-01"
    assert extract(p, "company_jobs") == []

def test_org_number_boundaries_and_deduplication():
    p = profile(); page(p)["title"] = "Org 123 456 789"
    p["evidence"]["website"]["value"]["pages"] *= 2
    assert len(extract(p)) == 1
    page(p)["title"] = "Number 91234567890"
    assert extract(p) == []
