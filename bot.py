import os
import logging
import feedparser
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

# --- CONFIGURATION ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Setup Flask pour empêcher Render d'endormir le bot
app = Flask(__name__)


@app.route('/')
def home():
    return "Le bot Alerte Cyber V2 est en vie ! 🚀"


def run_flask():
    # Render définit le port dynamiquement
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)


# --- LOGIQUE DU BOT ---
SOURCES = {
    "FR": {
        "ANSSI": "https://www.ssi.gouv.fr/actualites/flux-rss/",
        "Cyberveille": "https://cyberveille.fr/feed/",
        "Zataz": "https://www.zataz.com/feed/"
    },
    "EN": {
        "The Hacker News": "https://feeds.feedburner.com/TheHackersNews",
        "BleepingComputer": "https://www.bleepingcomputer.com/feed/",
        "Cybersecurity News": "https://cybersecuritynews.com/feed/",
        "Reddit CyberSecurity": "https://www.reddit.com/r/cybersecurity/.rss",
    }
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


async def check_for_news(context: ContextTypes.DEFAULT_TYPE):
    sent_articles = load_sent_articles()
    count = 0
    for lang, sources in SOURCES.items():
        emoji_lang = "🇫🇷" if lang == "FR" else "🇬🇧"
        for source_name, url in sources.items():
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:3]:
                    link = entry.link
                    if link not in sent_articles:
                        msg = (
                            f"{emoji_lang} *ALERTE CYBER {lang}* 🚨\n\n"
                            f"📰 *{entry.title}*\n\n"
                            f"🔗 [Lire]({link})\n\n"
                            f"🎯 {source_name}"
                        )
                        await context.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
                        save_sent_article(link)
                        sent_articles.add(link)
                        count += 1
            except Exception as e:
                print(f"Erreur {source_name}: {e}")
    print(f"Scan terminé. {count} news envoyées.")


async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scan manuel lancé...")
    await check_for_news(context)
    await update.message.reply_text("✅ Terminé !")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Alerte Cyber V2 active ! Tape /info pour des news.")


if __name__ == "__main__":
    # Lancer Flask dans un thread séparé pour ne pas bloquer le bot
    t = Thread(target=run_flask)
    t.start()

    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("info", info_command))

    job_queue = application.job_queue
    job_queue.run_repeating(check_for_news, interval=21600, first=10)

    print("Bot et serveur web lancés !")
    application.run_polling()
