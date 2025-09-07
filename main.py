from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import requests
from bs4 import BeautifulSoup
import os
from pathlib import Path
from typing import List
import logging
import re
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Free Research Agent",
    description="DuckDuckGo-powered research with smart content extraction. No API keys required!",
    version="2.0.0"
)

# Paths
current_dir = Path(__file__).parent
templates_dir = current_dir / "templates"
static_dir = current_dir / "static"

# Mount static and templates
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)


# ---------- DuckDuckGo Search ----------
def duckduckgo_search(query: str, max_results: int = 6):
    try:
        logger.info(f"🔍 Searching DuckDuckGo for: {query}")
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html",
        }
        url = "https://html.duckduckgo.com/html/"
        params = {"q": query, "kl": "wt-wt", "df": "d"}
        response = requests.post(url, data=params, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        for result in soup.find_all("div", class_="result")[:max_results]:
            title_elem = result.find("a", class_="result__a")
            if not title_elem:
                continue
            title = title_elem.get_text(strip=True)
            raw_url = title_elem.get("href", "")
            if not raw_url or "duckduckgo.com" in raw_url:
                continue

            snippet_elem = result.find("a", class_="result__snippet")
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

            # Normalize URL
            if raw_url.startswith("//"):
                url = "https:" + raw_url
            elif raw_url.startswith("/"):
                url = "https://duckduckgo.com" + raw_url
            else:
                url = raw_url

            display_url = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]

            results.append({
                "title": title,
                "url": url,
                "snippet": snippet,
                "source": "duckduckgo",
                "display_url": display_url,
            })

        logger.info(f"✅ Found {len(results)} results")
        return results
    except Exception as e:
        logger.error(f"❌ DuckDuckGo search failed: {e}")
        return []


# ---------- Content Extraction ----------
def extract_research_content(url: str):
    try:
        logger.info(f"📄 Extracting content from: {url}")
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        for element in soup(["script", "style", "nav", "footer", "aside", "header", "form"]):
            element.decompose()

        title = soup.title.string if soup.title else "No title available"
        body_text = soup.get_text(separator="\n", strip=True)
        body_text = re.sub(r"\s+", " ", body_text)

        return {"title": title, "text": body_text[:3000], "success": True}
    except Exception as e:
        logger.error(f"❌ Failed to extract content: {e}")
        return {"title": "Unavailable", "text": "", "success": False}


# ---------- Summarization ----------
def smart_summarize(text: str):
    if not text:
        return {"summary": "No content available", "key_points": [], "credibility_score": 0}

    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

    summary = " ".join(sentences[:3]) if sentences else text[:300]
    key_points = sentences[:3]
    credibility_score = min(90, max(40, len(text) // 50))

    return {
        "summary": summary,
        "key_points": key_points,
        "credibility_score": credibility_score,
    }


# ---------- Research Workflow ----------
def conduct_research(query: str, max_results: int = 5):
    results = duckduckgo_search(query, max_results)
    seen = set()
    unique = []
    for r in results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique.append(r)
    return unique[:max_results]


# ---------- Routes ----------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/search", response_class=HTMLResponse)
async def search(request: Request, query: str = Form(...)):
    logger.info(f"🧪 Research started for: {query}")
    results_raw = conduct_research(query)
    analyzed_results = []

    for r in results_raw:
        content = extract_research_content(r["url"])
        if not content["success"]:
            continue
        summary_data = smart_summarize(content["text"])
        analyzed_results.append({
            "url": r["url"],
            "title": content["title"],
            "source": r.get("source", "web"),
            "summary": summary_data["summary"],
            "key_points": summary_data["key_points"],
            "credibility_score": summary_data["credibility_score"],
            "display_url": r.get("display_url", r["url"]),
        })
        time.sleep(0.5)

    return templates.TemplateResponse(
        "results.html",
        {"request": request, "query": query, "results": analyzed_results}
    )


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/debug")
async def debug():
    return {
        "templates_dir": str(templates_dir),
        "static_dir": str(static_dir),
        "templates_exist": (templates_dir / "index.html").exists(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
