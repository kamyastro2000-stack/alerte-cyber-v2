import os
import logging
import feedparser
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
import google.generativeai as genai

# --- CONFIGURATION ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GEMINI_KEY = os.environ.get("GEMINI_KEY")  # La clé API Google

# Config IA
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-pro')

# Setup Flask
app = Flask(__name__)


@app.route('/')
def home():
    return "SentineL V3 est Active ⚡"


def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)


# --- SOURCES DE RENSEIGNEMENT ---
SOURCES = {
    "NEWS_FR": "https://cyberveille.fr/feed/",
    "NEWS_EN": "https://feeds.feedburner.com/TheHackersNews",
    "CVE_CRITICAL": "https://nvd.nist.gov/feeds/xml/cve/misc/nvd-rss.xml"  # Flux officiel des failles
}

DB_FILE = "sent_articles.txt"
logging.basicConfig(level=logging.INFO)


def load_sent_articles():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return set(f.read().splitlines())
    return set()


def save_sent_article(link):
    with open(DB_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")


# --- FONCTION IA : ANALYSEUR ---
async def analyze_with_ai(text):
    try:
        prompt = (
            "Analyse cet article de cybersécurité et donne-moi un résumé "
            "ultra-concis (2 phrases max) avec l'impact réel et le niveau "
            "de danger (Critique/Haut/Moyen). Sois technique et direct. "
            f"Texte: {text}"
        )
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Analyse IA indisponible : {e}"


# --- COMMANDES PRÉCISES ---

# 1. /radar : Scan des failles CVE critiques
async def radar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎯 *Lancement du Radar CVE...* Recherche de failles critiques en cours.")
    feed = feedparser.parse(SOURCES["CVE_CRITICAL"])
    found = 0
    for entry in feed.entries[:10]:
        if "CRITICAL" in entry.title.upper() or "HIGH" in entry.title.upper():
            msg = f"⚠️ *FAILLE DÉTECTÉE* ⚠️\n\n📛 *{entry.title}*\n\n🔗 [Détails NIST]({entry.link})"
            await update.message.reply_text(msg, parse_mode="Markdown")
            found += 1
    if found == 0:
        await update.message.reply_text("✅ Aucune faille critique immédiate détectée dans le flux NIST.")


# 2. /brief : Résumé IA des dernières news
async def brief_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🧠 *L'IA analyse les dernières news...* Patientez.")
    feed = feedparser.parse(SOURCES["NEWS_EN"])
    top_article = feed.entries[0]
    summary = await analyze_with_ai(top_article.title + " " + top_article.summary)
    msg = f"💎 *BRIEFING IA* 💎\n\n📰 *{top_article.title}*\n\n🤖 *Analyse :* {summary}\n\n🔗 [Source]({top_article.link})"
    await update.message.reply_text(msg, parse_mode="Markdown")


# 3. /info : Scan classique FR/EN
async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scan classique lancé...")
    sent_articles = load_sent_articles()
    for name, url in SOURCES.items():
        if "CVE" in name:
            continue  # On ignore les CVE ici
        feed = feedparser.parse(url)
        for entry in feed.entries[:3]:
            if entry.link not in sent_articles:
                msg = f"🚨 *NEWS CYBER* 🚨\n\n📰 *{entry.title}*\n\n🔗 [Lire]({entry.link})"
                await update.message.reply_text(msg, parse_mode="Markdown")
                save_sent_article(entry.link)
    await update.message.reply_text("✅ Terminé.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🌐 *SentineL V3 - Intelligence Cyber*\n\n"
        "👉 /radar : Scan des failles CVE critiques (Technique)\n"
        "👉 /brief : Analyse IA de la news majeure (Résumé)\n"
        "👉 /info : Flux classique FR/EN\n"
        "👉 /start : Menu"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


# --- SCAN AUTOMATIQUE (planificateur) ---
async def scheduled_scan(context: ContextTypes.DEFAULT_TYPE):
    sent_articles = load_sent_articles()
    for name, url in SOURCES.items():
        if "CVE" in name:
            continue
        feed = feedparser.parse(url)
        for entry in feed.entries[:3]:
            if entry.link not in sent_articles:
                msg = f"🚨 *NEWS CYBER* 🚨\n\n📰 *{entry.title}*\n\n🔗 [Lire]({entry.link})"
                await context.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
                save_sent_article(entry.link)
                sent_articles.add(entry.link)


if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.start()

    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("radar", radar_command))
    application.add_handler(CommandHandler("brief", brief_command))
    application.add_handler(CommandHandler("info", info_command))

    # Auto-scan toutes les 6h
    application.job_queue.run_repeating(scheduled_scan, interval=21600, first=10)

    print("SentineL V3 Lancé avec IA !")
    application.run_polling()
