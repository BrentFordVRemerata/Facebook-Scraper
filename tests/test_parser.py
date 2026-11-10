"""
Unit tests for src/parser.py
"""

import unittest
from src.parser import (
    normalize_whitespace,
    extract_text_blocks,
    is_ignorable_block,
    generate_content_hash,
    generate_post_id,
    extract_title_from_block,
    build_post_record,
    parse_posts_from_text,
)


class TestParser(unittest.TestCase):
    def test_normalize_whitespace(self):
        raw = "Line 1\r\nLine 2\rLine 3  \n\n\n\nLine 4"
        norm = normalize_whitespace(raw)
        self.assertIn("Line 1\nLine 2\nLine 3", norm)
        self.assertNotIn("\r", norm)
        self.assertEqual(normalize_whitespace(""), "")
        self.assertEqual(normalize_whitespace(None), "")

    def test_extract_text_blocks_flushes_last_block(self):
        """Verify trailing block at the end of text is not dropped (fixing historical bug)."""
        raw_text = (
            "This is line number one of announcement block one.\n"
            "This is line number two of announcement block one.\n"
            "This is line number three of announcement block one.\n"
            "\n"
            "This is line number one of trailing announcement block.\n"
            "This is line number two of trailing announcement block.\n"
            "This is line number three of trailing announcement block."
        )
        blocks = extract_text_blocks(raw_text, min_line_len=10, min_block_len=50)
        self.assertEqual(len(blocks), 2, "Expected both blocks, including trailing block")
        self.assertIn("trailing announcement block", blocks[1])

    def test_extract_text_blocks_filters_short_lines(self):
        raw_text = (
            "Short\n"
            "Ok\n"
            "This is a long enough line for testing block collection.\n"
            "Another valid long line that belongs to this test block.\n"
            "X\n"
        )
        blocks = extract_text_blocks(raw_text, min_line_len=10, min_block_len=40)
        self.assertEqual(len(blocks), 1)
        self.assertNotIn("Short", blocks[0])
        self.assertNotIn("Ok", blocks[0])

    def test_is_ignorable_block(self):
        self.assertTrue(is_ignorable_block("Like\nComment\nShare"))
        self.assertTrue(is_ignorable_block("Log In to see more"))
        self.assertTrue(is_ignorable_block("Number of unread notifications\n14"))
        self.assertTrue(is_ignorable_block("Privacy · Terms · Advertising"))
        self.assertTrue(is_ignorable_block(""))
        
        valid_announcement = (
            "ADVISORY ON ENROLLMENT SCHEDULE\n"
            "Quezon City University announces that enrollment for the 2nd Semester "
            "Academic Year 2025-2026 will start on February 15, 2026."
        )
        self.assertFalse(is_ignorable_block(valid_announcement))

    def test_hash_collision_prevention_on_identical_headers(self):
        """
        Verify that posts with identical headers (e.g. university letterheads)
        do NOT produce colliding hashes when hashed over the full body text.
        """
        header = (
            "QUEZON CITY UNIVERSITY\n"
            "San Bartolome, Novaliches, Quezon City\n"
            "OFFICE OF THE REGISTRAR\n"
            "OFFICIAL ADVISORY\n"
        )
        post_a = header + "All BSIT students must submit clearance documents by Friday."
        post_b = header + "Graduation application deadline has been extended to next Monday."

        # Verify their first 100 characters are identical
        self.assertEqual(post_a[:100], post_b[:100])

        # Verify our SHA-256 full text hash differentiates them
        hash_a = generate_content_hash(post_a)
        hash_b = generate_content_hash(post_b)
        self.assertNotEqual(hash_a, hash_b)

        # Verify post IDs are also distinct
        id_a = generate_post_id("qcu1994", hash_a)
        id_b = generate_post_id("qcu1994", hash_b)
        self.assertNotEqual(id_a, id_b)

    def test_extract_title_from_block(self):
        block = "Short Title\nSecond line with additional detail."
        self.assertEqual(extract_title_from_block(block), "Short Title")

        long_line = "A" * 120 + "\nSecond line"
        title = extract_title_from_block(long_line, max_length=50)
        self.assertTrue(title.endswith("..."))
        self.assertLessEqual(len(title), 53)

    def test_build_post_record_schema(self):
        block = (
            "MIDTERM EXAMINATION GUIDELINES\n"
            "Please be informed that midterm examinations will commence next week.\n"
            "Students are advised to secure their examination permits."
        )
        record = build_post_record("qcu_main", "QCU Main Page", block)

        self.assertIn("post_id", record)
        self.assertEqual(record["source_id"], "qcu_main")
        self.assertEqual(record["source_name"], "QCU Main Page")
        self.assertEqual(record["title"], "MIDTERM EXAMINATION GUIDELINES")
        self.assertEqual(record["text"], block)
        self.assertEqual(record["body"], block)
        self.assertIn("scraped_at", record)
        self.assertIn("content_hash", record)
        self.assertTrue(record["post_id"].startswith("qcu_main_"))

    def test_parse_posts_from_text_deduplication_and_limit(self):
        announcement_1 = (
            "ANNOUNCEMENT 1: CLASS SUSPENSION\n"
            "Due to inclement weather, all classes are suspended today.\n"
            "Please stay safe and monitor official announcements."
        )
        announcement_2 = (
            "ANNOUNCEMENT 2: SCHOLARSHIP APPLICATIONS\n"
            "Applications for the local government tertiary scholarship are now open.\n"
            "Visit the student affairs office for requirements."
        )
        raw_stream = (
            f"Like\nComment\nShare\n\n"
            f"{announcement_1}\n\n"
            f"{announcement_1}\n\n"  # Duplicate
            f"{announcement_2}\n\n"
            f"Log In\nPrivacy\n"
        )

        posts = parse_posts_from_text(raw_stream, "qcu", "QCU", max_posts=10, min_block_len=40)
        self.assertEqual(len(posts), 2, "Expected duplicates to be pruned")

        # Test limit
        posts_limited = parse_posts_from_text(raw_stream, "qcu", "QCU", max_posts=1, min_block_len=40)
        self.assertEqual(len(posts_limited), 1)

    def test_legacy_post_id_generation(self):
        from src.parser import generate_legacy_post_id
        block = "REGISTRAR ADVISORY: Graduation requirements must be submitted by Monday."
        legacy_id = generate_legacy_post_id("qcu1994", block)
        self.assertTrue(legacy_id.startswith("qcu1994_"))
        # MD5 digest prefix length is 8 hex chars
        self.assertEqual(len(legacy_id.split("_")[1]), 8)

        # Verify legacy_post_id is present in build_post_record
        record = build_post_record("qcu1994", "QCU Main", block)
        self.assertIn("legacy_post_id", record)
        self.assertEqual(record["legacy_post_id"], legacy_id)


if __name__ == "__main__":
    unittest.main()
