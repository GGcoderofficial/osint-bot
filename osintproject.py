import logging
import aiohttp
import asyncio
import os
import base64
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = "8190327180:AAGxOddgXrfFwIqRi9bR92SJOHg5dChFBbk"
IMGUR_CLIENT_ID = "d73b264a5e45f7f"

# Логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    filename="osint_bot.log",
    filemode="a",
)
logger = logging.getLogger(__name__)

# 📄 Справка /help
COMMANDS = {
    "start": "Показать приветствие",
    "help": "Показать это меню помощи",
    "find <ник>": "Поиск профиля по нику (в соцсетях)",
    "phone <номер>": "Поиск по номеру телефона",
    "ip <IP-адрес>": "Пробив по IP (геолокация, провайдер)",
    "📷 Отправь фото (как документ)":
        "Показать EXIF и сделать реверсивный поиск по изображению"
}


# 📌 /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я OSINT-бот. Используй /help, чтобы посмотреть команды."
    )


# 📌 /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "🛠 Доступные команды:\n\n"
    for cmd, desc in COMMANDS.items():
        msg += f"🔹 /{cmd} — {desc}\n"
    await update.message.reply_text(msg)


# 📌 /find <username>
async def check_username(username: str) -> list:
    services = {
        "Instagram": f"https://www.instagram.com/{username}",
        "Reddit": f"https://www.reddit.com/user/{username}",
        "TikTok": f"https://www.tiktok.com/@{username}",
        "Telegram": f"https://t.me/{username}",
        "VK": f"https://vk.com/{username}",
        "Steam": f"https://steamcommunity.com/id/{username}",
        "GitHub": f"https://github.com/{username}",
        "Twitter": f"https://x.com/{username}",
    }

    found = []
    async with aiohttp.ClientSession() as session:
        for name, url in services.items():
            try:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        found.append(f"🔗 {name}: {url}")
            except:
                continue
    return found


async def find_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ Пример: /find johndoe")
        return
    username = context.args[0]
    await update.message.reply_text(f"🔍 Ищу {username}...")
    results = await check_username(username)
    if results:
        await update.message.reply_text("✅ Найдено:\n" + "\n".join(results))
    else:
        await update.message.reply_text("❌ Ничего не найдено.")


# 📌 /phone <номер>
async def search_phone_sources(phone: str) -> list:
    return [
        f"🔎 Google: https://www.google.com/search?q={phone}",
        f"🟡 Yandex: https://yandex.kz/search/?text={phone}",
        f"📞 WhoCalledMe: https://whocalledme.io/number/{phone}",
        f"📱 Telegram: https://t.me/{phone}",
        f"🔍 Truecaller: https://www.truecaller.com/search/kz/{phone}",
        f"👥 GetContact: https://api.getcontact.com/lookup?phone={phone} (если доступно)",
        f"💬 Поиск по форумам: https://rutracker.org/forum/search_cse.php?q={phone}",
    ]


async def search_by_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ Пример: /phone 87071234567")
        return
    phone = context.args[0]
    await update.message.reply_text(f"🔍 Ищу по номеру {phone}...")
    results = await search_phone_sources(phone)
    await update.message.reply_text("📊 Результаты:\n" + "\n".join(results))


# 📌 /ip <адрес>
async def check_ip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ Пример: /ip 8.8.8.8")
        return

    ip = context.args[0]
    await update.message.reply_text(f"🌐 Пробиваю IP: {ip}...")

    url = f"http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,isp,org,as,query"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                if data["status"] == "fail":
                    await update.message.reply_text(f"❌ Ошибка: {data.get('message', 'неизвестная ошибка')}")
                    return

                result = (
                    f"🌍 IP: {data['query']}\n"
                    f"📍 Страна: {data['country']}\n"
                    f"🏙️ Регион: {data['regionName']}\n"
                    f"🏡 Город: {data['city']}\n"
                    f"📡 ISP: {data['isp']}\n"
                    f"🏢 Организация: {data['org']}\n"
                    f"🔎 AS: {data['as']}"
                )
                await update.message.reply_text(result)
    except Exception as e:
        logger.error(f"[IP ERROR] {e}")
        await update.message.reply_text("⚠️ Ошибка при запросе IP-API.")


# 📷 Обработка фото (EXIF + поиск по изображению)
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        file = update.message.document or update.message.photo[-1]
        if not file:
            await update.message.reply_text("❗ Пожалуйста, отправь изображение как *фото* или *документ*.")
            return

        file_id = file.file_id
        new_file = await context.bot.get_file(file_id)
        local_path = f"photo_{file_id}.jpg"
        await new_file.download_to_drive(local_path)

        # --- EXIF
        exif_result = "📷 EXIF-данные:\n"
        try:
            image = Image.open(local_path)
            exif_data = image._getexif()

            if exif_data:
                parsed = {TAGS.get(tag_id, tag_id): value for tag_id, value in exif_data.items()}
                gps_info = parsed.get("GPSInfo")

                if gps_info:
                    gps_data = {GPSTAGS.get(t, t): gps_info[t] for t in gps_info}

                    def to_degrees(val):
                        d, m, s = val
                        return d[0]/d[1] + m[0]/m[1]/60 + s[0]/s[1]/3600

                    lat = to_degrees(gps_data["GPSLatitude"])
                    if gps_data.get("GPSLatitudeRef") != "N":
                        lat = -lat
                    lon = to_degrees(gps_data["GPSLongitude"])
                    if gps_data.get("GPSLongitudeRef") != "E":
                        lon = -lon

                    exif_result += f"📍 Координаты: {lat:.6f}, {lon:.6f}\n"
                    exif_result += f"🌍 Google Maps: https://maps.google.com/?q={lat},{lon}\n"

                if "DateTimeOriginal" in parsed:
                    exif_result += f"📅 Дата съёмки: {parsed['DateTimeOriginal']}\n"
                if "Model" in parsed:
                    exif_result += f"📱 Устройство: {parsed['Model']}\n"
            else:
                exif_result += "❌ В фото не найдено EXIF-данных.\n"

        except Exception as exif_err:
            logger.error(f"[EXIF ERROR] {exif_err}")
            exif_result += "⚠️ Ошибка при разборе EXIF.\n"

        await update.message.reply_text(exif_result.strip())

        # --- Imgur Upload
        headers = {"Authorization": f"Client-ID {IMGUR_CLIENT_ID}"}
        with open(local_path, "rb") as f:
            img_data = base64.b64encode(f.read())

        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.imgur.com/3/upload", headers=headers, data={"image": img_data}) as resp:
                data = await resp.json()

        if data.get("success"):
            imgur_link = data["data"]["link"]
            rev_search = (
                f"🔍 Реверсивный поиск по изображению:\n"
                f"🟢 Google: https://www.google.com/searchbyimage?image_url={imgur_link}\n"
                f"🔵 Yandex: https://yandex.kz/images/search?rpt=imageview&url={imgur_link}\n"
                f"🟡 Bing: https://www.bing.com/images/search?q=imgurl:{imgur_link}&view=detailv2\n"
                f"📎 Ссылка на файл: {imgur_link}"
            )
            await update.message.reply_text(rev_search)
        else:
            await update.message.reply_text("❌ Не удалось загрузить фото на Imgur.")
            logger.warning(f"[IMGUR ERROR] Ответ: {data}")

    except Exception as e:
        await update.message.reply_text("❌ Не удалось обработать фото.")
        logger.error(f"[PHOTO ERROR] {e}")
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)


# 📌 Ошибки
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Ошибка:", exc_info=context.error)
    if update and isinstance(update, Update) and update.message:
        await update.message.reply_text("❌ Что-то пошло не так, но я живой 🙂")


# 🔁 Запуск
def run_bot():
    print("🚀 OSINT-бот запускается...")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("find", find_user))
    app.add_handler(CommandHandler("phone", search_by_phone))
    app.add_handler(CommandHandler("ip", check_ip))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_photo))
    app.add_error_handler(error_handler)

    loop = asyncio.get_event_loop()
    loop.create_task(app.run_polling())
    print("✅ OSINT-бот запущен и ждёт команды...")
    loop.run_forever()


if __name__ == "__main__":
    try:
        run_bot()
    except Exception as e:
        logger.critical(f"❌ Критическая ошибка: {e}")
