import time
import threading
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

usd_to_toman = 0
symbol_map = {}

# ✅ مسیر دقیق فایل mapping
def load_symbol_map():
    global symbol_map
    try:
        with open(r"C:\Users\Nepiux\Desktop\endmod_arz\fa_crypto_symbols.txt", "r", encoding="utf-8") as f:
            symbol_map = json.load(f)
    except Exception as e:
        print("❌ Could not load symbol map:", e)
        symbol_map = {}

# 🔍 تبدیل ورودی به آدرس CoinMarketCap (با fallback)
def resolve_symbol(user_input: str) -> str:
    user_input = user_input.strip().lower()
    for cmc_name, aliases in symbol_map.items():
        if user_input == cmc_name.lower() or user_input in [a.lower() for a in aliases]:
            return cmc_name
    # اگر پیدا نشد، خودش رو استفاده کن
    return user_input

# 🟢 گرفتن قیمت تتر از Wallex
def update_usd_price():
    global usd_to_toman
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')

    while True:
        try:
            driver = webdriver.Chrome(options=options)
            driver.get("https://wallex.ir/buy-and-sell/usdt")
            time.sleep(2)
            element = driver.find_element(By.CSS_SELECTOR, 'span[component="span"]')
            usd_to_toman = int(element.text.replace(",", ""))
            print("✅ Updated USDT price:", usd_to_toman)
        except Exception as e:
            print("❌ Error updating USDT price:", e)
        finally:
            driver.quit()
        time.sleep(300)

# 🟣 گرفتن قیمت ارز دیجیتال از CMC
def get_crypto_price(symbol):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')

    driver = webdriver.Chrome(options=options)
    try:
        url = f"https://coinmarketcap.com/currencies/{symbol}/"
        driver.get(url)
        time.sleep(2)
        element = driver.find_element(By.CSS_SELECTOR, 'span[data-test="text-cdp-price-display"]')
        return float(element.text.strip().replace('$', '').replace(',', ''))
    except Exception as e:
        print(f"❌ Error fetching price for {symbol}:", e)
        return None
    finally:
        driver.quit()

# 📩 هندل پیام
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global usd_to_toman

    text = update.message.text.strip()
    if not text.startswith("."):
        return

    parts = text[1:].split()
    if not parts:
        return

    raw_input = parts[0].lower()
    amount = float(parts[1]) if len(parts) > 1 and parts[1].replace('.', '', 1).isdigit() else 1

    symbol = resolve_symbol(raw_input)
    price_usd = get_crypto_price(symbol)
    if price_usd is None or usd_to_toman == 0:
        await update.message.reply_text("❌ Couldn't fetch live price.",
                                        reply_to_message_id=update.message.message_id)
        return

    total_usd = price_usd * amount
    total_toman = int(total_usd * usd_to_toman)

    msg = (
        f"💰 Price of {amount:g} {symbol.upper()}:\n\n"
        f"🇮🇷 Toman: {total_toman:,}\n"
        f"🇺🇸 USD: ${total_usd:,.2f}"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("𝗔𝗗𝗗 𝗧𝗢 𝗚𝗥𝗢𝗨𝗣", url="https://t.me/EndArzBot?startgroup=true")]
    ])

    await update.message.reply_text(msg, reply_markup=keyboard, reply_to_message_id=update.message.message_id)

# 🟢 اجرا
def main():
    load_symbol_map()
    threading.Thread(target=update_usd_price, daemon=True).start()

    app = ApplicationBuilder().token("7585937559:AAGmwXAiIWP7JCGqNJErhqNMjtLfLuEHgw0").build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
