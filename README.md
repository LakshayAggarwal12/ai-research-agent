🚀 Overview

Free Research Agent is a web-based research tool that helps you quickly find, extract, and summarize information from the web using DuckDuckGo search.

Unlike traditional research tools, it:

✅ Requires no API keys

✅ Extracts meaningful content from articles/summerization 

✅ Generates automatic summaries and key points

✅ Scores credibility based on content length and quality

✅ Comes with a simple & clean UI

Perfect for quick literature reviews, topic exploration, or background research.

📸 Screenshots
🔎 Home Page

A clean search interface:
<img width="1509" height="874" alt="image" src="https://github.com/user-attachments/assets/65ed0f14-2ce6-4691-9780-b88239817c83" />


📊 Results Page

Summarized and analyzed results:
<img width="1220" height="869" alt="image" src="https://github.com/user-attachments/assets/ef5d0572-b3ce-4511-b944-8091569ae979" />



⚡ Features

Web Search (DuckDuckGo HTML) → No API limits or keys

Content Extraction → Cleans unnecessary scripts, ads, and junk

Automatic Summarization → Key sentences + insights

Credibility Score → Quick quality indicator

Responsive UI → Mobile-friendly templates with Jinja2

🛠️ Tech Stack

Backend: FastAPI

Frontend: Jinja2 Templates

Scraping & Parsing: Requests
, BeautifulSoup4

Deployment: Render

📂 Project Structure
ai-research-agent/
│── app/
│   ├── main.py          # Main FastAPI app
│   ├── templates/       # Jinja2 templates (index.html, results.html)
│   ├── static/          # CSS, JS, Images
│   └── ...
│
│── requirements.txt     # Python dependencies
│── README.md            # Project documentation
│── Procfile/render.yaml # Deployment config (Render/Heroku)

⚙️ Installation & Setup
🔹 Clone the Repository
git clone https://github.com/your-username/ai-research-agent.git
cd ai-research-agent

🔹 Create Virtual Environment
python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows

🔹 Install Dependencies
pip install -r requirements.txt

🔹 Run Locally
uvicorn app.main:app --reload


Now visit 👉 http://127.0.0.1:8000

🌍 Deployment on Render

Push this repo to GitHub

Connect repo to Render

Add a Web Service → Environment = Python 3

Start Command:

gunicorn -k uvicorn.workers.UvicornWorker app.main:app


Done 🎉 → Your app is live!

🔧 API Endpoints

GET / → Home page (search UI)

POST /research → Submit search form & get results

GET /health → Health check JSON

GET /debug → Debug info about templates/static

📜 License

This project is licensed under the MIT License.
You’re free to use, modify, and distribute with attribution.

💡 Future Improvements

 Smarter NLP-based summarization (spaCy / transformers)

 User history & bookmarking

 Multi-source comparison view

 PDF/Doc export of research summaries

🤝 Contributing

Contributions are welcome! 🎯
Fork this repo, create a new branch, make your changes, and open a PR.

✨ Built with ❤️ using FastAPI
