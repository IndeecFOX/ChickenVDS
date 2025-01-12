from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
import asyncio
import aiohttp
import json

# Конфигурация
TOKEN = "TOKEN"
CHAT_ID = "-1002377841002"
CHANNEL_ID = "-1002424283274"
THREAD_ID = "769"
API_URL = "https://hostvds.com/api/regions/"

CITY_FLAGS = {
    "Hong-kong": "🇭🇰"  ,
    "Hel": "🇫🇮"  ,
    "Kansas": "🇺🇸"  ,
    "Paris": "🇫🇷"  ,
    "Amsterdam": "🇳🇱"  ,
    "Silicon-valley": "🇺🇸"  ,
    "Dallas": "🇺🇸"
}

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

async def fetch_plans(session, region_code):
    async with session.get(f"https://hostvds.com/api/plans/?region={region_code}") as response:
        return await response.json()

async def fetch_regions():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(API_URL) as response:
                data = await response.json()

            available_locations = {}
            for region in data:
                if not region.get("is_out_of_stock"):
                    region_code = region['region']
                    plans_data = await fetch_plans(session, region_code)

                    city_name = region['city_code'].capitalize()
                    flag = CITY_FLAGS.get(city_name, '')

                    # Собираем все тарифы для этой локации
                    price_lines = []
                    target_prices = [0.99, 1.99, 3.99]
                    has_available_plans = False

                    for price in target_prices:
                        matching_plan = next((plan for plan in plans_data if plan.get("monthly") == price), None)
                        if matching_plan:
                            status = "✅" if not matching_plan.get("is_out_of_stock") else "❌"
                            if status == "✅":
                                has_available_plans = True
                            price_line = f"${price}/мес {status}"
                            price_lines.append(price_line)

                    if has_available_plans:
                        available_locations[f"{flag} {city_name}"] = price_lines

            return available_locations
        except Exception as e:
            print(f"Ошибка при получении данных: {e}")
            return {}

async def check_servers():
    previous_locations = {}

    # Стартовое сообщение в чат
    await bot.send_message(
        chat_id=CHAT_ID,
        message_thread_id=THREAD_ID,
        text="Бот перезагружен. Created by: bank. Upgraded code by Fatyzzz specialy for Z4R."
    )

    # Стартовое сообщение в канал
    if CHANNEL_ID:
        await bot.send_message(CHANNEL_ID, "Made by Fatyzzz for Z4R. Интервал проверки: 2 минуты")

    while True:
        try:
            current_locations = await fetch_regions()
            if current_locations != previous_locations:
                previous_locations = current_locations
                if current_locations:
                    # Формирование сообщения
                    message = "🌎 Доступные локации:\n\n"

                    # Сначала список всех локаций со статусами
                    for location, prices in current_locations.items():
                        has_available = any("✅" in price for price in prices)
                        status_circle = " " if has_available else "🔴"
                        message += f"{location} {status_circle}\n"

                    message += "\n💵 Наличие недорогих тарифов:"
                    # Создаем один расширяемый блок со всеми локациями
                    message += "\n<blockquote expandable>"
                    for location, prices in current_locations.items():
                        message += f"\n{location}\n{chr(8226)} " + f"\n{chr(8226)} ".join(prices) + "\n"
                    message += "</blockquote>"
                else:
                    message = "Нет доступных серверов"

                # Отправка в чат с thread_id
                await bot.send_message(
                    chat_id=CHAT_ID,
                    message_thread_id=THREAD_ID,
                    text=message,
                    parse_mode=ParseMode.HTML
                )

                # Отправка в канал
                if CHANNEL_ID:
                    await bot.send_message(
                        chat_id=CHANNEL_ID,
                        text=message,
                        parse_mode=ParseMode.HTML
                    )

            await asyncio.sleep(120)
        except Exception as e:
            print(f"Ошибка в основном цикле: {e}")
            await asyncio.sleep(5)

async def main():
    await check_servers()

if __name__ == "__main__":
    asyncio.run(main())
