import aiohttp
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# 🔹 Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("✅ /start вызван")
    await update.message.reply_text("Наргызик вкусненьки котенак")

# 🔹 Команда /cat
async def send_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("📷 /cat вызван")
    url = "https://cataas.com/cat"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                photo = await resp.read()
                await update.message.reply_photo(photo)
            else:
                await update.message.reply_text("Не удалось загрузить котика 😿")

# 🔹 Запуск
app = ApplicationBuilder().token("7408748272:AAFB5VSX7Ai-InH4McLdTIVZP6nwBojbCY4").build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("cat", send_cat))

print("🚀 Бот запущен")
app.run_polling()
