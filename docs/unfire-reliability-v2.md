# Unfire Signalpost — v2 reliability revision (10 October 2026)

**Prior frozen entry:** `e574b1148c3624987f6a204a9c4c063d0e756928`, emailed to submit@builderr.ai on 6 October.

## Change and reason

The original runner could terminate the complete official batch if a single company's
asynchronous enrichment task raised an uncaught exception. Because Builderr requires
exactly one terminal envelope for each input company, this creates an unnecessary
risk of a zero-scored batch.

This revision handles each failed enrichment task separately. The registry-anchored
company profile is preserved; any enrichment fields that could not be fetched are
marked `source_error`. Failed organisation numbers and exception types are recorded
in the machine-readable report. Request/byte totals are labeled partial when
some workers crash, instead of claiming a complete accounting.

The change does not bypass source-rights rules, fabricate missing evidence, or
accept unverified third-party social profiles. Scoring and external research coverage
may remain low; this is principally an execution-reliability hardening change.

## Tests and representative output

- **106 Python unit tests passed**, plus 5 subtests (2 newly introduced
  tests demonstrate worker failure recovery and preservation of already valid evidence).
- A 100-company **checkpoint/resume check** produced 100 terminal envelopes,
  100 distinct organisation numbers, zero silent drops and validated terminal
  statuses. All 100 profiles were reused from the previous documented local
  smoke test, **not freshly downloaded**.
- The retained pre-revision live smoke result from Oct 6 had 100/100 emitted,
  536 public source requests; this is not newly claimed live testing.
- No external LLM API, paid data provider or private credentials were used.

## Run

Standard evaluator command unchanged:

```bash
uv sync
uv run python scripts/run_competition_batch.py \
  --organisations <builderr_batch.jsonl> \
  --bulk brreg-enheter.csv \
  --profiles-output out/profiles.jsonl \
  --output out/envelopes.jsonl \
  --report out/run-report.json \
  --run-id <run_id> \
  --expected-count <count>
```

For a local 100-company checkpoint validation, include `--resume` and
use existing 100-company `out/smoke-profiles.jsonl` as the checkpoint,
or start without `--resume` for a fresh live run.

## Compliance and limitations

- Public official registry and website sources are used subject to each site's terms,
  robots policy and rate limits. Unsafe/private scraping is not introduced.
- Development used AI coding assistance; assertions and test results were executed
  on the author's Mac. No automatic model inference is used at runtime.
- A failure result is not a verified fact about the company. It is explicitly an
  execution/source-error outcome.
- Unit tests exercise intentionally failing workers; the checkpoint resume does
  not exercise new network requests.
- Source licence and existing dependencies are unchanged.
