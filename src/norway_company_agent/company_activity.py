"""Conservative company-owned dated news and open jobs; no extra requests."""
from __future__ import annotations
import re
from datetime import datetime, timezone
from urllib.parse import urlparse
from .evidence import evidence


def _walk(node):
    if isinstance(node, dict):
        yield node
        for child in node.values():
            yield from _walk(child)
    elif isinstance(node, list):
        for child in node:
            yield from _walk(child)


def _date(value):
    if not isinstance(value, str) or not re.match(r"^\d{4}-\d{2}-\d{2}(?:$|T)", value):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    except ValueError:
        return None


def _name(value):
    return " ".join(re.findall(r"\w+", str(value or "").casefold()))


def _matches(profile, text):
    org = str(profile.get("organisation_number") or "")
    # Bounded digits, permitting the official 3-3-3 spacing, never concatenate
    # unrelated dates or telephone numbers into a false organisation number.
    org_match = bool(re.fullmatch(r"\d{9}", org) and re.search(
        r"(?<!\d)" + r"[ .]?".join(org) + r"(?!\d)", text))
    name = _name(profile.get("name"))
    return org_match or bool(len(name) >= 5 and re.search(
        r"(?<!\w)" + re.escape(name) + r"(?!\w)", _name(text)))


def extract_activity(profile, *, now=None):
    now = now or datetime.now(timezone.utc)
    site = profile.get("evidence", {}).get("website", {})
    value = site.get("value") or {}
    homepage = str(value.get("final_url") or site.get("source_url") or "")
    host = urlparse(homepage).netloc.casefold()
    accepted = {"company_news": [], "company_jobs": []}
    if site.get("status") == "available" and (value.get("identity_assessment") or {}).get("publishable"):
        for page in value.get("pages") or []:
            url = str(page.get("url") or "")
            digest = str(page.get("content_sha256") or "")
            if (urlparse(url).scheme not in {"http", "https"} or
                urlparse(url).netloc.casefold() != host or
                not re.fullmatch(r"[a-f0-9]{64}", digest)):
                continue
            text = " ".join(str(page.get(k) or "") for k in ("title", "main_text_excerpt", "identity_text_excerpt"))
            if not _matches(profile, text):
                continue
            for item in _walk(page.get("structured_data") or {}):
                kinds = item.get("@type")
                kinds = kinds if isinstance(kinds, list) else [kinds]
                published = _date(item.get("datePosted") if "JobPosting" in kinds else item.get("datePublished"))
                if not published or published > now:
                    continue
                title = str(item.get("headline") or item.get("title") or "").strip()
                if not title or len(title) > 500:
                    continue
                record = {"title": title, "source_url": url, "published_at": published.isoformat(),
                          "content_sha256": digest, "retrieved_at": site.get("retrieved_at"),
                          "exact_entity": True, "evidence_span": text[:1200],
                          "claim_boundary": "Company-owned structured claim; not independent verification."}
                if any(isinstance(k, str) and k in {"NewsArticle", "Article", "BlogPosting"} for k in kinds):
                    accepted["company_news"].append(record)
                elif "JobPosting" in kinds:
                    employer = item.get("hiringOrganization") or {}
                    expiry = _date(item.get("validThrough"))
                    if not isinstance(employer, dict) or _name(employer.get("name")) != _name(profile.get("name")):
                        continue
                    if not expiry or expiry <= now:
                        continue
                    accepted["company_jobs"].append({**record, "valid_through": expiry.isoformat()})
    result = {}
    for field, rows in accepted.items():
        unique = {(x["source_url"], x["title"], x["published_at"]): x for x in rows}
        result[field] = evidence(field, "available" if unique else "not_found",
            "company_owned_structured_activity", homepage, value=list(unique.values())[:10],
            retrieved_at=site.get("retrieved_at"),
            note="Only same-host, page-level company identity, dated structured items; jobs require matching employer and future expiry. Absence is not proof of no news/jobs.")
    return result
