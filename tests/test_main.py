"""
Unit tests for main.py execution pipeline
"""

import unittest
from unittest.mock import patch, MagicMock
from main import run_pipeline
from src.scraper import ScraperStats


class TestMainPipeline(unittest.TestCase):
    @patch("src.scraper.SELENIUM_AVAILABLE", True)
    @patch("src.scraper.scrape_page")
    @patch("main.initialize_firebase")
    @patch("main.save_posts_batch")
    def test_run_pipeline_passes_posts_to_fetch_and_page_name(
        self,
        mock_save_posts,
        mock_init_fb,
        mock_scrape_page
    ):
        """
        Verify that main.py properly forwards posts_to_fetch and page_name
        to scrape_page() - fixing historical issue where limit was dropped.
        """
        mock_init_fb.return_value = True
        mock_save_posts.return_value = {"saved": 1, "skipped": 0, "errors": 0}
        
        stat = ScraperStats(page_id="test_page", success=True)
        stat.time_total = 1.0
        mock_scrape_page.return_value = ([{"post_id": "test_1", "text": "sample"}], stat)

        sources = [
            {
                "id": "qcu_test",
                "name": "QCU Test Campus",
                "posts_to_fetch": 7,
                "enabled": True,
            }
        ]

        exit_code = run_pipeline(
            sources=sources,
            use_playwright=False,
            headless=True,
            dry_run=False
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(mock_scrape_page.call_count, 1)

        # Inspect kwargs passed to scrape_page
        _, kwargs = mock_scrape_page.call_args
        self.assertEqual(kwargs.get("page_id"), "qcu_test")
        self.assertEqual(kwargs.get("page_name"), "QCU Test Campus")
        self.assertEqual(kwargs.get("max_posts"), 7, "Configured posts_to_fetch must be passed to scrape_page")
        self.assertTrue(kwargs.get("headless"))
        self.assertFalse(kwargs.get("save_debug"), "save_debug should default to False")

    @patch("src.scraper.SELENIUM_AVAILABLE", True)
    @patch("src.scraper.scrape_page")
    @patch("main.initialize_firebase")
    @patch("main.save_posts_batch")
    def test_run_pipeline_dry_run_skips_firebase(
        self,
        mock_save_posts,
        mock_init_fb,
        mock_scrape_page
    ):
        stat = ScraperStats(page_id="test_page", success=True)
        mock_scrape_page.return_value = ([{"post_id": "test_1", "text": "sample"}], stat)

        sources = [{"id": "qcu_test", "name": "QCU", "posts_to_fetch": 3, "enabled": True}]

        exit_code = run_pipeline(
            sources=sources,
            use_playwright=False,
            headless=True,
            dry_run=True
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(mock_init_fb.call_count, 0)
        self.assertEqual(mock_save_posts.call_count, 0)

    @patch("src.scraper.scrape_page")
    def test_run_pipeline_offline_fixture_mode(self, mock_scrape_page):
        """Verify offline mode parses local fixtures without invoking browser scrapers."""
        sources = [{"id": "qcu_test", "name": "QCU Offline", "posts_to_fetch": 5, "enabled": True}]

        exit_code = run_pipeline(
            sources=sources,
            dry_run=True,
            offline=True
        )

        self.assertEqual(exit_code, 0)
        # Browser scraper must NEVER be invoked in offline mode
        self.assertEqual(mock_scrape_page.call_count, 0)

    @patch("src.scraper.scrape_page")
    @patch("main.initialize_firebase")
    @patch("main.save_posts_batch")
    def test_run_pipeline_offline_unconditionally_disables_firebase_and_network(
        self,
        mock_save_posts,
        mock_init_fb,
        mock_scrape_page
    ):
        """
        Regression test: Verify that offline=True unconditionally prevents browser access,
        network requests, and external database writes even when dry_run=False.
        """
        sources = [{"id": "qcu_test", "name": "QCU Offline", "posts_to_fetch": 3, "enabled": True}]

        exit_code = run_pipeline(
            sources=sources,
            offline=True,
            dry_run=False  # Even with dry_run=False, offline mode must not write to Firebase!
        )

        self.assertEqual(exit_code, 0)
        # Neither Firebase connection nor batch persistence should ever be attempted
        self.assertEqual(mock_init_fb.call_count, 0, "Firebase must not be initialized in offline mode")
        self.assertEqual(mock_save_posts.call_count, 0, "Firestore writes must not occur in offline mode")
        self.assertEqual(mock_scrape_page.call_count, 0, "Browser scraper must not run in offline mode")

    def test_run_pipeline_offline_missing_fixture_exits_nonzero(self):
        """Verify that a missing fixture file in offline mode returns a non-zero exit status (code 1)."""
        from pathlib import Path
        sources = [{"id": "qcu_test", "name": "QCU", "posts_to_fetch": 2, "enabled": True}]

        exit_code = run_pipeline(
            sources=sources,
            offline=True,
            fixture_path=Path("/nonexistent/path/fixture.txt")
        )

        self.assertEqual(exit_code, 1, "Missing offline fixture must return non-zero exit code 1")

    @patch("src.scraper.SELENIUM_AVAILABLE", True)
    @patch("src.scraper.scrape_page")
    @patch("main.initialize_firebase", return_value=True)
    @patch("main.save_posts_batch")
    def test_run_pipeline_database_write_error_exits_nonzero(
        self,
        mock_save_posts,
        mock_init_fb,
        mock_scrape_page
    ):
        """Verify that Firestore write errors result in a non-zero exit status (code 3)."""
        stat = ScraperStats(page_id="test_page", success=True)
        mock_scrape_page.return_value = ([{"post_id": "test_1", "text": "sample"}], stat)
        
        # Simulate Firestore reporting 2 write errors
        mock_save_posts.return_value = {"saved": 0, "skipped": 0, "errors": 2}

        sources = [{"id": "qcu_test", "name": "QCU", "posts_to_fetch": 2, "enabled": True}]

        exit_code = run_pipeline(
            sources=sources,
            dry_run=False
        )

        self.assertEqual(exit_code, 3, "Database write errors must return exit code 3")


if __name__ == "__main__":
    unittest.main()
