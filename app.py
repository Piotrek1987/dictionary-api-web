from flask import Flask, render_template, request, redirect, url_for, session, send_file, make_response, Response, flash
import sqlite3
import requests
import os
import random
from datetime import date
import csv
from fpdf import FPDF
from io import BytesIO
import textwrap
import unicodedata
import re

app = Flask(__name__)
app.secret_key = "quizmeplease123"

QUOTES = [
    "The limits of my language mean the limits of my world. – Ludwig Wittgenstein",
    "One language sets you in a corridor for life. Two languages open every door along the way. – Frank Smith",
    "Words are, in my not-so-humble opinion, our most inexhaustible source of magic. – J.K. Rowling",
    "Language is the road map of a culture. – Rita Mae Brown",
    "To have another language is to possess a second soul. – Charlemagne",
    "Language shapes the way we think, and determines what we can think about. — Benjamin Lee Whorf",
    "Those who know nothing of foreign languages know nothing of their own. — Johann Wolfgang von Goethe",
    "Do you know what a foreign accent is? It's a sign of bravery. — Amy Chua"
]

# --- DB Setup ---
def init_db():
    with sqlite3.connect("history.db") as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, word TEXT, searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
        conn.execute("CREATE TABLE IF NOT EXISTS favorites (id INTEGER PRIMARY KEY, word TEXT UNIQUE);")
        conn.execute("CREATE TABLE IF NOT EXISTS daily_word (day TEXT PRIMARY KEY, word TEXT);")


def save_search(word):
    with sqlite3.connect("history.db") as conn:
        conn.execute("INSERT INTO history (word) VALUES (?);", (word,))

def get_recent_searches(limit=10):
    with sqlite3.connect("history.db") as conn:
        return conn.execute("SELECT id, word FROM history ORDER BY searched_at DESC LIMIT ?;", (limit,)).fetchall()

def save_favorite(word):
    with sqlite3.connect("history.db") as conn:
        conn.execute("INSERT OR IGNORE INTO favorites (word) VALUES (?);", (word,))

def get_favorites():
    with sqlite3.connect("history.db") as conn:
        return conn.execute("SELECT word FROM favorites;").fetchall()

def get_random_word():
    for attempt in range(10):  # attempt up to 10 times
        try:
            response = requests.get(
                "https://random-word-api.vercel.app/api?words=1",
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list) and data:
                word = data[0]
                definition = fetch_definition(word)
                if definition:
                    print(f"[WOTD] Selected '{word}' with valid definition")
                    return word
                else:
                    print(f"[WOTD] '{word}' has no definition")
        except requests.RequestException as e:
            print(f"[WOTD] Attempt {attempt+1} failed: {e}")

    print("[WOTD] All attempts failed—using fallback 'serendipity'")
    return "serendipity"



def get_daily_quote():
    today = date.today().toordinal()
    return QUOTES[today % len(QUOTES)]

def get_word_of_the_day():
    today = date.today().isoformat()
    with sqlite3.connect("history.db") as conn:
        row = conn.execute("SELECT word FROM daily_word WHERE day = ?", (today,)).fetchone()
        if row:
            return row[0]
        else:
            # Get new random word with valid definition
            while True:
                word = get_random_word()
                if fetch_definition(word):
                    break
            conn.execute("INSERT INTO daily_word (day, word) VALUES (?, ?);", (today, word))
            print(f"[WOTD] New word of the day set: {word}")
            return word

# def safe_text(text):
#     if not text:
#         return ""
#     text = str(text).replace("—", "-").replace("–", "-").replace("•", "*")
#     if any(len(word) > 100 for word in text.split()):
#         return "[Content skipped due to length]"
#     # Ensure Latin1-safe output
#     return text.encode('latin1', 'replace').decode('latin1')

def safe_text(text):
    if not text:
        return ""
    return str(text).replace("’", "'").replace("“", '"').replace("”", '"').replace("–", "-")

def clean_example(text):
    if not text:
        return ""
    text = str(text)

    # Normalize unicode (e.g., full-width punctuation, diacritics)
    text = unicodedata.normalize("NFKC", text)

    # Remove non-printable/control characters
    text = ''.join(c for c in text if unicodedata.category(c)[0] != "C")

    # Replace non-breaking and narrow spaces with regular space
    text = text.replace('\u00A0', ' ').replace('\u202F', ' ').replace('\u200B', '')

    # Collapse long "words" (i.e. unbroken strings)
    text = re.sub(r"(\S{25,})", r"\1 ", text)

    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Optional truncation
    if len(text) > 400:
        text = text[:400] + "..."

    return text

# --- Dictionary API Call ---
def fetch_definition(word):
    try:
        response = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}", timeout=5)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and data:
            return data[0]  # Always return dict
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching definition for '{word}': {e}")
        return None

# --- Routes ---
@app.route("/", methods=["GET", "POST"])
def index():
    word = request.args.get("word", "").strip()
    result = None

    word_of_the_day = get_word_of_the_day()
    wotd_data = fetch_definition(word_of_the_day)
    daily_quote = get_daily_quote()

    if request.method == "POST":
        word = request.form.get("word", "").strip()
        if word:
            result = fetch_definition(word)
            if result:
                save_search(word)

    elif word:
        result = fetch_definition(word)
        if result:
            save_search(word)

    recent_searches = get_recent_searches()

    return render_template("index.html",
                           word=word,
                           result=result,
                           word_of_the_day=word_of_the_day,
                           wotd_data=wotd_data,
                           daily_quote=daily_quote,
                           recent_searches=recent_searches)

@app.route("/favorite", methods=["POST"])
def favorite():
    word = request.form.get("word")
    if word:
        save_favorite(word)
        flash(f"'{word}' added to your favorites!")
    else:
        flash("No word received!")
    return redirect(request.referrer or url_for("index"))



@app.route("/favorites")
def favorites():
    words = get_favorites()
    favorites_dict = {}
    for word_tuple in words:
        word = word_tuple[0]
        data = fetch_definition(word.lower())
        if data:
            favorites_dict[word] = data
    daily_quote = get_daily_quote()
    return render_template("favorites.html", favorites=favorites_dict, daily_quote=daily_quote)


@app.route("/delete_search/<int:search_id>")
def delete_search(search_id):
    with sqlite3.connect("history.db") as conn:
        conn.execute("DELETE FROM history WHERE id = ?;", (search_id,))
    return redirect(url_for("index"))

@app.route("/clear_history")
def clear_history():
    with sqlite3.connect("history.db") as conn:
        conn.execute("DELETE FROM history;")
    return redirect(url_for("index"))

@app.route("/download/favorites/csv")
def download_csv():
    favorites = get_favorites()
    if not favorites:
        return redirect(url_for("favorites"))

    filename = "favorites_detailed.csv"
    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Word", "Phonetics", "Part of Speech", "Definition", "Example", "Synonyms"])

        for word_row in favorites:
            word = word_row[0]
            data = fetch_definition(word)
            if not data:
                continue

            phonetics = ", ".join(ph.get("text", "") for ph in data.get("phonetics", []) if "text" in ph)

            for meaning in data.get("meanings", []):
                for defn in meaning.get("definitions", []):
                    writer.writerow([
                        data["word"],
                        phonetics,
                        meaning.get("partOfSpeech", ""),
                        defn.get("definition", ""),
                        defn.get("example", ""),
                        ", ".join(defn.get("synonyms", []))
                    ])

    return send_file(filename, as_attachment=True)

@app.route("/download/favorites/pdf")
def download_pdf():
    with sqlite3.connect("history.db") as conn:
        favorites = conn.execute("SELECT word FROM favorites").fetchall()

    # favorites = get_favorites()
    # if not favorites:
    #     return "No favorites to download.", 400

    if not favorites:
        flash("No favorite words to export.")
        return redirect(url_for("favorites"))

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Fonts
    font_dir = os.path.join(os.path.dirname(__file__), "fonts")
    pdf.add_font('DejaVu', '', os.path.join(font_dir, 'DejaVuSans.ttf'))
    pdf.add_font('DejaVu', 'B', os.path.join(font_dir, 'DejaVuSans-Bold.ttf'))
    pdf.add_font('DejaVu', 'I', os.path.join(font_dir, 'DejaVuSans-Oblique.ttf'))
    pdf.set_font("DejaVu", "B", 16)
    pdf.cell(0, 10, "Favorite Words – Detailed Definitions", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(10)

    line_height = pdf.font_size * 1.5
    page_width = pdf.w - 2 * pdf.l_margin
    pdf.set_font("DejaVu", '', 12)

    for word_row in favorites:
        word = word_row[0]
        data = fetch_definition(word)
        if not data:
            print(f"[PDF] Skipping '{word}' – no definition found")
            continue

        pdf.add_page()
        pdf.ln(5)
        pdf.set_font("DejaVu", "B", 14)
        pdf.multi_cell(page_width, line_height, f"Word: {safe_text(data['word'])}")
        pdf.ln(1)

        # Phonetics
        phonetics = [p["text"] for p in data.get("phonetics", []) if p.get("text")]
        if phonetics:
            pdf.set_font("DejaVu", "I", 11)
            pdf.multi_cell(page_width, line_height, f"Phonetics: {', '.join(phonetics)}")
            pdf.ln(1)

        # Meanings & Definitions
        for meaning in data.get("meanings", []):
            pos = safe_text(meaning.get("partOfSpeech", ""))
            pdf.set_font("DejaVu", "B", 12)
            pdf.multi_cell(page_width, line_height, f"Part of Speech: {pos}")
            pdf.ln(1)

            for defn in meaning.get("definitions", []):
                # Definition bullet point
                pdf.set_font("DejaVu", '', 11)
                definition = safe_text(defn.get("definition", ""))
                pdf.multi_cell(page_width, line_height, f"- {definition}")

                # Example
                # example = clean_example(defn.get("example", ""))
                # if example:
                #     pdf.set_font("DejaVu", '', 10)  # temporarily use regular instead of italic
                #     pdf.multi_cell(page_width - 5, line_height, f"Example: {example}")
                #     pdf.ln(1)
                #     print(f"[DEBUG] page_width: {page_width}")

                example = defn.get("example", "")
                if example:
                    example = safe_text(example).strip()
                    print(f"[DEBUG] Final example text: {repr(example)}")

                    try:
                        pdf.set_font("Helvetica", '', 10)  # core font, avoids font fallback issues
                        pdf.set_text_color(90, 90, 90)  # light gray for example
                        pdf.set_x(15)  # left margin
                        pdf.multi_cell(w=170, h=6, text=f"Example: {example}", align="L")
                        pdf.ln(2)
                    except Exception as e:
                        print(f"[ERROR writing example]: {e}")
                    finally:
                        pdf.set_text_color(0, 0, 0)  # reset to black

                # Synonyms
                synonyms = defn.get("synonyms", [])
                if synonyms:
                    pdf.set_font("Helvetica", '', 8)
                    syn_line = f"Synonyms: {', '.join(safe_text(s) for s in synonyms)}"
                    pdf.multi_cell(page_width, line_height, syn_line)

                pdf.ln(1)  # space between definitions

            pdf.ln(5)  # space between words

    # Finalize and return the PDF
    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)
    return send_file(
        pdf_output,
        as_attachment=True,
        download_name="favorites.pdf",
        mimetype="application/pdf"
    )

@app.route("/random_word")
def random_word():
    word = get_random_word()
    return redirect(url_for("index", word=word))

@app.route("/archive")
def word_archive():
    with sqlite3.connect("history.db") as conn:
        rows = conn.execute("SELECT day, word FROM daily_word ORDER BY day DESC;").fetchall()

    archive_with_defs = []
    for day, word in rows:
        data = fetch_definition(word)
        if not data:
            continue

        archive_with_defs.append({
            "day": day,
            "word": word,
            "data": data
        })

    daily_quote = get_daily_quote()
    return render_template("archive.html", archive=archive_with_defs, daily_quote=daily_quote)



@app.route("/remove_favorite/<word>")
def remove_favorite(word):
    with sqlite3.connect("history.db") as conn:
        conn.execute("DELETE FROM favorites WHERE word = ?;", (word,))
    return redirect(url_for("favorites"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
