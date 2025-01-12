import requests
import asyncio
from telegram import Bot
from telegram.error import TelegramError

# Токен вашего бота
TOKEN = "ЦИФРОБУКВЫБОТА"
# ID чата, куда бот будет отправлять сообщения
CHAT_ID = "88027389"
# ID канала, куда бот будет отправлять сообщения
CHANNEL_ID = "-1002377841002"
# ID треда в канале
THREAD_ID = 769

# URL API для проверки
API_URL = "https://hostvds.com/api/regions/"

# Инициализация Telegram-бота
bot = Bot(token=TOKEN)

async def send_message(chat_id, text, thread_id=None):
    """Асинхронная отправка сообщений в чат или тред."""
    try:
        if thread_id:
            # Отправка сообщения в тред, если thread_id указан
            await bot.send_message(chat_id=chat_id, text=text, message_thread_id=thread_id)
        else:
            # Отправка сообщения в основной чат
            await bot.send_message(chat_id=chat_id, text=text)
        print(f"Сообщение успешно отправлено в chat_id {chat_id}, thread_id {thread_id}: {text}")
    except TelegramError as e:
        print(f"Ошибка при отправке сообщения в chat_id {chat_id}, thread_id {thread_id}: {e}")

async def fetch_regions():
    """Получает данные из API и фильтрует их."""
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        return sorted(
            region["city_code"].capitalize()
            for region in data
            if region.get("is_out_of_stock") is False and region.get("is_available") is True
        )
    except Exception as e:
        print(f"Ошибка при получении данных: {e}")
        return []

async def main():
    """Основной цикл бота."""
    previous_cities = []  # Список для хранения предыдущих данных

    try:
        # Сообщение о запуске бота
        startup_message = "Бот обновлен до новой версии. Интервал проверки сокращен с 5 до 2 минут"
        await send_message(CHAT_ID, startup_message)
        await send_message(CHANNEL_ID, startup_message, THREAD_ID)
        print("Отправлено сообщение о перезапуске бота.")
    except Exception as e:
        print(f"Ошибка при отправке сообщения о запуске: {e}")

    print("Бот запущен и отслеживает изменения...")

    while True:
        try:
            # Получение подходящих городов
            current_cities = await fetch_regions()

            # Проверяем, изменились ли данные
            if current_cities != previous_cities:
                # Если данные изменились, обновляем список и отправляем сообщение
                previous_cities = current_cities
                if current_cities:
                    city_list = "\n".join(current_cities)
                    message = f"Сервера в наличии:\n{city_list}"
                else:
                    message = "Свободные места на всех серверах закончились."

                await send_message(CHAT_ID, message)
                await send_message(CHANNEL_ID, message, THREAD_ID)
                print(f"Сообщение отправлено: {message}")
            else:
                print("Данные не изменились. Сообщение не отправлено.")

            # Задержка перед следующей проверкой (5 минут)
            await asyncio.sleep(120)

        except KeyboardInterrupt:
            print("Работа бота была прервана.")
            break
        except Exception as e:
            print(f"Произошла ошибка: {e}")
            await asyncio.sleep(5)  # Задержка перед повторной попыткой
if __name__ == "__main__":
    # Запуск асинхронного цикла
    asyncio.run(main())
