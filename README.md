![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-green)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-purple)
![License](https://img.shields.io/badge/License-MIT-yellow)

# 🤖 AI Research Agent

An intelligent web research assistant that leverages AI to find, extract, and summarize information from across the web.

## Features

- 🔍 Smart web search using Google Custom Search API
- 🧠 AI-powered summarization with OpenAI GPT
- 🎨 Professional, responsive web interface
- ⚡ Fast performance with async processing
- 📊 Multiple source integration

## Quick Start

1. Install dependencies: `pip install -r requirements.txt`
2. Set up environment variables in `.env` file
3. Run: `uvicorn main:app --reload`
4. Open: http://localhost:8000

## Environment Variables

Create a `.env` file with:
OPENAI_API_KEY=your_openai_api_key
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CSE_ID=your_search_engine_id


## License

MIT License - see LICENSE file for details
