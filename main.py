from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
import os
from pathlib import Path
from typing import List
import logging
import re
import time
import random

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Free Research Agent", 
    description="DuckDuckGo-powered research with smart content extraction. No API keys required!", 
    version="2.0.0"
)

# Get the current directory and setup paths
current_dir = Path(__file__).parent
templates_dir = current_dir / "templates"
static_dir = current_dir / "static"

# Create directories if they don't exist
static_dir.mkdir(exist_ok=True)
templates_dir.mkdir(exist_ok=True)

# Mount static files and setup templates
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

# Data Models
class SearchTerms(BaseModel):
    query: str

class ResearchResult(BaseModel):
    url: str
    title: str
    source: str
    summary: str
    key_points: List[str]
    credibility_score: int
    display_url: str

# DuckDuckGo Search function - No API keys needed!
def duckduckgo_search(query: str, max_results: int = 6):
    """Search DuckDuckGo without any API keys"""
    try:
        logger.info(f"🔍 Searching DuckDuckGo for: {query}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # DuckDuckGo search URL
        url = "https://html.duckduckgo.com/html/"
        params = {
            "q": query,
            "kl": "wt-wt",  # No specific region
            "df": "d"       # Any time
        }
        
        response = requests.post(url, data=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        
        # Find all search result elements
        result_elements = soup.find_all("div", class_="result")
        
        for result in result_elements[:max_results]:
            try:
                # Extract title and URL
                title_elem = result.find("a", class_="result__a")
                if not title_elem:
                    continue
                    
                title = title_elem.get_text(strip=True)
                raw_url = title_elem.get("href", "")
                
                # Skip DuckDuckGo internal links
                if "duckduckgo.com" in raw_url and "/y.js?" not in raw_url:
                    continue
                
                # Extract snippet
                snippet_elem = result.find("a", class_="result__snippet")
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                # Clean and validate URL
                if raw_url.startswith("//"):
                    url = "https:" + raw_url
                elif raw_url.startswith("/"):
                    url = "https://duckduckgo.com" + raw_url
                else:
                    url = raw_url
                
                # Extract display domain
                display_url = re.sub(r'^https?://(www\.)?', '', url)
                display_url = display_url.split('/')[0]
                
                results.append({
                    'title': title,
                    'url': url,
                    'snippet': snippet,
                    'source': 'duckduckgo',
                    'display_url': display_url
                })
                
            except Exception as e:
                logger.warning(f"Error parsing search result: {e}")
                continue
        
        logger.info(f"✅ Found {len(results)} results from DuckDuckGo")
        return results
        
    except Exception as e:
        logger.error(f"❌ DuckDuckGo search failed: {e}")
        return []

# Enhanced content extraction
def extract_research_content(url: str):
    """Extract meaningful content from webpages"""
    try:
        logger.info(f"📄 Extracting content from: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "footer", "aside", "header", "form"]):
            element.decompose()
        
        # Extract title
        title = soup.title.string if soup.title else "No title available"
        
        # Try to find main content
        content_selectors = [
            "article", "main", "[role='main']", ".content", ".article", 
            ".post", ".story-content", ".main-content", "#content"
        ]
        
        main_content = None
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        if not main_content:
            main_content = soup.body
        
        # Extract clean text
        text = main_content.get_text(separator="\n", strip=True)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'\s+', ' ', text)
        
        # Extract meaningful paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 80]
        
        if paragraphs:
            text = '\n\n'.join(paragraphs[:6])
        else:
            text = text[:1200]
        
        if len(text) > 5000:
            text = text[:5000] + "..."
        
        logger.info(f"✅ Successfully extracted content from {url}")
        
        return {
            "title": title,
            "text": text,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to extract content: {e}")
        return {
            "title": "Content unavailable",
            "text": "Could not extract content from this page.",
            "success": False
        }

# Smart summarization without API keys
def smart_summarize(text: str, title: str = "") -> dict:
    """Intelligent summarization using text analysis - No API needed!"""
    try:
        if not text or len(text.strip()) < 100:
            return {
                "summary": "Not enough content for a meaningful summary.",
                "key_points": [],
                "credibility_score": 0
            }
        
        # Extract sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        if not sentences:
            return {
                "summary": "Content structure not suitable for automatic summarization.",
                "key_points": [],
                "credibility_score": 50
            }
        
        # Simple algorithm: take first, middle, and last meaningful sentences
        summary_sentences = []
        if sentences:
            summary_sentences.append(sentences[0])  # First sentence (often introduction)
        
        if len(sentences) > 3:
            summary_sentences.append(sentences[len(sentences)//2])  # Middle sentence
        
        if len(sentences) > 1:
            summary_sentences.append(sentences[-1])  # Last sentence (often conclusion)
        
        # Create summary
        summary = " ".join(summary_sentences)
        
        # Extract key points (first few sentences that look important)
        key_points = []
        for sentence in sentences[:8]:  # Check first 8 sentences
            if len(sentence) > 30 and any(keyword in sentence.lower() for keyword in 
                                         ['important', 'key', 'summary', 'conclusion', 'findings']):
                key_points.append(sentence)
                if len(key_points) >= 3:
                    break
        
        # If no key points found, use first few meaningful sentences
        if not key_points:
            key_points = sentences[:3]
        
        # Calculate credibility score (simple heuristic)
        credibility_score = min(90, max(40, len(text) // 50))  # Longer content = more credible
        
        return {
            "summary": summary,
            "key_points": key_points[:5],
            "credibility_score": credibility_score
        }
        
    except Exception as e:
        logger.error(f"Summarization error: {e}")
        return {
            "summary": "Automatic summarization failed.",
            "key_points": [],
            "credibility_score": 0
        }

# Main research function
def conduct_research(query: str, max_results: int = 5):
    """Conduct complete research using DuckDuckGo"""
    results = duckduckgo_search(query, max_results)
    
    # Remove duplicates
    seen_urls = set()
    unique_results = []
    
    for result in results:
        if result['url'] not in seen_urls:
            seen_urls.add(result['url'])
            unique_results.append(result)
    
    return unique_results[:max_results]

# Create default templates if missing
def create_default_templates():
    """Ensure templates exist"""
    templates_dir.mkdir(exist_ok=True)
    
    # Simple index.html
    index_html = """<!DOCTYPE html>
<html>
<head>
    <title>Free Research Agent</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; background: #2c3e50; color: white; padding: 30px; border-radius: 10px; }
        .search-box { margin: 30px 0; text-align: center; }
        input[type="text"] { width: 70%; padding: 12px; font-size: 16px; border: 2px solid #ddd; border-radius: 5px; }
        button { padding: 12px 24px; background: #27ae60; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
        button:hover { background: #219a52; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 Free Research Agent</h1>
        <p>No API keys required • Powered by DuckDuckGo</p>
    </div>
    
    <div class="search-box">
        <form method="post" action="/research">
            <input type="text" name="query" placeholder="Enter any research topic..." required>
            <br><br>
            <button type="submit">Start Research</button>
        </form>
    </div>
</body>
</html>"""
    
    # Simple results.html
    results_html = """<!DOCTYPE html>
<html>
<head>
    <title>Research Results</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; }
        .back-link { color: #3498db; text-decoration: none; }
        .result { background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #3498db; }
        .result h3 { margin-top: 0; color: #2c3e50; }
        .url { color: #7f8c8d; font-size: 14px; }
        .score { background: #27ae60; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
        .key-points { background: #fff3cd; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .error { background: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px; }
    </style>
</head>
<body>
    <a href="/" class="back-link">← New Search</a>
    <h1>📊 Research Results for: "{{ query }}"</h1>
    
    {% if error %}
        <div class="error">
            <h3>⚠️ Error</h3>
            <p>{{ error }}</p>
        </div>
    {% endif %}
    
    {% if results %}
        <p>Found {{ results|length }} results:</p>
        {% for result in results %}
            <div class="result">
                <h3>{{ result.title }}</h3>
                <div class="url">{{ result.display_url }}</div>
                {% if result.credibility_score > 0 %}
                    <span class="score">Credibility: {{ result.credibility_score }}/100</span>
                {% endif %}
                
                <p><strong>Summary:</strong> {{ result.summary }}</p>
                
                {% if result.key_points %}
                    <div class="key-points">
                        <strong>🔑 Key Points:</strong>
                        <ul>
                            {% for point in result.key_points %}
                                <li>{{ point }}</li>
                            {% endfor %}
                        </ul>
                    </div>
                {% endif %}
                
                <p><small>Source: {{ result.source }} • <a href="{{ result.url }}" target="_blank">Visit Website</a></small></p>
            </div>
        {% endfor %}
    {% else %}
        <p>No results found. Try a different search term.</p>
    {% endif %}
</body>
</html>"""
    
    # Write templates
    (templates_dir / "index.html").write_text(index_html)
    (templates_dir / "results.html").write_text(results_html)
    logger.info("📁 Default templates created")

# Create templates if they don't exist
if not (templates_dir / "index.html").exists():
    create_default_templates()

# API Endpoints
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/research", response_class=HTMLResponse)
async def research_ui(request: Request, query: str = Form(...)):
    try:
        if not query or len(query.strip()) < 2:
            return templates.TemplateResponse(
                "results.html", 
                {
                    "request": request, 
                    "query": query,
                    "error": "Please enter a valid search term (at least 2 characters)",
                    "results": []
                }
            )
        
        logger.info(f"🧪 Research started for: {query}")
        research_results = conduct_research(query)
        analyzed_results = []

        for i, result in enumerate(research_results):
            logger.info(f"📊 Analyzing result {i+1}/{len(research_results)}: {result['url']}")
            
            content = extract_research_content(result["url"])
            
            if not content["success"]:
                logger.warning(f"❌ Content extraction failed for {result['url']}")
                continue
                
            analysis = smart_summarize(content["text"], content["title"])
            
            analyzed_results.append({
                "url": result["url"],
                "title": content["title"],
                "source": result.get("source", "web"),
                "summary": analysis["summary"],
                "key_points": analysis["key_points"],
                "credibility_score": analysis["credibility_score"],
                "display_url": result.get("display_url", result["url"][:30] + "..."),
            })
            
            time.sleep(0.5)  # Be nice to websites

        return templates.TemplateResponse(
            "results.html", 
            {
                "request": request, 
                "query": query,
                "results": analyzed_results,
                "total_results": len(analyzed_results)
            }
        )
        
    except Exception as e:
        logger.error(f"💥 Research UI error: {e}")
        return templates.TemplateResponse(
            "results.html", 
            {
                "request": request, 
                "query": query,
                "error": f"Research error: {str(e)}",
                "results": []
            }
        )

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "message": "Free Research Agent is running! No API keys required.",
        "version": "2.0.0",
        "timestamp": time.time()
    }

@app.get("/debug")
async def debug_info():
    return {
        "templates_dir": str(templates_dir),
        "templates_exist": (templates_dir / "index.html").exists(),
        "static_dir": str(static_dir),
        "static_exists": static_dir.exists(),
        "api_keys_required": "none"
    }

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
