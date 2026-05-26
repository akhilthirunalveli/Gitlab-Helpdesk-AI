import json
from langchain_text_splitters import RecursiveCharacterTextSplitter

with open("data/scraped_pages.json", "r", encoding="utf-8") as f:
    pages = json.load(f)

text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

print(f"Total pages in scraped_pages.json: {len(pages)}")
for idx, page in enumerate(pages):
    url = page.get("url")
    content = page.get("content", "")
    chunks = text_splitter.split_text(content)
    print(f"Page {idx}: {url} -> {len(chunks)} chunks")
