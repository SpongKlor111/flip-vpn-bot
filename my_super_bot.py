import urllib.request
import urllib.parse
import json
import time
import random
import sqlite3

# ВСТАВЬ СВОЙ ТОКЕН
TOKEN = "9193138685:AAE1qJdEnbdd07o0i0fgqokANT293RGZ4Qs"
URL = f"https://api.telegram.org/bot{TOKEN}/"

KEYS_URL = "https://raw.githubusercontent.com/SoliSpirit/SolVPN/main/Protocols/vless.txt"

# --- НАСТРОЙКА БАЗЫ ДАННЫХ ---
conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
conn.commit()

def get_fresh_key():
    try:
        req = urllib.request.Request(KEYS_URL, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=10)
        text = response.read().decode('utf-8')
        lines = [line.strip() for line in text.split('\n') if line.strip().startswith('vless://')]
        if lines:
            return random.choice(lines)
        else:
            return "Ключи не найдены. Попробуйте позже."
    except Exception as e:
        print("Ошибка скачивания ключей:", e)
        return "Ошибка сервера. Попробуйте позже."

def send_message(chat_id, text, reply_markup=None):
    url = URL + "sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    
    data = urllib.parse.urlencode(payload).encode()
    try:
        urllib.request.urlopen(url, data=data)
    except Exception as e:
        print("Ошибка отправки:", e)

# Функция отправки счета (Telegram Stars)
def send_invoice(chat_id):
    url = URL + "sendInvoice"
    # Создаем счет на 50 звезд (цена в копейках/центах для Stars = 1 звезда это 1 цент)
    # В Telegram Stars цена указывается в количестве звезд
    payload = {
        "chat_id": chat_id,
        "title": "Подписка Flip VPN",
        "description": "Доступ к VPN на 1 месяц",
        "payload": "vpn_sub_1month",
        "currency": "XTR",  # XTR - это код валюты Telegram Stars
        "prices": json.dumps([{"label": "Подписка на месяц", "amount": 50}]) # 50 звезд
    }
    data = urllib.parse.urlencode(payload).encode()
    try:
        urllib.request.urlopen(url, data=data)
    except Exception as e:
        print("Ошибка отправки счета:", e)

def answer_callback(callback_id):
    url = URL + "answerCallbackQuery"
    data = urllib.parse.urlencode({"callback_query_id": callback_id}).encode()
    try:
        urllib.request.urlopen(url, data=data)
    except Exception as e:
        print("Ошибка ответа на кнопку:", e)

print("Бот запущен! Жду сообщений...")
last_update_id = 0

while True:
    try:
        url = URL + f"getUpdates?offset={last_update_id + 1}&timeout=10"
        response = urllib.request.urlopen(url)
        data = json.loads(response.read().decode())
        
        if data["ok"]:
            for update in data["result"]:
                last_update_id = update["update_id"]
                
                # Обработка /start и обычных сообщений
                if "message" in update and "text" in update["message"]:
                    chat_id = update["message"]["chat"]["id"]
                    text = update["message"]["text"]
                    
                    if text == "/start":
                        keyboard = {
                            "inline_keyboard": [
                                [{"text": "🔑 Получить бесплатный ключ", "callback_data": "get_key"}],
                                [{"text": "💳 Купить подписку", "callback_data": "buy"}],
                                [{"text": "ℹ️ Помощь", "callback_data": "help"}]
                            ]
                        }
                        send_message(chat_id, "Привет! Это бот Flip VPN.\nТы можешь получить 1 бесплатный тестовый ключ или купить подписку.", reply_markup=keyboard)
                
                # Обработка нажатий на кнопки
                if "callback_query" in update:
                    callback_id = update["callback_query"]["id"]
                    chat_id = update["callback_query"]["message"]["chat"]["id"]
                    data_btn = update["callback_query"]["data"]
                    
                    if data_btn == "get_key":
                        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (chat_id,))
                        user = cursor.fetchone()
                        
                        if user:
                            send_message(chat_id, "❌ Ты уже получал бесплатный ключ.\n\nДля получения нового ключа купи подписку.", reply_markup={"inline_keyboard": [[{"text": "💳 Купить", "callback_data": "buy"}]]})
                        else:
                            send_message(chat_id, "⏳ Ищу свежий ключ, подожди пару секунд...")
                            key = get_fresh_key()
                            cursor.execute("INSERT INTO users (user_id) VALUES (?)", (chat_id,))
                            conn.commit()
                            msg = f"✅ Твой бесплатный ключ:\n`{key}`\n\nСкопируй его и вставь в приложение."
                            send_message(chat_id, msg)
                        
                        answer_callback(callback_id)
                        
                    elif data_btn == "buy":
                        send_invoice(chat_id)
                        answer_callback(callback_id)

                    elif data_btn == "help":
                        send_message(chat_id, "Инструкция:\n1. Скачай v2rayNG или Hiddify.\n2. Скопируй ключ из бота.\n3. Вставь в приложение.\n4. Включи VPN.")
                        answer_callback(callback_id)

                # Обработка успешной оплаты
                if "pre_checkout_query" in update:
                    # Подтверждаем, что можем принять оплату (всегда true для простоты)
                    pre_checkout_id = update["pre_checkout_query"]["id"]
                    url = URL + "answerPreCheckoutQuery"
                    data = urllib.parse.urlencode({"pre_checkout_query_id": pre_checkout_id, "ok": True}).encode()
                    urllib.request.urlopen(url, data=data)

                if "message" in update and "successful_payment" in update["message"]:
                    chat_id = update["message"]["chat"]["id"]
                    send_message(chat_id, "🎉 Оплата прошла успешно! Сейчас выдам ключ.")
                    # Даем ключ (записываем юзера в базу, чтобы обновить ему подписку)
                    key = get_fresh_key()
                    msg = f"✅ Твой оплаченный ключ:\n`{key}`\n\nСкопируй его и вставь в приложение."
                    send_message(chat_id, msg)
                    print(f"Пользователь {chat_id} оплатил подписку!")

    except Exception as e:
        print("Ошибка в цикле:", e)
        time.sleep(3)