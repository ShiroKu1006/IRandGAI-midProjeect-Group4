
from urllib.parse import urljoin, urlsplit, urlunsplit
from collections import deque
from bs4 import BeautifulSoup
import requests
from urllib.robotparser import RobotFileParser
import time
from database import (
    init_database,
    save_document,
    get_document_count,
    get_all_documents
)
import logging
from pathlib import Path
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

# 題目
ALLOWED_HOSTS = {
    "www.postgresql.org"
}

USER_AGENT = "IRandGAI-StudentSearchBot/1.0"
REQUEST_INTERVAL = 2
REQUEST_TIMEOUT = 10
MAX_REDIRECTS = 5

last_request_time = {}

HEADERS = {
    "User-Agent": USER_AGENT
}

# 文件路徑
ALLOWED_PATH_PREFIXES = (
    "/docs/",
)
# Retry 設定
MAX_ATTEMPTS_PER_URL = 3

# Log 檔案位置
LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "crawler.log"

# Logging 設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
MAX_TOTAL_ATTEMPTS = 3000


class RequestBudget:
    """管理整個爬蟲的 HTTP 請求次數"""

    def __init__(self, max_attempts=MAX_TOTAL_ATTEMPTS):
        self.max_attempts = max_attempts
        self.attempts = 0

    def consume(self):
        """請求前確認是否還有額度"""

        if self.attempts >= self.max_attempts:
            return False

        self.attempts += 1
        return True

    def remaining(self):
        return self.max_attempts - self.attempts


def normalize_url(url, base_url=None):
    """
    網址正規化：
    1. 支援相對網址
    2. 統一 scheme 與 hostname 大小寫
    3. 移除 fragment
    4. 保留 query parameters
    """

    if not url:
        return None

    url = url.strip()

    if base_url:
        url = urljoin(base_url, url)

    try:
        parsed = urlsplit(url)

        scheme = parsed.scheme.lower()

        # 只接受 HTTP / HTTPS
        if scheme not in ("http", "https"):
            return None

        hostname = parsed.hostname

        if not hostname:
            return None

        # 不接受包含帳號密碼的網址
        if parsed.username or parsed.password:
            return None

        hostname = hostname.lower()

        # 處理 Port
        port = parsed.port

        if port is not None:
            if not (
                (scheme == "http" and port == 80)
                or (scheme == "https" and port == 443)
            ):
                netloc = f"{hostname}:{port}"
            else:
                netloc = hostname
        else:
            netloc = hostname

        path = parsed.path or "/"

        # 不移除 query
        query = parsed.query

        # 移除 fragment
        return urlunsplit((
            scheme,
            netloc,
            path,
            query,
            ""
        ))

    except ValueError:
        return None


def is_allowed_url(url):
    """
    檢查網址是否符合爬取範圍：
    1. HTTP / HTTPS
    2. hostname 必須在白名單
    3. 路徑必須位於 /docs/ 下
    """

    if not url:
        return False

    try:
        parsed = urlsplit(url)

        if parsed.scheme not in ("http", "https"):
            return False

        if parsed.hostname not in ALLOWED_HOSTS:
            return False

        if not parsed.path.startswith(ALLOWED_PATH_PREFIXES):
            return False

        return True

    except ValueError:
        return False


def extract_links(html, base_url):
    """
    從 HTML 中擷取符合爬取範圍的連結。
    """

    soup = BeautifulSoup(html, "html.parser")

    links = set()

    for tag in soup.find_all("a", href=True):

        href = tag["href"]

        # 將相對網址轉成完整網址
        full_url = normalize_url(href, base_url)

        # 檢查網址是否符合爬取範圍
        if full_url and is_allowed_url(full_url):
            links.add(full_url)

    return links


class URLFrontier:

    def __init__(self):
        # 等待爬取的網址
        self.queue = deque()

        # 已經加入過佇列的網址
        self.known_urls = set()

    def add(self, url):
        """
        新增網址，避免重複。
        """

        normalized_url = normalize_url(url)

        if not normalized_url:
            return False

        if not is_allowed_url(normalized_url):
            return False

        if normalized_url in self.known_urls:
            return False

        self.queue.append(normalized_url)
        self.known_urls.add(normalized_url)

        return True

    def pop_next(self):
        """
        取出下一個等待爬取的網址。
        """

        if not self.queue:
            return None

        return self.queue.popleft()

    def is_empty(self):
        """
        確認佇列是否為空。
        """

        return len(self.queue) == 0

    def size(self):
        """
        回傳目前等待爬取的網址數量。
        """

        return len(self.queue)

def load_robots_parser():
    """
    讀取 PostgreSQL 官方網站的 robots.txt。
    """
    robots_url = "https://www.postgresql.org/robots.txt"

    response = requests.get(
        robots_url,
        headers=HEADERS,
        timeout=10,
        allow_redirects=False
    )

    parser = RobotFileParser()
    parser.set_url(robots_url)

    if response.status_code == 200:
        parser.parse(response.text.splitlines())

    elif response.status_code == 404:
        # 沒有 robots.txt，視為沒有設定爬取限制
        parser.parse([])

    else:
        # 遇到其他狀態或錯誤時，不冒險繼續爬取
        raise RuntimeError(
            f"無法確認 robots.txt 規則，HTTP {response.status_code}"
        )

    return parser

def is_allowed_by_robots(url, parser):
    """
    檢查 robots.txt 是否允許目前的爬蟲存取網址。
    """
    return parser.can_fetch(USER_AGENT, url)

def wait_for_host(host):
    """
    確保同一個主機的請求至少間隔 2 秒。
    """
    now = time.monotonic()
    last_time = last_request_time.get(host)

    if last_time is not None:
        elapsed = now - last_time
        if REQUEST_INTERVAL > elapsed:
            time.sleep(2)

    last_request_time[host] = time.monotonic()
    

def fetch_page(url, robots_parser, request_budget=None):
    """下載網頁，包含網址檢查、Redirect、Retry 與錯誤紀錄"""

    # 1. 檢查網址
    normalized_url = normalize_url(url)

    if not normalized_url:
        logger.warning("[SKIP] Invalid URL: %s", url)
        return None

    if not is_allowed_url(normalized_url):
        logger.warning("[SKIP] URL outside allowed scope: %s", normalized_url)
        return None

    if not is_allowed_by_robots(normalized_url, robots_parser):
        logger.warning("[SKIP] Blocked by robots.txt: %s", normalized_url)
        return None

    # 2. 最多嘗試三次
    for attempt in range(1, MAX_ATTEMPTS_PER_URL + 1):

        current_url = normalized_url
        redirect_count = 0

        try:
            # 3. 處理 Redirect
            while True:

                parsed = urlsplit(current_url)
                host = parsed.hostname

                # 確保同一 Host 請求間隔至少兩秒
                wait_for_host(host)
                if request_budget is not None:
                    if not request_budget.consume():
                        logger.error(
                            "[STOP] Global request limit reached: %s",
                            request_budget.max_attempts
                        )
                        return None
                response = requests.get(
                    current_url,
                    headers=HEADERS,
                    timeout=REQUEST_TIMEOUT,
                    allow_redirects=False
                )

                status = response.status_code

                # 4. 處理 Redirect
                if status in (301, 302, 303, 307, 308):

                    location = response.headers.get("Location")
                    response.close()

                    if not location:
                        logger.error(
                            "[FAIL] Redirect without Location: %s",
                            current_url
                        )
                        return None

                    redirect_count += 1

                    if redirect_count > MAX_REDIRECTS:
                        logger.error(
                            "[FAIL] Too many redirects: %s",
                            normalized_url
                        )
                        return None

                    next_url = normalize_url(
                        location,
                        current_url
                    )

                    if not next_url or not is_allowed_url(next_url):
                        logger.warning(
                            "[SKIP] Redirect outside allowed scope: %s",
                            location
                        )
                        return None

                    if not is_allowed_by_robots(next_url, robots_parser):
                        logger.warning(
                            "[SKIP] Redirect blocked by robots.txt: %s",
                            next_url
                        )
                        return None

                    logger.info(
                        "[REDIRECT] %s -> %s",
                        current_url,
                        next_url
                    )

                    current_url = next_url
                    continue

                # 5. 處理暫時性 HTTP 錯誤
                if status in (429, 500, 502, 503, 504):

                    if attempt < MAX_ATTEMPTS_PER_URL:
                        delay = get_retry_delay(response, attempt)
                        response.close()

                        logger.warning(
                            "[RETRY] HTTP %s | Attempt %s/%s | "
                            "Wait %.1f seconds | %s",
                            status,
                            attempt,
                            MAX_ATTEMPTS_PER_URL,
                            delay,
                            current_url
                        )

                        time.sleep(delay)
                        break

                    response.close()

                    logger.error(
                        "[FAIL] HTTP %s after %s attempts: %s",
                        status,
                        MAX_ATTEMPTS_PER_URL,
                        current_url
                    )
                    return None

                # 6. 處理其他非 200 狀態
                if status != 200:
                    response.close()

                    logger.error(
                        "[FAIL] HTTP %s: %s",
                        status,
                        current_url
                    )
                    return None

                # 7. 檢查 Content-Type
                content_type = response.headers.get(
                    "Content-Type", ""
                ).lower()

                if "text/html" not in content_type:
                    response.close()

                    logger.warning(
                        "[SKIP] Not HTML: %s | Content-Type: %s",
                        current_url,
                        content_type
                    )
                    return None

                # 8. 下載成功
                html = response.text
                response.close()

                logger.info(
                    "[SUCCESS] Downloaded: %s",
                    current_url
                )

                return {
                    "url": current_url,
                    "html": html
                }

            # 如果跳出 while，代表遇到可重試的 HTTP 狀態
            # 接著進入下一次 attempt
            continue

        except requests.RequestException as error:

            if attempt < MAX_ATTEMPTS_PER_URL:
                delay = 2 ** attempt

                logger.warning(
                    "[RETRY] Network error | Attempt %s/%s | "
                    "Wait %s seconds | %s | Error: %s",
                    attempt,
                    MAX_ATTEMPTS_PER_URL,
                    delay,
                    current_url,
                    error
                )

                time.sleep(delay)

            else:
                logger.error(
                    "[FAIL] Network error after %s attempts: %s | %s",
                    MAX_ATTEMPTS_PER_URL,
                    current_url,
                    error
                )

                return None

    return None


def inspect_html_structure(html):
    soup = BeautifulSoup(html, "html.parser")

    body = soup.body

    if not body:
        print("Body not found")
        return

    def print_div_tree(element, depth=0, max_depth=6):
        if depth > max_depth:
            return

        for child in element.find_all("div", recursive=False):
            indent = "  " * depth

            print(
                f"{indent}div | "
                f"ID: {child.get('id')} | "
                f"Class: {child.get('class')} | "
                f"Text: {child.get_text(' ', strip=True)[:100]}"
            )

            print_div_tree(child, depth + 1, max_depth)

    print("\nHTML DIV structure:")
    print_div_tree(body)

def parse_page(html, url):
    soup = BeautifulSoup(html, "html.parser")

    # 1. 找到 PostgreSQL 文件主要內容區域
    doc_content = soup.find("div", id="docContent")

    if not doc_content:
        logger.warning("[SKIP] docContent not found: %s", url)
        return None

    # 2. 判斷文件類型
    # SQL 指令參考文件通常使用 refentry
    # 一般教學章節可能使用 sect1、chapter 等結構
    article = doc_content.find(
        "div",
        class_="refentry"
    )

    if article is None:
        article = doc_content.find(
            "div",
            class_=[
                "sect1",
                "chapter",
                "appendix",
                "preface",
                "reference",
                "part"
            ]
        )

    if article is None:
        logger.debug("[SKIP] Article content not found: %s", url)
        return None

    # 3. 擷取標題
    if "refentry" in article.get("class", []):
        # SQL 指令參考文件
        title_element = article.select_one(".refentrytitle")

    else:
        # 一般章節文件
        title_element = (
            article.select_one(".titlepage h1.title")
            or article.select_one(".titlepage h2.title")
            or article.select_one(".titlepage h3.title")
            or article.select_one("h1.title")
            or article.select_one("h2.title")
            or article.select_one("h1")
            or article.select_one("h2")
        )

    title = (
        title_element.get_text(" ", strip=True).rstrip("#").strip()
        if title_element
        else ""
    )
    # 4. 移除不需要的 HTML 元素
    for element in article.select(
        ".navheader, .navfooter, script, style, #docComments"
    ):
        element.decompose()

    # 5. 擷取正文
    text = article.get_text(" ", strip=True)

    if not text.strip():
        logger.warning("[SKIP] Empty document: %s", url)
        return None

    # 6. 回傳統一格式
    return {
        "url": url,
        "title": title,
        "text": text
    }
    
def get_retry_delay(response, attempt):
    """計算重試前應等待的秒數"""

    retry_after = response.headers.get("Retry-After")

    if retry_after:
        # Retry-After 可能是秒數
        try:
            delay = float(retry_after)

        except ValueError:
            # 也可能是 HTTP 日期格式
            try:
                retry_time = parsedate_to_datetime(retry_after)

                if retry_time.tzinfo is None:
                    retry_time = retry_time.replace(
                        tzinfo=timezone.utc
                    )

                delay = (
                    retry_time - datetime.now(timezone.utc)
                ).total_seconds()

            except (ValueError, TypeError, OverflowError):
                delay = 2 ** attempt
    else:
        # 沒有 Retry-After 時，使用指數退避
        delay = 2 ** attempt

    # 最少等待 2 秒，最多等待 60 秒
    return min(max(delay, 2), 60)

def run_crawler(seed_urls, max_documents=200):
    print("\nStarting crawler...")
    print(f"Target documents: {max_documents}\n")

    init_database()

    robots_parser = load_robots_parser()

    frontier = URLFrontier()
    request_budget = RequestBudget()

    for url in seed_urls:
        frontier.add(url)

    skipped_count = 0

    while (
        not frontier.is_empty()
        and get_document_count() < max_documents
        and request_budget.remaining() > 0
    ):
        url = frontier.pop_next()

        result = fetch_page(
            url,
            robots_parser,
            request_budget=request_budget
        )

        if result is None:
            skipped_count += 1

            if request_budget.remaining() <= 0:
                break

            continue

        document = parse_page(
            result["html"],
            result["url"]
        )

        if not document or not document["text"].strip():
            skipped_count += 1
            continue

        save_document(document)

        links = extract_links(
            result["html"],
            result["url"]
        )

        for link in links:
            frontier.add(link)

        # 顯示目前進度
        current_count = get_document_count()

        print(
            f"\rProgress: {current_count:4d} / {max_documents} "
            f"| Requests: {request_budget.attempts:4d} / "
            f"{request_budget.max_attempts}",
            end="",
            flush=True
        )

    print("\n\nCrawler finished.")
    print(f"Documents: {get_document_count()}")
    print(f"HTTP requests: {request_budget.attempts}")

if __name__ == "__main__":
    seed_urls = [
        # SQL 指令參考文件
        "https://www.postgresql.org/docs/current/sql-select.html",

        # 教學文件
        "https://www.postgresql.org/docs/current/tutorial-window.html",

        # 其他文件
        "https://www.postgresql.org/docs/current/queries-with.html",
        "https://www.postgresql.org/docs/current/sql-keywords-appendix.html",

        # 不同版本的 SELECT 文件
        "https://www.postgresql.org/docs/16/sql-select.html",
        "https://www.postgresql.org/docs/14/sql-select.html",
        "https://www.postgresql.org/docs/9.5/sql-select.html",
        "https://www.postgresql.org/docs/8.1/sql-select.html"
    ]

    run_crawler(
        seed_urls=seed_urls,
        max_documents=200
    )