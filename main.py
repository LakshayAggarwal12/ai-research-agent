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
import re
import random

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
    description="Search engine research with enhanced content extraction and analysis.", 
    version="1.0.0"
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

# Check if templates exist, create if missing
if not (templates_dir / "index.html").exists() or not (templates_dir / "results.html").exists():
    logger.warning("Templates missing, creating default templates")
    create_default_templates()
else:
    logger.info("Templates found and ready")

# Create default templates if they don't exist
def create_default_templates():
    """Create default HTML templates if they don't exist"""
    
    # Create index.html
    index_html = """<!DOCTYPE html>
<html>
<head>
    <title>AI Research Agent</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .container { background: #f5f5f5; padding: 30px; border-radius: 10px; }
        input[type="text"] { width: 70%; padding: 10px; font-size: 16px; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
        .result { margin: 20px 0; padding: 15px; background: white; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 AI Research Agent</h1>
        <form method="post" action="/research">
            <input type="text" name="query" placeholder="Enter research topic..." required>
            <button type="submit">Research</button>
        </form>
    </div>
</body>
</html>"""
    
    # Create results.html
    results_html = """<!DOCTYPE html>
<html>
<head>
    <title>Research Results</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; }
        .result { margin: 20px 0; padding: 20px; background: #f9f9f9; border-radius: 8px; border-left: 4px solid #007bff; }
        .url { color: #0066cc; font-size: 14px; }
        .score { background: #28a745; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
        .error { background: #ffebee; color: #c62828; padding: 15px; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>📊 Research Results for: "{{ query }}"</h1>
    <a href="/">← New Search</a>
    
    {% if error %}
        <div class="error">
            <h3>Error</h3>
            <p>{{ error }}</p>
        </div>
    {% endif %}
    
    {% if results %}
        <p>Found {{ results|length }} results:</p>
        {% for result in results %}
            <div class="result">
                <h3>{{ result.title }}</h3>
                <div class="url">{{ result.url }}</div>
                {% if result.credibility_score > 0 %}
                    <span class="score">Credibility: {{ result.credibility_score }}/100</span>
                {% endif %}
                <p><strong>Summary:</strong> {{ result.summary }}</p>
                {% if result.key_points %}
                    <div>
                        <strong>Key Points:</strong>
                        <ul>
                            {% for point in result.key_points %}
                                <li>{{ point }}</li>
                            {% endfor %}
                        </ul>
                    </div>
                {% endif %}
            </div>
        {% endfor %}
    {% else %}
        <p>No results found. Try a different search term.</p>
    {% endif %}
</body>
</html>"""
    
    # Create templates directory if it doesn't exist
    templates_dir.mkdir(exist_ok=True)
    
    # Write template files
    (templates_dir / "index.html").write_text(index_html)
    (templates_dir / "results.html").write_text(results_html)
    logger.info("Default templates created")

# Call this function after template setup
create_default_templates()

# Data Models
class SearchTerms(BaseModel):
    query: str

class SearchResult(BaseModel):
    title: str
    url: str
    source: str
    snippet: str

class ResearchResult(BaseModel):
    url: str
    title: str
    source: str
    summary: str
    key_points: List[str]
    credibility_score: int

# Search Engines Configuration
SEARCH_ENGINES = {
    "google": {
        "name": "Google Search",
        "weight": 0.8
    },
    "hackernews": {
        "name": "Hacker News",
        "weight": 0.6
    },
    "scholar": {
        "name": "Academic Sources",
        "weight": 0.9
    }
}

# Google CSE Search function
def google_cse_search(query: str, num_results: int = 8):
    """Search using Google Custom Search Engine API"""
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        cse_id = os.getenv("GOOGLE_CSE_ID")
        
        if not api_key or not cse_id:
            logger.warning("Google API key or CSE ID not found")
            return []
        
        logger.info(f"Searching Google CSE for: {query}")
        service = build("customsearch", "v1", developerKey=api_key)
        result = service.cse().list(
            q=query, 
            cx=cse_id, 
            num=num_results,
            gl="us",
            lr="lang_en"
        ).execute()
        
        search_results = []
        if 'items' in result:
            logger.info(f"Found {len(result['items'])} results from Google CSE")
            for item in result['items']:
                search_results.append({
                    'title': item.get('title', 'No title'),
                    'url': item.get('link', ''),
                    'snippet': item.get('snippet', ''),
                    'source': 'google',
                    'display_url': item.get('displayLink', '')
                })
        return search_results
    except Exception as e:
        logger.error(f"Google CSE API error: {e}")
        return []

# Hacker News Search function
def fetch_hn_search_results(query: str, limit: int = 4):
    """Hacker News search function for technical content"""
    try:
        logger.info(f"Searching Hacker News for: {query}")
        url = "http://hn.algolia.com/api/v1/search"
        params = {
            "query": query, 
            "hitsPerPage": limit,
            "tags": "story",
            "numericFilters": "points>10"
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        results = []
        for hit in data["hits"]:
            if hit.get("title") and hit.get("url"):
                results.append({
                    "title": hit["title"],
                    "url": hit["url"],
                    "snippet": hit.get("_highlightResult", {}).get("content", {}).get("value", "")[:200] if hit.get("_highlightResult", {}).get("content") else "",
                    "source": "hackernews",
                    "display_url": "news.ycombinator.com"
                })
        
        logger.info(f"Found {len(results)} results from Hacker News")
        return results
    except Exception as e:
        logger.error(f"Hacker News search failed: {e}")
        return []

# Enhanced content extraction with better parsing
def extract_research_content(url: str):
    """Enhanced content extraction for research purposes"""
    try:
        logger.info(f"Extracting research content from: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        response = requests.get(url, timeout=12, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "footer", "aside", "header", "form", "button"]):
            element.decompose()
        
        # Extract title
        title = soup.title.string if soup.title else "No title available"
        
        # Try to identify article structure
        article_selectors = [
            "article", "[role='main']", "main", ".article", ".content", 
            ".post", ".blog-post", ".story", ".main-content", "#content"
        ]
        
        main_content = None
        content_source = "body"
        
        for selector in article_selectors:
            found = soup.select_one(selector)
            if found:
                main_content = found
                content_source = selector
                break
        
        if not main_content:
            main_content = soup.body
            content_source = "body"
        
        # Clean and extract text
        text = main_content.get_text(separator="\n", strip=True)
        
        # Remove excessive whitespace and clean up
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'\s+', ' ', text)
        
        # Extract meaningful paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 100]
        
        if paragraphs:
            text = '\n\n'.join(paragraphs[:8])  # Take top 8 paragraphs
        else:
            # Fallback: use first 1000 characters
            text = text[:1000]
        
        # Limit text length
        if len(text) > 6000:
            text = text[:6000] + "..."
        
        # Extract metadata
        meta_description = soup.find("meta", attrs={"name": "description"})
        description = meta_description["content"] if meta_description else ""
        
        # Determine content type
        content_type = "article"
        if any(x in url for x in ['.pdf', '.doc', '.docx']):
            content_type = "document"
        elif any(x in url for x in ['github.com', 'stackoverflow.com']):
            content_type = "technical"
        
        logger.info(f"Successfully extracted {content_type} content from {url}")
        
        return {
            "title": title,
            "text": text,
            "description": description,
            "content_type": content_type,
            "content_source": content_source,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Failed to extract content from {url}: {e}")
        return {
            "title": "Content extraction failed",
            "text": f"Unable to extract content: {str(e)}",
            "description": "",
            "content_type": "error",
            "success": False
        }

# Enhanced summarization with research focus
def generate_research_summary(text: str, title: str = "", content_type: str = "article") -> dict:
    """Generate comprehensive research summary with key points"""
    try:
        if not text or len(text.strip()) < 100:
            return {
                "summary": "Insufficient content for meaningful analysis.",
                "key_points": [],
                "credibility_score": 0
            }
        
        if not gemini_api_key:
            return {
                "summary": "API configuration required.",
                "key_points": [],
                "credibility_score": 0
            }
        
        # Create research-focused prompt
        prompt = f"""
        Analyze this {content_type} content for research purposes and provide:
        
        1. A comprehensive 3-paragraph summary
        2. 5 key bullet points of main ideas/findings
        3. Credibility assessment score (1-100)
        
        Title: {title}
        
        Content: {text[:5000]}
        
        Provide output in this exact format:
        SUMMARY: [your summary here]
        KEY_POINTS: [bullet point 1] | [bullet point 2] | [bullet point 3] | [bullet point 4] | [bullet point 5]
        CREDIBILITY: [score 1-100]
        """
        
        response = model.generate_content(prompt)
        result_text = response.text
        
        # Parse the response
        summary = "Analysis unavailable"
        key_points = []
        credibility_score = 50  # Default neutral score
        
        if "SUMMARY:" in result_text:
            parts = result_text.split("SUMMARY:")
            if len(parts) > 1:
                summary_part = parts[1].split("KEY_POINTS:")[0].strip()
                summary = summary_part
        
        if "KEY_POINTS:" in result_text:
            kp_part = result_text.split("KEY_POINTS:")[1].split("CREDIBILITY:")[0].strip()
            key_points = [kp.strip() for kp in kp_part.split("|") if kp.strip()][:5]
        
        if "CREDIBILITY:" in result_text:
            try:
                cred_part = result_text.split("CREDIBILITY:")[1].strip()
                credibility_score = min(100, max(1, int(cred_part.split()[0])))
            except:
                pass
        
        return {
            "summary": summary,
            "key_points": key_points,
            "credibility_score": credibility_score
        }
        
    except Exception as e:
        logger.error(f"Research analysis failed: {e}")
        return {
            "summary": f"Analysis failed: {str(e)}",
            "key_points": [],
            "credibility_score": 0
        }

# Main research function
def conduct_research(query: str, max_results: int = 6):
    """Conduct comprehensive research across multiple sources"""
    all_results = []
    
    # Get results from multiple sources
    google_results = google_cse_search(query, max_results)
    hn_results = fetch_hn_search_results(query, min(3, max_results//2))
    
    # Combine and prioritize results
    if google_results:
        all_results.extend(google_results)
    if hn_results:
        all_results.extend(hn_results)
    
    # Remove duplicates and limit results
    seen_urls = set()
    unique_results = []
    
    for result in all_results:
        if result['url'] not in seen_urls and len(unique_results) < max_results:
            seen_urls.add(result['url'])
            unique_results.append(result)
    
    return unique_results

@app.get("/debug-templates")
async def debug_templates():
    """Check if templates exist and are readable"""
    index_path = templates_dir / "index.html"
    results_path = templates_dir / "results.html"
    
    return {
        "templates_dir": str(templates_dir),
        "index_exists": index_path.exists(),
        "results_exists": results_path.exists(),
        "index_content": index_path.read_text()[:100] + "..." if index_path.exists() else "MISSING",
        "results_content": results_path.read_text()[:100] + "..." if results_path.exists() else "MISSING"
    }

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
        
        logger.info(f"Processing research query: {query}")
        research_results = conduct_research(query)
        analyzed_results = []

        for i, result in enumerate(research_results):
            logger.info(f"Analyzing result {i+1}/{len(research_results)}: {result['url']}")
            
            content = extract_research_content(result["url"])
            
            # Skip if content extraction failed
            if not content["success"]:
                logger.warning(f"Content extraction failed for {result['url']}")
                continue
                
            analysis = generate_research_summary(
                content["text"], 
                content["title"],
                content["content_type"]
            )
            
            analyzed_results.append({
                "url": result["url"],
                "title": content["title"],
                "source": result.get("source", "unknown"),
                "summary": analysis["summary"],
                "key_points": analysis["key_points"],
                "credibility_score": analysis["credibility_score"],
                "display_url": result.get("display_url", result["url"][:50] + "..."),
            })
            
            time.sleep(1.2)

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
        logger.error(f"Research UI error: {e}")
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
    gemini_working = bool(os.getenv("GEMINI_API_KEY"))
    google_working = bool(os.getenv("GOOGLE_API_KEY") and os.getenv("GOOGLE_CSE_ID"))
    
    return {
        "status": "operational" if gemini_working else "degraded",
        "services": {
            "google_cse": google_working,
            "gemini": gemini_working
        },
        "timestamp": time.time()
    }

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
