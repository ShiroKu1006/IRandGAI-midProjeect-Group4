import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import crawler
from indexed_app import create_indexed_app
from search import SearchIndex


class DemoSnapshotTests(unittest.TestCase):
    def test_version_scope_and_normalization(self):
        base = "https://www.postgresql.org/docs/18/index.html"
        self.assertEqual(
            crawler.extract_links(
                '<a href="sql-select.html?q=1#syntax">yes</a>'
                '<a href="/docs/17/sql-select.html">no</a>'
                '<a href="/docs/current/sql-select.html">no</a>'
                '<a href="https://www.postgresql.org/docs/18/%2e%2e/17/index.html">no</a>',
                base,
            ),
            {"https://www.postgresql.org/docs/18/sql-select.html?q=1"},
        )

    def test_existing_snapshot_rejected_before_network(self):
        with patch("crawler.load_robots_parser") as robots:
            with self.assertRaises(FileExistsError):
                crawler.run_crawler([], db_path=Path(__file__))
            robots.assert_not_called()

    def test_redirect_to_another_version_is_rejected(self):
        response = Mock(status_code=302, headers={"Location": "/docs/17/index.html"})
        with (
            patch("crawler.requests.get", return_value=response) as request,
            patch("crawler.wait_for_host"),
            patch("crawler.is_allowed_by_robots", return_value=True),
        ):
            self.assertIsNone(crawler.fetch_page(crawler.SEED_URLS[0], None))
        self.assertEqual(request.call_count, 1)

    def test_duplicate_body_is_skipped_but_its_links_are_followed(self):
        first, second, third = crawler.SEED_URLS[:3]
        pages = {
            first: "first body",
            second: f' first \n body <a href="{third}"></a>',
            third: "different body",
        }

        def fetch(url, *args, **kwargs):
            html = f'<div id="docContent"><div class="sect1">{pages[url]}</div></div>'
            return {"url": url, "html": html}

        with (
            patch.object(Path, "touch"),
            patch("crawler.init_database"),
            patch("crawler.load_robots_parser"),
            patch("crawler.fetch_page", side_effect=fetch),
            patch("crawler.save_document") as save,
        ):
            summary = crawler.run_crawler([first, second], db_path=Path("unused.db"))

        self.assertEqual([call.args[0]["url"] for call in save.call_args_list], [first, third])
        self.assertEqual(summary["documents"], 2)
        self.assertEqual(summary["duplicate_bodies"], 1)

    def test_search_snippet_limits_words(self):
        documents = {
            1: {"title": "long", "url": "https://example.com/long",
                "text": "  \n".join(["select"] * 90)},
            2: {"title": "short", "url": "https://example.com/short",
                "text": "select \n  rows"},
        }
        index = SearchIndex(documents, {"select": {1: 1, 2: 1}},
                            {"select": 1}, {1: 1, 2: 1}, str.split)
        _, hits = index.search("select")
        self.assertEqual(hits[0]["snippet"], " ".join(["select"] * 75))
        self.assertEqual(hits[1]["snippet"], "select rows")

    def test_factory_loads_configured_index(self):
        with patch.dict("os.environ", {"SEARCH_INDEX_PATH": "missing-demo-index.json"}):
            with self.assertRaisesRegex(FileNotFoundError, "missing-demo-index"):
                create_indexed_app()
