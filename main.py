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
from googleapiclient.discovery import build
from dotenv import load_dotenv
import time
import google.generativeai as genai

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure Gemini
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    logger.warning("GEMINI_API_KEY not found in environment variables")
genai.configure(api_key=gemini_api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

# Initialize FastAPI
app = FastAPI(
    title="AI Research Agent", 
    description="Fetch web sources, extract content, and summarize with Gemini.", 
    version="1.0.0"
)

# Get the current directory and setup paths
current_dir = Path(_file_).parent
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

class SearchResult(BaseModel):
    title: str
    url: str

class ExtractedContent(BaseModel):
    url: str
    title: str
    summary: str

# Google CSE Search function
def google_cse_search(query: str, num_results: int = 5):
    """Search using Google Custom Search Engine API"""
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        cse_id = os.getenv("GOOGLE_CSE_ID")
        
        if not api_key or not cse_id:
            logger.warning("Google API key or CSE ID not found in environment variables")
            return []
        
        logger.info(f"Searching Google CSE for: {query}")
        service = build("customsearch", "v1", developerKey=api_key)
        result = service.cse().list(q=query, cx=cse_id, num=num_results).execute()
        
        search_results = []
        if 'items' in result:
            logger.info(f"Found {len(result['items'])} results from Google CSE")
            for item in result['items']:
                search_results.append({
                    'title': item.get('title', 'No title'),
                    'url': item.get('link', ''),
                    'snippet': item.get('snippet', 'No snippet available')
                })
        else:
            logger.warning("No items found in Google CSE response")
        
        return search_results
    except Exception as e:
        logger.error(f"Google CSE API error: {e}")
        return []

# Hacker News Search function
def fetch_hn_search_results(query: str, limit: int = 5):
    """Hacker News search function"""
    try:
        logger.info(f"Searching Hacker News for: {query}")
        url = "http://hn.algolia.com/api/v1/search"
        params = {"query": query, "hitsPerPage": limit}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        results = []
        for hit in data["hits"]:
            if hit.get("title") and (hit.get("url") or hit.get("story_url")):
                results.append({
                    "title": hit["title"],
                    "url": hit["url"] or hit.get("story_url", "")
                })
        
        logger.info(f"Found {len(results)} results from Hacker News")
        return results
    except Exception as e:
        logger.error(f"Hacker News search failed: {e}")
        return []

# Fetch search results from multiple sources
def fetch_search_results(query: str, limit: int = 5):
    """Fetch results from multiple sources"""
    all_results = []
    
    # Try Google CSE first (primary source)
    google_results = google_cse_search(query, limit)
    
    if google_results:
        logger.info(f"Using {len(google_results)} results from Google CSE")
        for result in google_results:
            all_results.append({
                "title": result['title'],
                "url": result['url']
            })
    else:
        # If no Google results, try Hacker News as fallback
        logger.info("No Google results found, trying Hacker News")
        hn_results = fetch_hn_search_results(query, limit)
        if hn_results:
            logger.info(f"Using {len(hn_results)} results from Hacker News")
            all_results.extend(hn_results)
        else:
            logger.warning("No results found from any source")
    
    return all_results[:limit]

# Extract content from webpage with better error handling
def extract_content(url: str):
    try:
        logger.info(f"Extracting content from: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, timeout=15, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "footer", "aside", "header"]):
            element.decompose()
            
        title = soup.title.string if soup.title else "No title available"
        
        # Try to find main content areas
        main_selectors = ["main", "article", "[role='main']", ".content", ".main", ".article", "#content", "#main", "#article"]
        
        main_content = None
        for selector in main_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
                
        if main_content:
            text = main_content.get_text(separator=" ", strip=True)
        else:
            # Fallback to paragraph extraction
            paragraphs = soup.find_all("p")
            text = " ".join([p.get_text() for p in paragraphs[:10]])  # Limit paragraphs
        
        # Clean and limit text
        text = ' '.join(text.split())
        if len(text) > 8000:
            text = text[:8000] + "..."
            
        logger.info(f"Successfully extracted content from {url}")
        return {"title": title, "text": text, "success": True}
        
    except Exception as e:
        logger.error(f"Failed to extract content from {url}: {e}")
        return {"title": "Failed to extract content", "text": f"Error: {str(e)}", "success": False}

# Summarize with Gemini
def summarize_text(text: str, title: str = "") -> str:
    """Summarize text using Google Gemini"""
    try:
        if not text or len(text.strip()) < 50:
            return "Not enough content to summarize."
        
        if not gemini_api_key:
            return "Gemini API key not configured. Please set GEMINI_API_KEY environment variable."
        
        # Create the prompt for Gemini
        prompt = f"""
        Please provide a concise summary (2-3 paragraphs) of the following content:
        
        Title: {title}
        
        Content: {text[:8000]}
        
        Provide a clear and informative summary:
        """
        
        # Generate content
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        logger.error(f"Gemini summarization failed: {e}")
        return f"Summarization failed: {str(e)}"

# API Endpoints
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/search", response_class=HTMLResponse)
async def search_ui(request: Request, query: str = Form(...)):
    try:
        logger.info(f"Processing search query: {query}")
        web_results = fetch_search_results(query)
        extracted = []

        for i, result in enumerate(web_results):
            logger.info(f"Processing result {i+1}/{len(web_results)}: {result['url']}")
            content = extract_content(result["url"])
            summary = summarize_text(content["text"], content["title"])
            extracted.append({
                "url": result["url"],
                "title": content["title"],
                "summary": summary
            })
            # Add a small delay to avoid rate limiting
            time.sleep(0.5)

        return templates.TemplateResponse(
            "results.html", 
            {
                "request": request, 
                "query": query,
                "results": extracted
            }
        )
    except Exception as e:
        logger.error(f"Search UI error: {e}")
        return templates.TemplateResponse(
            "results.html", 
            {
                "request": request, 
                "query": query,
                "error": f"An error occurred: {str(e)}",
                "results": []
            }
        )

@app.post("/api/search", response_model=List[ExtractedContent])
async def search_api(search_terms: SearchTerms):
    web_results = fetch_search_results(search_terms.query)
    extracted = []

    for result in web_results:
        content = extract_content(result["url"])
        summary = summarize_text(content["text"], content["title"])
        extracted.append(ExtractedContent(
            url=result["url"],
            title=content["title"],
            summary=summary
        ))
        # Add a small delay to avoid rate limiting
        time.sleep(0.5)

    return extracted

@app.get("/health")
async def health_check():
    gemini_working = bool(os.getenv("GEMINI_API_KEY"))
    google_working = bool(os.getenv("GOOGLE_API_KEY") and os.getenv("GOOGLE_CSE_ID"))
    
    status = "healthy" if gemini_working else "degraded"
    
    return {
        "status": status,
        "services": {
            "google_cse": google_working,
            "gemini": gemini_working
        },
        "timestamp": time.time()
    }

@app.get("/debug")
async def debug_info():
    return {
        "current_dir": str(current_dir),
        "templates_dir": str(templates_dir),
        "templates_dir_exists": templates_dir.exists(),
        "static_dir": str(static_dir),
        "static_dir_exists": static_dir.exists(),
        "google_api_key_set": bool(os.getenv("GOOGLE_API_KEY")),
        "google_cse_id_set": bool(os.getenv("GOOGLE_CSE_ID")),
        "gemini_api_key_set": bool(os.getenv("GEMINI_API_KEY"))
    }

# Run the application
if _name_ == "_main_":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
