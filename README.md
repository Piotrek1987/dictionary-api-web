# 📖 Word Dictionary App

A Flask web application for looking up English words, viewing definitions, examples, synonyms, and exporting favorite words as CSV or PDF.

![screenshot](https://your-screenshot-url-if-you-have-one.png)

---

## 🚀 Features

- 🔍 Search words and get definitions from [Free Dictionary API](https://dictionaryapi.dev)
- 🌟 Mark favorites and export them
- 📄 Download your favorite words as **CSV** or **PDF**
- 📅 View a "Word of the Day" and quote
- 🧠 Track recent searches (stored in SQLite)

---

## 🧰 Tech Stack

- Flask (Python)
- SQLite (for history/favorites)
- FPDF (for PDF export)
- Jinja2 (templating)
- Hosted via [Render.com](https://render.com)

---

## 📦 Installation

1. Clone this repo:
   ```bash
   git clone https://github.com/your-username/word-dictionary-app.git
   cd word-dictionary-app

2. (Optional) Create a virtual environment:
    python -m venv venv
    source venv/bin/activate

3. Install dependencies:
   pip install -r requirements.txt

4. Run the app locally:
    python app.py
