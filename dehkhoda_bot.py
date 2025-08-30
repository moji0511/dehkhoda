# dehkhoda_bot.py
import os
import logging
import re
import html
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from telegram import ParseMode
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler

# ====== تنظیمات از محیط ======
TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    raise SystemExit("ERROR: TELEGRAM_TOKEN environment variable is not set")

GROUP_TAG = os.environ.get("GROUP_TAG", "@iran9897")
USER_AGENT = os.environ.get("USER_AGENT", "Mozilla/5.0 (compatible)")

# ====== لاگ ======
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def _looks_like_persian_meaning(text: str) -> bool:
    return bool(re.search(r'[\u0600-\u06FF]', text)) and len(text) > 10

def search_dehkhoda(word: str) -> str:
    word = (word or "").strip()
    if not word:
        return "کلمه‌ای برای جستجو داده نشده."

    headers = {"User-Agent": USER_AGENT}
    urls = [
        f"https://www.vajehyab.com/dehkhoda/{quote_plus(word)}",
        f"https://www.vajehyab.com/?q={quote_plus(word)}&pv=dehkhoda",
        f"https://www.loghatnameh.org/{quote_plus(word)}",
    ]

    candidates = []
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=8)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            # تلاش برای المان‌های معمول معنی
            for sel in ['div.meaning', 'div.mean', 'div.definition', 'div.entry', 'div#content', 'article']:
                el = soup.select_one(sel)
                if el:
                    text = el.get_text("\n", strip=True)
                    if _looks_like_persian_meaning(text):
                        candidates.append(text)
            # اگر چیزی نیومد پاراگرافهای معقول را بررسی کن
            for p in soup.find_all(['p', 'div', 'span']):
                t = p.get_text(" ", strip=True)
                if _looks_like_persian_meaning(t):
                    candidates.append(t)
            if candidates:
                # بلندترین نتیجه را انتخاب کن
                candidates = sorted(set(candidates), key=lambda s: len(s), reverse=True)
                return candidates[0][:3000]
        except Exception as e:
            logger.debug("scrape error %s: %s", url, e)
            continue

    return "معنی‌ای در منابع قابل‌دسترسی پیدا نشد."

def start(update, context):
    update.message.reply_text(
        "ربات دهخدا آماده‌ست.\nروش استفاده:\n— روی پیامِ کلمه (مثلاً `آسمان`) ریپلای کن و فقط بنویس `دهخدا`.\n— یا تایپ کن `دهخدا کلمه`"
    )

def handle_message(update, context):
    msg = update.message
    if not msg:
        return
    text = (msg.text or "").strip()
    trigger = "دهخدا"

    # حالت ریپلای + فقط 'دهخدا' یا 'دهخدا <کلمه>'
    if msg.reply_to_message and trigger in text:
        after = text.split(trigger, 1)[1].strip()
        if after:
            query = after.splitlines()[0].strip()
        else:
            # از متن پیامِ ریپلای‌شده استفاده کن
            query = (msg.reply_to_message.text or msg.reply_to_message.caption or "").strip()
            if not query:
                msg.reply_text("لطفاً روی یک پیام متنی ریپلای کن (مثلاً `آسمان`).")
                return
        if len(query.split()) > 6:
            query = query.split()[0]
        meaning = search_dehkhoda(query)
        out = f"🔍 معنی «{html.escape(query)}» در لغت‌نامهٔ دهخدا:\n\n{html.escape(meaning)}\n\nگروه بچه‌های ایرون {GROUP_TAG}"
        try:
            msg.reply_to_message.reply_text(out, parse_mode=ParseMode.HTML)
        except Exception:
            msg.reply_text(out, parse_mode=ParseMode.HTML)
        return

    # حالت بدون ریپلای: 'دهخدا کلمه'
    if text.startswith(trigger):
        after = text[len(trigger):].strip()
        if not after:
            msg.reply_text("برای استفاده: روی پیام کلمه ریپلای کن و `دهخدا` بنویس، یا `دهخدا کلمه` بنویس.")
            return
        query = after.split()[0]
        meaning = search_dehkhoda(query)
        out = f"🔍 معنی «{html.escape(query)}» در لغت‌نامهٔ دهخدا:\n\n{html.escape(meaning)}\n\nگروه بچه‌های ایرون {GROUP_TAG}"
        msg.reply_text(out, parse_mode=ParseMode.HTML)
        return

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & (~Filters.command), handle_message))
    logger.info("Bot is starting...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
