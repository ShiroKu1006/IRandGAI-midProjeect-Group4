
import unittest
from unittest.mock import patch
import crawler


class FakeResponse:
    """模擬 requests.get() 回傳的 Response"""

    def __init__(self, status_code, text="", headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}

    def close(self):
        pass


class TestCrawlerRetry(unittest.TestCase):

    @patch("crawler.wait_for_host")
    @patch("crawler.time.sleep")
    @patch("crawler.is_allowed_by_robots", return_value=True)
    @patch("crawler.is_allowed_url", return_value=True)
    @patch("crawler.normalize_url")
    @patch("crawler.requests.get")
    def test_retry_until_success(
        self,
        mock_get,
        mock_normalize,
        mock_allowed,
        mock_robots,
        mock_sleep,
        mock_wait
    ):
        url = "https://www.postgresql.org/docs/current/sql-select.html"

        # 模擬網址正規化
        mock_normalize.return_value = url

        # 模擬伺服器回應：
        # 第一次 503、第二次 503、第三次 200
        mock_get.side_effect = [
            FakeResponse(503),
            FakeResponse(503),
            FakeResponse(
                200,
                text="<html><body>SELECT</body></html>",
                headers={"Content-Type": "text/html"}
            )
        ]

        with self.assertLogs("crawler", level="INFO") as logs:
            result = crawler.fetch_page(url, None)

        # 確認最後成功取得 HTML
        self.assertIsNotNone(result)
        self.assertEqual(result["url"], url)
        self.assertIn("SELECT", result["html"])

        # 確認總共請求三次
        self.assertEqual(mock_get.call_count, 3)

        # 確認兩次重試紀錄
        retry_logs = [
            log for log in logs.output
            if "[RETRY]" in log
        ]

        self.assertEqual(len(retry_logs), 2)

        # 確認成功紀錄
        success_logs = [
            log for log in logs.output
            if "[SUCCESS]" in log
        ]

        self.assertEqual(len(success_logs), 1)

        print("\nTest result:")
        print("HTTP attempts:", mock_get.call_count)
        print("Retry count:", len(retry_logs))
        print("Final result:", result["url"])

    def test_retry_delay(self):
        """測試沒有 Retry-After 時的指數退避"""

        self.assertEqual(
            crawler.get_retry_delay(
                FakeResponse(503), 1
            ),
            2
        )

        self.assertEqual(
            crawler.get_retry_delay(
                FakeResponse(503), 2
            ),
            4
        )

    def test_request_budget(self):
        """測試全域請求次數上限"""

        budget = crawler.RequestBudget(max_attempts=3)

        self.assertTrue(budget.consume())
        self.assertTrue(budget.consume())
        self.assertTrue(budget.consume())

        # 第四次請求應該被拒絕
        self.assertFalse(budget.consume())

        self.assertEqual(budget.attempts, 3)
        self.assertEqual(budget.remaining(), 0)

if __name__ == "__main__":
    unittest.main(verbosity=2)
