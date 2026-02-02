import asyncio
import json
from pathlib import Path

import httpx
from bs4 import BeautifulSoup


class DuckDBDocsScraper:
    def __init__(self, max_pages: int = 50):
        self.base_url = "https://duckdb.org/docs/stable/"
        self.scraped_content = []
        self.visited_urls = set()
        self.max_pages = max_pages

    async def _fetch_page(self, client: httpx.AsyncClient, url: str) -> str | None:
        try:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            return None

    def _extract_content(self, soup: BeautifulSoup) -> dict:
        for element in soup.find_all(["script", "style", "nav", "header", "footer"]):
            element.decompose()

        title = ""
        title_elem = soup.find("div", class_="title")
        if title_elem:
            title = title_elem.get_text(strip=True)
        else:
            h1_elem = soup.find("h1")
            if h1_elem:
                title = h1_elem.get_text(strip=True)

        main_content = soup.find("div", id="main_content_wrap") or soup.find("main")
        if not main_content:
            return {"title": title, "content": "", "sections": []}

        for selector in [
            ".sidenavigation",
            ".toc_menu",
            ".pagemeta",
            ".bottomline",
            ".headlinebar",
            ".breadcrumbs",
            ".index",
            "#sidebar",
        ]:
            for elem in main_content.select(selector):
                elem.decompose()

        sections = []
        current_section = {"heading": "", "content": []}

        for element in main_content.find_all(["h2", "h3", "h4", "p", "pre", "table", "ul", "ol"]):
            if element.name in ["h2", "h3", "h4"]:
                if current_section["content"]:
                    sections.append(
                        {
                            "heading": current_section["heading"],
                            "text": "\n".join(current_section["content"]),
                        }
                    )
                current_section = {"heading": element.get_text(strip=True), "content": []}
            else:
                text = element.get_text(separator=" ", strip=True)
                if text and len(text) > 10:
                    current_section["content"].append(text)

        if current_section["content"]:
            sections.append(
                {
                    "heading": current_section["heading"],
                    "text": "\n".join(current_section["content"]),
                }
            )

        full_text = f"{title}\n\n" + "\n\n".join(
            f"{s['heading']}\n{s['text']}" if s["heading"] else s["text"] for s in sections
        )

        return {"title": title, "content": full_text.strip(), "sections": sections}

    def _get_sub_urls(self, soup: BeautifulSoup) -> list[str]:
        sidebar = soup.find("div", class_="sidenavigation")
        if not sidebar:
            return []

        sub_urls = []
        for link in sidebar.find_all("a", href=True):
            href = str(link["href"])

            if href.startswith("/docs/stable/"):
                full_url = f"https://duckdb.org{href}"
            elif href.startswith("http"):
                full_url = href
            else:
                continue

            if "sql/functions/" in full_url and full_url not in self.visited_urls:
                sub_urls.append(full_url)

        return sub_urls

    async def _scrape_page(self, client: httpx.AsyncClient, url: str):
        if url in self.visited_urls or len(self.visited_urls) >= self.max_pages:
            return

        self.visited_urls.add(url)
        print(f"Scraping [{len(self.visited_urls)}/{self.max_pages}]: {url}")

        html = await self._fetch_page(client, url)
        if not html:
            return

        soup = BeautifulSoup(html, "html.parser")
        content = self._extract_content(soup)
        content["url"] = url
        self.scraped_content.append(content)

        for sub_url in self._get_sub_urls(soup):
            await self._scrape_page(client, sub_url)

    async def scrape(self):
        async with httpx.AsyncClient() as client:
            await self._scrape_page(client, f"{self.base_url}sql/functions/overview")
        print(f"Scraped {len(self.scraped_content)} pages")
        return self.scraped_content

    def save_to_file(self, output_path: str = "scripts/data/duckdb_docs_raw.json"):
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.scraped_content, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(self.scraped_content)} pages to {output_file}")


async def main():
    scraper = DuckDBDocsScraper()
    await scraper.scrape()
    scraper.save_to_file()


if __name__ == "__main__":
    asyncio.run(main())
