# 🏔️ Project Sentinel: Autonomous Data Scraper

**Built for the ML Empowerment Build Challenge 3.0**

This repository contains the backend data engine for **Project Sentinel**, an AI-driven ecosystem designed to promote sustainable tourism in Jammu & Kashmir. 

While popular spots face overtourism, countless beautiful locations remain hidden. This Python-based scraper autonomously mines Hindi travel vlogs on YouTube to extract verified "hidden gems" (like Drung Waterfall or offbeat trails near Pahalgam), processes them using Gemini 3.5 Flash-Lite, and feeds them into our live Google Sheets database for the frontend Next.js app to use via RAG.

## ✨ Features
* **Autonomous Execution:** Scheduled to run entirely on GitHub Actions without human intervention.
* **Smart Extraction:** Uses `youtube-transcript-api` to pull Hindi and English captions from local travel vlogs.
* **AI Parsing Pipeline:** Feeds the raw transcripts to Google's Gemini 3.5 Flash-Lite API, which intelligently parses out geospatial data, location names, and vibe descriptions.
* **Live Database Sync:** Pushes the cleaned, structured JSON data directly to a Google Sheets Webhook, instantly updating the RAG context for the frontend.

## 🛠️ Tech Stack
* **Language:** Python 3.x
* **APIs:** Google Gemini 3.5 Flash-Lite API, YouTube Transcript API
* **Automation:** GitHub Actions (CI/CD)
* **Database Pipeline:** Google Apps Script (Webhook) & Google Sheets

## 🧠 Data Flow Architecture
1. **Fetch:** The script identifies relevant J&K travel vlog URLs.
2. **Extract:** Transcripts are pulled using `youtube-transcript-api`.
3. **Analyze:** Gemini 3.5 Flash-Lite processes the text to identify offbeat locations, removing generic tourist traps.
4. **Format:** The data is structured into a clean JSON array (Name, Location, Description, Tags).
5. **Sync:** The script sends a POST request to our Google Apps Script Webhook, live-updating the database used by the Next.js frontend.

## 🚀 Local Setup

1. **Clone the repository:**
git clone https://github.com/DRUNKAssassin/project-sentinel.git
cd project-sentinel-scraper

2. **Install dependencies:**
pip install -r requirements.txt

*(If you don't have a requirements.txt, run: `pip install google-genai youtube-transcript-api requests`)*

3. **Set up environment variables:**
Create a `.env` file (or set your system variables) with your API key:
GEMINI_API_KEY=your_gemini_api_key_here

4. **Run the scraper manually:**
python scraper.py
