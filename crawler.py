import asyncio
import aiohttp
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from database import insert_document
from utils import clean_text


class WebCrawler:

    def __init__(self, max_pages=200, workers=25):

        self.visited = set()
        self.queued = set()
        self.failed_domains = set()

        self.to_visit = asyncio.Queue()

        self.max_pages = max_pages
        self.workers = workers

        self.sem = asyncio.Semaphore(10)

        # freeze detection
        self.last_progress = time.time()
        self.freeze_timeout = 600   # 10 minutes


    def is_valid_url(self, url):

        blacklist = ["#", "login", "signup", "contact", "privacy", "terms"]

        if any(word in url.lower() for word in blacklist):
            return False

        if url.endswith((".jpg", ".png", ".pdf", ".jpeg", ".svg")):
            return False

        return True


    async def fetch(self, session, url):

        try:

            async with self.sem:

                timeout = aiohttp.ClientTimeout(
                    total=6,
                    connect=4,
                    sock_read=4
                )

                async with session.get(url, timeout=timeout) as response:

                    if response.status in [403, 429]:
                        print("Blocked:", url)
                        return None

                    if response.status != 200:
                        return None

                    html = await response.text()

                    if len(html) > 1_000_000:
                        print("Page too large:", url)
                        return None

                    return html

        except asyncio.TimeoutError:
            print("Timeout:", url)
            return None

        except Exception as e:
            print("Fetch error:", url, e)
            return None


    async def worker(self, session, domains):

        while True:

            # freeze detection
            if time.time() - self.last_progress > self.freeze_timeout:
                print("Crawler frozen for too long. Stopping workers.")
                return

            if len(self.visited) >= self.max_pages:
                return

            url = await self.to_visit.get()

            try:

                if url in self.visited:
                    continue

                domain = urlparse(url).netloc

                if domain in self.failed_domains:
                    continue

                print("\nCrawling:", url)

                try:
                    html = await asyncio.wait_for(
                        self.fetch(session, url),
                        timeout=7
                    )
                except asyncio.TimeoutError:
                    print("Skipping slow site:", url)
                    self.failed_domains.add(domain)
                    self.visited.add(url)
                    continue


                if not html:
                    self.visited.add(url)
                    continue


                try:
                    soup = await asyncio.wait_for(
                        asyncio.to_thread(BeautifulSoup, html, "lxml"),
                        timeout=3
                    )
                except asyncio.TimeoutError:
                    print("Parsing too slow:", url)
                    self.visited.add(url)
                    continue


                article = soup.find("article")

                if article:
                    paragraphs = article.find_all("p")
                else:
                    paragraphs = soup.find_all("p")


                if len(paragraphs) < 3:
                    self.visited.add(url)
                    continue


                full_text = "\n".join(p.get_text() for p in paragraphs)

                words = clean_text(full_text)

                content = " ".join(words[:500])

                title = url
                if soup.title and soup.title.string:
                    title = soup.title.string.strip()


                doc_id = await asyncio.to_thread(
                    insert_document,
                    title,
                    url,
                    content
                )

                print("Inserted:", doc_id)

                # update freeze timer
                self.last_progress = time.time()

                self.visited.add(url)


                link_count = 0

                for link in soup.find_all("a", href=True):

                    if link_count >= 25:
                        break

                    href = link["href"]
                    full_url = urljoin(url, href)

                    parsed = urlparse(full_url)

                    if (
                        parsed.scheme in ["http", "https"]
                        and parsed.netloc in domains
                        and full_url not in self.visited
                        and full_url not in self.queued
                        and self.is_valid_url(full_url)
                    ):

                        if self.to_visit.qsize() < 700:

                            self.queued.add(full_url)
                            await self.to_visit.put(full_url)

                            link_count += 1


                print(
                    f"Visited: {len(self.visited)}/{self.max_pages} | Queue: {self.to_visit.qsize()}"
                )

            except Exception as e:

                print("Worker error:", e)

            finally:

                self.to_visit.task_done()


    async def crawl(self, start_urls):

        for url in start_urls:
            await self.to_visit.put(url)
            self.queued.add(url)

        domains = {urlparse(url).netloc for url in start_urls}

        async with aiohttp.ClientSession(
            headers={"User-Agent": "Mozilla/5.0"}
        ) as session:

            tasks = []

            for _ in range(self.workers):

                tasks.append(
                    asyncio.create_task(
                        self.worker(session, domains)
                    )
                )

            await self.to_visit.join()

            for task in tasks:
                task.cancel()


START_URLS = [

    "https://www.bbc.com/news/world",
    "https://www.bbc.com/news/politics",
    "https://www.bbc.com/news/technology",

    "https://edition.cnn.com/world",
    "https://edition.cnn.com/politics",

    "https://www.reuters.com/world/",
    "https://www.reuters.com/politics/",

    "https://www.theguardian.com/world",

    "https://www.thehindu.com/news/national/",
    "https://www.ndtv.com/world-news"
]


async def main():

    crawler = WebCrawler(
        max_pages=200,
        workers=25
    )

    await crawler.crawl(START_URLS)


if __name__ == "__main__":

    asyncio.run(main())

    print("\nCrawling finished.")
