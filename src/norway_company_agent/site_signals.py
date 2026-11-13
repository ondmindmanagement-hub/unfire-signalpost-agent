"""Conservative company-owned news and open-job signals from already fetched pages.

No additional requests: source pages must have passed the registry-linked website
identity gate, and each individual page must name the exact legal entity or number.
Abstain rather than promoting generic news archives or career landing pages.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import date, datetime, timezone
from urllib.parse import urlparse


NEWS_ARTICLE = re.compile(r"/(?:news|press|aktuelt|nyheter|artikler|blog)/[^/?#]+", re.I)
JOB_DETAIL = re.compile(r"/(?:jobs?|careers?|karriere|stillinger|ledige-stillinger|vacancies)/[^/?#]+", re.I)
APPLY_CTA = re.compile(r"\b(?:apply now|apply for (?:this|the) (?:job|position)|send (?:your )?application|søk på stillingen|søk stillingen|send søknad|sok pa stillingen)\b", re.I)
CLOSED = re.compile(r"\b(?:applications? closed|position filled|no longer accepting|søknadsfristen er utløpt|stillingen er besatt)\b", re.I)
ISO_DATE = re.compile(r"(?<!\d)(20\d{2})[-/.](0?[1-9]|1[0-2])[-/.]([0-2]?\d|3[01])(?!\d)")
EU_DATE = re.compile(r"(?<!\d)([0-2]?\d|3[01])[./](0?[1-9]|1[0-2])[./](20\d{2})(?!\d)")


def _normal(text: str) -> str:
    text = str(text or "").casefold().replace("æ", "ae").replace("ø", "o").replace("å", "a")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _page_identity(profile: dict, page: dict) -> str | None:
    # Inspect the article headline and its opening, not a global site footer.
    opening = str(page.get("title") or "") + " " + str(page.get("main_text_excerpt") or "")[:1000]
    org = "".join(re.findall(r"\d", str(profile.get("organisation_number") or "")))
    if len(org) == 9 and re.search(r"(?<!\d)" + r"\s*".join(re.escape(c) for c in org) + r"(?!\d)", opening):
        return "organisation_number_in_article"
    legal_name = _normal(profile.get("name") or "")
    if len(legal_name) >= 4 and (" " + legal_name + " ") in (" " + _normal(opening) + " "):
        return "full_legal_name_in_article"
    return None


def _date_in_article(page: dict) -> str | None:
    # Reject undated press archive links. Require a visible or URL-carried date.
    source = str(page.get("title") or "") + " " + str(page.get("main_text_excerpt") or "")[:500]
    source += " " + urlparse(str(page.get("url") or "")).path
    today = datetime.now(timezone.utc).date()
    for pattern, order in ((ISO_DATE, "ymd"), (EU_DATE, "dmy")):
        for match in pattern.finditer(source):
            parts = [int(v) for v in match.groups()]
            year, month, day = parts if order == "ymd" else (parts[2], parts[1], parts[0])
            try:
                value = date(year, month, day)
                if date(2000, 1, 1) <= value <= today:
                    return value.isoformat()
            except ValueError:
                continue
    return None


def site_observations(profile: dict) -> list[dict]:
    website = (profile.get("evidence") or {}).get("website") or {}
    value = website.get("value") or {}
    if website.get("status") != "available" or not (value.get("identity_assessment") or {}).get("publishable"):
        return []
    base = urlparse(str(value.get("final_url") or website.get("source_url") or ""))
    if base.scheme not in {"http", "https"} or not base.hostname:
        return []
    output = []
    seen = set()
    for page in value.get("pages") or []:
        url = str(page.get("url") or "")
        parsed = urlparse(url)
        digest = str(page.get("content_sha256") or "")
        if parsed.scheme not in {"http", "https"} or parsed.hostname != base.hostname:
            continue
        if len(digest) != 64 or not re.fullmatch(r"[a-fA-F0-9]{64}", digest):
            continue
        proof = _page_identity(profile, page)
        if not proof:
            continue
        if parsed.path.strip("/").split("/")[-1].casefold() in {"archive", "category", "categories", "tag", "tags", "author", "page", "all", "latest"}:
            continue
        text = str(page.get("main_text_excerpt") or "")
        kind = None
        extra = {}
        published = _date_in_article(page) if NEWS_ARTICLE.search(parsed.path) else None
        if published:
            kind = "public_post"
            extra["published_at"] = published
        elif JOB_DETAIL.search(parsed.path) and APPLY_CTA.search(text) and not CLOSED.search(text):
            kind = "job_posting"
            extra["posting_status"] = "open_cta_observed_not_independently_confirmed"
        if not kind or kind in seen:
            continue
        seen.add(kind)
        output.append({
            "id": "company-site-" + hashlib.sha256(f"{profile['organisation_number']}|{kind}|{url}".encode()).hexdigest()[:24],
            "organisation_number": str(profile["organisation_number"]),
            "platform": "company_site",
            "signal_type": kind,
            "source_url": url,
            "retrieved_at": website.get("retrieved_at"),
            "content_sha256": digest.lower(),
            "exact_entity": True,
            "identity_proof": [{"type": proof, "registry_website": value.get("final_url")}],
            "acquisition_mode": "permitted_public_page",
            "rights_status": "approved",
            "source_class": "company_site",
            "evidence_span": (str(page.get("title") or "") + " — " + text[:220]).strip(" —")[:500],
            "strategy": "verified_company_site_signals_v1",
            **extra,
        })
        if len(seen) == 2:
            break
    return output
