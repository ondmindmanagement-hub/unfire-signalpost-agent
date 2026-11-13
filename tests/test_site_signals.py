"""Isolation tests for external signals; stdlib only, no network requests."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from norway_company_agent.site_signals import site_observations


def fixture(name="NORDIC DOOR AS"):
    return {
        "organisation_number": "923609016",
        "name": name,
        "evidence": {
            "website": {
                "status": "available",
                "source_url": "https://nordic.example/",
                "retrieved_at": "2026-11-13T12:00:00Z",
                "value": {
                    "final_url": "https://nordic.example/",
                    "identity_assessment": {"publishable": True},
                    "pages": [
                        {"url": "https://nordic.example/news/new-factory",
                         "title": "NORDIC DOOR AS opens a new factory on 2026-11-12",
                         "main_text_excerpt": "NORDIC DOOR AS announced a new facility on 2026-11-12.",
                         "content_sha256": "a" * 64},
                        {"url": "https://nordic.example/careers/senior-engineer",
                         "title": "Senior Engineer — NORDIC DOOR AS",
                         "main_text_excerpt": "NORDIC DOOR AS seeks a Senior Engineer. Apply now to join our team.",
                         "content_sha256": "b" * 64},
                    ],
                },
            },
        },
    }


class VerifiedSiteSignalsTests(unittest.TestCase):
    def test_two_supported_company_owned_signals(self):
        rows = site_observations(fixture())
        self.assertEqual([r["signal_type"] for r in rows], ["public_post", "job_posting"])
        self.assertEqual(rows[0]["published_at"], "2026-11-12")
        self.assertIn("open_cta", rows[1]["posting_status"])
        self.assertEqual(len({r["id"] for r in rows}), 2)

    def test_wrong_legal_entity_abstains(self):
        profile = fixture(name="NORDIC DOOR BERGEN AS")
        self.assertEqual(site_observations(profile), [])

    def test_archive_page_without_date_abstains(self):
        profile = fixture()
        page = profile["evidence"]["website"]["value"]["pages"][0]
        page["title"] = "NORDIC DOOR AS - Latest news"
        page["main_text_excerpt"] = "NORDIC DOOR AS latest news."
        profile["evidence"]["website"]["value"]["pages"] = [page]
        self.assertEqual(site_observations(profile), [])

    def test_open_job_requires_explicit_apply_action(self):
        profile = fixture()
        page = profile["evidence"]["website"]["value"]["pages"][1]
        page["main_text_excerpt"] = "NORDIC DOOR AS has an engineering team."
        profile["evidence"]["website"]["value"]["pages"] = [page]
        self.assertEqual(site_observations(profile), [])

    def test_closed_job_abstains(self):
        profile = fixture()
        page = profile["evidence"]["website"]["value"]["pages"][1]
        page["main_text_excerpt"] += " Applications closed."
        profile["evidence"]["website"]["value"]["pages"] = [page]
        self.assertEqual(site_observations(profile), [])

    def test_cross_domain_and_unverified_site_abstain(self):
        profile = fixture()
        profile["evidence"]["website"]["value"]["pages"][0]["url"] = "https://wrong.example/news/article"
        profile["evidence"]["website"]["value"]["pages"][1]["url"] = "https://wrong.example/jobs/position"
        self.assertEqual(site_observations(profile), [])
        profile["evidence"]["website"]["value"]["identity_assessment"]["publishable"] = False
        self.assertEqual(site_observations(profile), [])


if __name__ == "__main__":
    unittest.main()
