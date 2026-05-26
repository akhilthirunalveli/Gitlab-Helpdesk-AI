#!/usr/bin/env python3
"""
Scraper script for crawling GitLab's Handbook and Direction pages.
Crawls recursively up to 2 levels deep, extracts title and text content,
and saves the result to a local JSON file.
"""

import os
import json
import time
import logging
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("gitlab_scraper")

# Load environment variables
load_dotenv()
SCRAPED_DATA_PATH = os.getenv("SCRAPED_DATA_PATH", "data/scraped_pages.json")

# Base URLs to scrape
BASE_URLS = [
    "https://handbook.gitlab.com",
    "https://handbook.gitlab.com/handbook/values",
    "https://about.gitlab.com/direction/"
]

def is_valid_sublink(url: str, base_url: str) -> bool:
    """
    Checks if the URL is a valid sublink of the base URL.
    Ensures we stay within the desired path prefixes.
    """
    # Canonicalize URLs by stripping fragments
    url = url.split("#")[0].split("?")[0]
    base_url = base_url.split("#")[0].split("?")[0]

    # Ensure it starts with the base URL
    if not url.startswith(base_url):
        return False
        
    # Ignore binary/media files
    ignored_extensions = (".pdf", ".png", ".jpg", ".jpeg", ".gif", ".zip", ".tar.gz", ".mp4", ".mov")
    if url.lower().endswith(ignored_extensions):
        return False
        
    return True

def convert_table_to_markdown(table_soup) -> str:
    """
    Converts a BeautifulSoup HTML table element to a Markdown table string.
    """
    rows = table_soup.find_all("tr")
    if not rows:
        return ""
    
    markdown_rows = []
    
    # Check if there are headers
    first_row_cells = rows[0].find_all(["th", "td"])
    is_first_row_header = all(cell.name == "th" for cell in first_row_cells) or rows[0].find("th") is not None
    
    col_count = len(first_row_cells)
    
    if is_first_row_header:
        headers = [cell.get_text(strip=True).replace("\n", " ") for cell in first_row_cells]
        start_row_idx = 1
    else:
        # Generate generic headers if first row is not headers
        headers = [f"Column {i+1}" for i in range(col_count)]
        start_row_idx = 0
        
    # Format header row
    header_line = "| " + " | ".join(headers) + " |"
    sep_line = "| " + " | ".join(["---"] * len(headers)) + " |"
    markdown_rows.append(header_line)
    markdown_rows.append(sep_line)
    
    for row in rows[start_row_idx:]:
        cells = row.find_all(["th", "td"])
        if not cells:
            continue
        # Ensure cell count matches header count, pad with empty strings if necessary
        cell_texts = []
        for i in range(len(headers)):
            if i < len(cells):
                cell_texts.append(cells[i].get_text(strip=True).replace("\n", " ").replace("|", "\\|"))
            else:
                cell_texts.append("")
        row_line = "| " + " | ".join(cell_texts) + " |"
        markdown_rows.append(row_line)
        
    return "\n" + "\n".join(markdown_rows) + "\n"

def extract_page_data(html_content: str, url: str) -> dict:
    """
    Parses HTML content to extract title and main text content.
    Ignores nav, footer, scripts, styles, header, and aside tags.
    """
    soup = BeautifulSoup(html_content, "lxml")
    
    # Extract title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""
    if not title:
        h1_tag = soup.find("h1")
        title = h1_tag.get_text(strip=True) if h1_tag else "No Title"

    # Remove clutter tags
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "iframe"]):
        tag.decompose()
        
    # Try to find main content or fallback to body
    main_content = soup.find("main") or soup.find("article") or soup.find("div", {"id": "content"}) or soup.find("body")
    
    if main_content:
        # Convert tables to markdown
        for table in main_content.find_all("table"):
            markdown_table = convert_table_to_markdown(table)
            table.replace_with(soup.new_string(markdown_table))
            
        # Convert headings to markdown
        for h in main_content.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            level = int(h.name[1])
            heading_text = h.get_text(strip=True)
            h.replace_with(soup.new_string(f"\n\n{'#' * level} {heading_text}\n\n"))
            
        # Get clean text
        text = main_content.get_text(separator="\n")
    else:
        text = soup.get_text(separator="\n")
        
    # Clean text whitespace
    lines = [line.strip() for line in text.splitlines()]
    clean_lines = [line for line in lines if line]
    clean_text = "\n".join(clean_lines)
    
    return {
        "url": url,
        "title": title,
        "content": clean_text
    }

def get_links_from_page(html_content: str, current_url: str, base_url: str) -> list[str]:
    """
    Extracts all valid sublinks from a page's HTML content.
    """
    soup = BeautifulSoup(html_content, "lxml")
    links = []
    
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        # Resolve relative URLs
        full_url = urljoin(current_url, href)
        # Normalize: strip fragments
        full_url = full_url.split("#")[0].split("?")[0].rstrip("/")
        
        if is_valid_sublink(full_url, base_url):
            links.append(full_url)
            
    return sorted(list(set(links)))

def scrape_gitlab(max_pages: int = 100) -> None:
    """
    Scrapes the base URLs recursively up to depth 2 (levels 0, 1, 2).
    Saves the extracted page data list to data/scraped_pages.json.
    """
    # Track visited URLs globally across all base seeds
    visited_urls = set()
    scraped_data = []
    
    # BFS queue containing tuples: (url, depth, base_url_seed)
    queue = []
    for base_url in BASE_URLS:
        queue.append((base_url.rstrip("/"), 0, base_url))
        visited_urls.add(base_url.rstrip("/"))
        
    logger.info("Starting crawler with seed URLs: %s", BASE_URLS)
    
    pages_scraped_count = 0
    
    while queue and pages_scraped_count < max_pages:
        url, depth, base_seed = queue.pop(0)
        
        logger.info("Scraping page %d (depth=%d): %s", pages_scraped_count + 1, depth, url)
        
        try:
            # Respectful delay
            time.sleep(0.5)
            
            # Fetch the page
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                logger.warning("Failed to fetch %s (Status: %d)", url, response.status_code)
                continue
                
            # Extract content
            page_data = extract_page_data(response.text, url)
            scraped_data.append(page_data)
            pages_scraped_count += 1
            
            # If we haven't reached depth 2, discover child links
            if depth < 2:
                child_links = get_links_from_page(response.text, url, base_seed)
                for child in child_links:
                    if child not in visited_urls:
                        visited_urls.add(child)
                        queue.append((child, depth + 1, base_seed))
                        
        except requests.exceptions.RequestException as e:
            logger.error("Error scraping %s: %s", url, str(e))
        except Exception as e:
            logger.error("Unexpected error parsing %s: %s", url, str(e))
            
    logger.info("Scraping completed. Total pages scraped: %d", pages_scraped_count)
    
    # Ensure parent directories exist
    os.makedirs(os.path.dirname(SCRAPED_DATA_PATH), exist_ok=True)
    
    # Save output to JSON
    with open(SCRAPED_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(scraped_data, f, indent=2, ensure_ascii=False)
        
    logger.info("Saved scraped data to %s", SCRAPED_DATA_PATH)

if __name__ == "__main__":
    # Allow overriding max pages scraped through environment or command line
    # For a demo/production system, we scrape up to 100 pages, but this is configurable.
    max_to_scrape = int(os.getenv("MAX_PAGES_TO_SCRAPE", "100"))
    scrape_gitlab(max_pages=max_to_scrape)
