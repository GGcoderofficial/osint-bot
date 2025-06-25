# 🕵 OSINT Telegram Bot

Бот для OSINT-анализа: поиск по номеру телефона, никам, IP-адресу, утечкам и фотографиям.

## 📦 Возможности
- /find <ник> — Поиск по соцсетям
- /phone <номер> — Сбор источников по номеру
- /ip <ip> — Геолокация и провайдер IP
- /leak <email/логин> — Проверка на утечки
- /photosearch — Поиск и анализ по фото
- Поддержка EXIF, Google Reverse Image, Bing, Yandex, Imgur

## 🚀 Запуск
```bash
pip install -r requirements.txt
python osintproject.py
