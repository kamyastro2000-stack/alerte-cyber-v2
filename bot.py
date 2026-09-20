import os
import logging
import feedparser
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

# --- CONFIGURATION ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

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

# Logs pour voir ce qui se passe sur Render
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


def load_sent_articles():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return set(f.read().splitlines())
    return set()


def save_sent_article(link):
    with open(DB_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")


async def check_for_news(context: ContextTypes.DEFAULT_TYPE):
    print("Scan automatique en cours...")
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
                        title = entry.title
                        msg = (
                            f"{emoji_lang} *ALERTE CYBER {lang}* 🚨\n\n"
                            f"📰 *{title}*\n\n"
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
    await update.message.reply_text("🔍 *Lancement d'un scan manuel...* Patientez quelques secondes.")
    await check_for_news(context)
    await update.message.reply_text("✅ Scan terminé !")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Salut ! Je suis ton Alerte Cyber V2.\n\n"
        "📡 Je t'envoie des news auto.\n"
        "💡 Tape /info pour forcer un scan maintenant !"
    )


if __name__ == "__main__":
    application = ApplicationBuilder().token(TOKEN).build()

    # Commandes
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("info", info_command))

    # Planificateur automatique (toutes les 6 heures)
    job_queue = application.job_queue
    job_queue.run_repeating(check_for_news, interval=6 * 3600, first=10)

    print("Bot démarré...")
    application.run_polling()
