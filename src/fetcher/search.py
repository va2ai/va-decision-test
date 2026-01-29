import re
import time
import logging
from typing import Optional
from urllib.parse import urlencode
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USER_AGENT = "VA-Decision-Test/1.0"
REQUEST_TIMEOUT = 15
RATE_LIMIT_DELAY = 2

# Year to dc parameter mapping for USA.gov search
YEAR_DC_MAP = {
    2020: 9161, 2021: 9162, 2022: 9256, 2023: 9692, 2024: 10080, 2025: 10280,
}

def build_search_url(query: str, year: Optional[int] = None) -> str:
    params = {"affiliate": "bvadecisions", "query": query}
    if year and year in YEAR_DC_MAP:
        params["dc"] = YEAR_DC_MAP[year]
    return f"https://search.usa.gov/search/docs?{urlencode(params)}"

def extract_year_from_url(url: str) -> int:
    match = re.search(r"/vetapp(\d{2})/", url)
    if match:
        yy = int(match.group(1))
        return 2000 + yy if yy < 50 else 1900 + yy
    return 2024

def search_bva(
    query: str,
    year: Optional[int] = None,
    max_results: int = 20,
    max_pages: int = 1
) -> list[dict]:
    """Search BVA decisions via USA.gov search."""
    results = []
    url = build_search_url(query, year)

    with httpx.Client(timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
        for page in range(max_pages):
            if len(results) >= max_results:
                break

            logger.info(f"Fetching page {page + 1} for '{query}'")
            resp = client.get(url)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            for r in soup.find_all("div", class_="result"):
                if len(results) >= max_results:
                    break

                title_elem = r.find("h4", class_="title")
                if not title_elem:
                    continue

                link = title_elem.find("a")
                if not link:
                    continue

                case_url = link.get("href", "")
                if not case_url.endswith(".txt"):
                    continue

                snippet_elem = r.find("span", class_="description")
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                case_number = case_url.split("/")[-1].replace(".txt", "")

                results.append({
                    "url": case_url,
                    "title": link.get_text(strip=True),
                    "snippet": snippet,
                    "year": extract_year_from_url(case_url),
                    "case_number": case_number,
                })

            # Check for next page
            next_link = soup.find("a", string="Next")
            if next_link and next_link.get("href"):
                url = next_link["href"]
                if not url.startswith("http"):
                    url = f"https://search.usa.gov{url}"
                time.sleep(RATE_LIMIT_DELAY)
            else:
                break

    return results

def fetch_decision_text(url: str) -> str:
    """Fetch raw text of a BVA decision."""
    if not url.startswith("https://www.va.gov/"):
        raise ValueError("URL must be from va.gov domain")

    with httpx.Client(timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text
