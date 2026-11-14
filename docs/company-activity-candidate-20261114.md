# Company-owned activity candidate — 14 November 2026

Problem: the evaluator command did not expose dated company news or current job postings, even when its bounded website crawl captured relevant structured evidence.

This candidate preserves JSON-LD in already-fetched pages and adds `company_news` and `company_jobs` evidence to the default evaluator command. No additional HTTP requests are introduced. Identity requires both the existing website gate and the company name or bounded organisation number on the individual page. Jobs additionally require the exact employer name, a nonfuture posting date and a future explicit expiry. Unsupported or missing evidence returns `not_found`, which does not claim the company has no news/jobs.

Validation: 121 tests and 5 subtests passed on Python 3.14.7 (11 pre-existing mf2py deprecation warnings). Fifteen new regression cases cover accepted news/jobs, wrong identity, foreign host, malformed digest, future dates, missing dates, unknown identity, archive-only pages, malformed schema type, expired jobs, missing expiry, wrong/missing employer, bounded organisation numbers and duplicates.

Bounded live smoke: AAS ELEKTRONIKK AS (888567232), registered website www.aelektronikk.no, returned available/exact website evidence after 6 requests and 8,767 bytes. Zero qualifying news/jobs were emitted. This validates fail-closed behavior on that page, NOT improved coverage or challenge qualification.

Limitations: JSON-LD only; current crawl depth and link budget unchanged; postings without explicit future expiry omitted; same-host only; source terms remain the existing crawler policy, not legally certified here. Requires live coverage measurement on development and nonoverlapping validation samples before promotion. Do not replace submitted commit 3801e25a1a65bc6844e8a454c9bfb1cb1cd4138e based only on synthetic tests.
