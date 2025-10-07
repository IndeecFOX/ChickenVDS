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
NOTIFY_THREAD_ID = "12130"  # ID потока для уведомлений о безлимитных тарифах
API_URL = "https://hostvds.com/api/regions/"

CITY_FLAGS = {
    "Hong-kong": "🇭🇰"    ,
    "Hel": "🇫🇮"    ,
    "Kansas": "🇺🇸"    ,
    "Paris": "🇫🇷"    ,
    "Amsterdam": "🇳🇱"    ,
    "Silicon-valley": "🇺🇸"    ,
    "Dallas": "🇺🇸"    ,
    "Del": "🇮🇳"    ,
    "Riga": "🇱🇻"
}

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

async def fetch_plans(session, region_code):
    """Получает список тарифов для указанного региона."""
    async with session.get(f"https://hostvds.com/api/plans/?region={region_code}") as response:
        return await response.json()

async def fetch_regions():
    """Получает список доступных регионов и проверяет наличие тарифов."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(API_URL) as response:
                data = await response.json()

            available_locations = {}
            has_unlimited = False  # Флаг наличия безлимитных тарифов

            for region in data:
                # Проверяем доступность региона
                if region.get("is_available") and not region.get("is_out_of_stock"):
                    region_code = region['region']
                    plans_data = await fetch_plans(session, region_code)

                    city_name = region['city_code'].capitalize()
                    flag = CITY_FLAGS.get(city_name, '')

                    # Собираем тарифы
                    price_lines = []
                    target_prices = [0.99, 1.99, 3.99]
                    has_available_plans = False
                    has_highfreq_shared_available = False

                    standard_plans = []
                    highfreq_shared_plans = []

                    for price in target_prices:
                        for kind in ["standard", "highfreq_shared"]:
                            matching_plan = next(
                                (plan for plan in plans_data if plan.get("monthly") == price and plan.get("kind") == kind),
                                None
                            )
                            if matching_plan:
                                status = "✅" if not matching_plan.get("is_out_of_stock") else "❌"
                                currency_symbol = "€" if city_name == "Kansas" else "$"
                                price_line = f"{currency_symbol}{price}/мес {status}"
                                if kind == "standard":
                                    standard_plans.append(price_line)
                                    has_available_plans = has_available_plans or status == "✅"
                                elif kind == "highfreq_shared":
                                    highfreq_shared_plans.append(price_line)
                                    if status == "✅":
                                        has_highfreq_shared_available = True
                                        has_unlimited = True  # Устанавливаем флаг наличия безлимитных тарифов

                    if standard_plans:
                        price_lines.extend(standard_plans)
                    if highfreq_shared_plans:
                        price_lines.append("♾️ Unlimited:")
                        price_lines.extend(highfreq_shared_plans)

                    if has_available_plans:
                        location_name = f"{flag} {city_name}"
                        if has_highfreq_shared_available:
                            location_name += " (+Unlimited_HF⭐ ∞)"

                        available_locations[location_name] = price_lines

            return available_locations, has_unlimited
        except Exception as e:
            print(f"Ошибка при получении данных: {e}")
            return {}, False

async def check_servers():
    """Основной цикл проверки серверов и отправки уведомлений."""
    previous_locations = {}
    has_unlimited_previous = False

    # Стартовое сообщение в чат
    await bot.send_message(
        chat_id=CHAT_ID,
        message_thread_id=THREAD_ID,
        text="Бот перезагружен. Fix канала уведомлений о безлимите (10.02). Created by: bank. With code support by: Fatyzzz."
    )

    # Стартовое сообщение в канал
    if CHANNEL_ID:
        await bot.send_message(CHANNEL_ID, "Made by Fatyzzz for Z4R. Интервал проверки: 2 минуты")

    while True:
        try:
            current_locations, has_unlimited = await fetch_regions()
            if current_locations != previous_locations:
                previous_locations = current_locations
                if current_locations:
                    message = "🌎 Доступные локации:\n\n"
                    for location, prices in current_locations.items():
                        has_available = any("✅" in price for price in prices)
                        status_circle = " " if has_available else "🔴"
                        message += f"{location} {status_circle}\n"

                    message += "\n💵 Наличие недорогих тарифов:\n<blockquote expandable>"
                    for location, prices in current_locations.items():
                        message += f"\n{location}\n{chr(8226)} " + f"\n{chr(8226)} ".join(prices) + "\n"
                    message += "</blockquote>"
                else:
                    message = "Нет доступных серверов или сайт недоступен (Возможно под защитой от DDOS)."

                await bot.send_message(
                    chat_id=CHAT_ID,
                    message_thread_id=THREAD_ID,
                    text=message,
                    parse_mode=ParseMode.HTML
                )

                if CHANNEL_ID:
                    await bot.send_message(
                        chat_id=CHANNEL_ID,
                        text=message,
                        parse_mode=ParseMode.HTML
                    )

            if has_unlimited and not has_unlimited_previous:
                await bot.send_message(
                    chat_id=CHAT_ID,
                    message_thread_id=NOTIFY_THREAD_ID,
                    text="Есть безлимит!"
                )
            has_unlimited_previous = has_unlimited

            await asyncio.sleep(60)
        except Exception as e:
            print(f"Ошибка в основном цикле: {e}")
            await asyncio.sleep(5)

async def main():
    await check_servers()

if __name__ == "__main__":
    asyncio.run(main())
