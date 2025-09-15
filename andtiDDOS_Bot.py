import asyncio
import json
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from playwright.async_api import async_playwright
import aiohttp
import time

# --- Конфиг ---
TOKEN = "TOKEN"
CHAT_ID = "-1002377841002"
CHANNEL_ID = "-1002424283274"
THREAD_ID = "769"
NOTIFY_THREAD_ID = "12130"
API_URL = "https://hostvds.com/api/regions/"

CITY_FLAGS = {
    "Hong-kong": "🇭🇰",
    "Hel": "🇫🇮",
    "Kansas": "🇺🇸",
    "Paris": "🇫🇷",
    "Amsterdam": "🇳🇱",
    "Silicon-valley": "🇺🇸",
    "Dallas": "🇺🇸",
    "Del": "🇮🇳"
}

bot = Bot(token=TOKEN)
dp = Dispatcher()


# --- 1. Получаем cookies и заголовки через Playwright ---
async def get_cookies_and_headers():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://hostvds.com/", wait_until="networkidle")
        await asyncio.sleep(6)

        cookies = await context.cookies()
        ua = await page.evaluate("() => navigator.userAgent")
        await browser.close()

        cookies_dict = {c["name"]: c["value"] for c in cookies}
        headers = {"User-Agent": ua}

        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ✅ Cookies обновлены")
        return cookies_dict, headers


# --- 2. Получение тарифов ---
async def fetch_plans(session, region_code):
    async with session.get(f"https://hostvds.com/api/plans/?region={region_code}") as response:
        return await response.json()


async def fetch_regions(session, cookies_headers_holder):
    try:
        async with session.get(API_URL) as response:
            content_type = response.headers.get("Content-Type", "")
            text = await response.text()

            if "application/json" not in content_type:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ Получен HTML вместо JSON! Обновляю cookies...")
                # аварийное обновление cookies
                cookies, headers = await get_cookies_and_headers()
                cookies_headers_holder["cookies"] = cookies
                cookies_headers_holder["headers"] = headers
                return {}, False

            data = json.loads(text)

        available_locations = {}
        has_unlimited = False

        for region in data:
            if region.get("is_available") and not region.get("is_out_of_stock"):
                region_code = region['region']
                plans_data = await fetch_plans(session, region_code)

                city_name = region['city_code'].capitalize()
                flag = CITY_FLAGS.get(city_name, '')

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
                            price_line = f"${price}/мес {status}"
                            if kind == "standard":
                                standard_plans.append(price_line)
                                has_available_plans = has_available_plans or status == "✅"
                            elif kind == "highfreq_shared":
                                highfreq_shared_plans.append(price_line)
                                if status == "✅":
                                    has_highfreq_shared_available = True
                                    has_unlimited = True

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
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ❌ Ошибка при получении данных: {e}")
        return {}, False


# --- 3. Основной цикл с проверкой изменений ---
async def check_servers(cookies_headers_holder):
    previous_locations = {}
    has_unlimited_previous = False

    await bot.send_message(
        chat_id=CHAT_ID,
        message_thread_id=THREAD_ID,
        text="Бот перезагружен. Проверка раз в 5 минут."
    )

    while True:
        try:
            async with aiohttp.ClientSession(
                cookies=cookies_headers_holder["cookies"],
                headers=cookies_headers_holder["headers"]
            ) as session:

                current_locations, has_unlimited = await fetch_regions(session, cookies_headers_holder)

                # --- Логирование ---
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Проверено — локаций: {len(current_locations)}")

                # --- Проверка изменений ---
                if current_locations != previous_locations:
                    previous_locations = current_locations

                    if current_locations:
                        message = "🌎 Доступные локации:\n\n"
                        for location, prices in current_locations.items():
                            has_available = any("✅" in price for price in prices)
                            status_circle = "" if has_available else "🔴"
                            message += f"{location} {status_circle}\n"

                        message += "\n💵 Наличие недорогих тарифов:\n<blockquote expandable>"
                        for location, prices in current_locations.items():
                            message += f"\n{location}\n• " + "\n• ".join(prices) + "\n"
                        message += "</blockquote>"
                    else:
                        message = "Нет доступных серверов или сайт недоступен (под защитой DDOS)."

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

            await asyncio.sleep(300)
        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Ошибка в основном цикле: {e}")
            await asyncio.sleep(5)


# --- 4. Задача обновления cookies каждые N часов ---
async def refresh_cookies_periodically(interval_hours, cookies_headers_holder):
    while True:
        cookies, headers = await get_cookies_and_headers()
        cookies_headers_holder["cookies"] = cookies
        cookies_headers_holder["headers"] = headers
        await asyncio.sleep(interval_hours * 3600)


# --- main ---
async def main():
    cookies, headers = await get_cookies_and_headers()
    cookies_headers_holder = {"cookies": cookies, "headers": headers}

    # Запускаем обновление cookies в фоне (каждый час)
    asyncio.create_task(refresh_cookies_periodically(1, cookies_headers_holder))

    # Основной цикл проверки серверов
    while True:
        await check_servers(cookies_headers_holder)


if __name__ == "__main__":
    asyncio.run(main())
