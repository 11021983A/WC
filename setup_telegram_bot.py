#!/usr/bin/env python3
"""
Скрипт для настройки Telegram бота
Помогает получить chat_id и проверить работу бота
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

def get_bot_info(token):
    """Получить информацию о боте"""
    url = f"https://api.telegram.org/bot{token}/getMe"
    response = requests.get(url)
    return response.json()

def get_updates(token):
    """Получить обновления (сообщения) бота"""
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    response = requests.get(url)
    return response.json()

def send_test_message(token, chat_id):
    """Отправить тестовое сообщение"""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': '🤖 Тестовое сообщение от системы учета проблем!\n\nБот настроен правильно!',
        'parse_mode': 'HTML'
    }
    response = requests.post(url, data=data)
    return response.json()

def main():
    print("🔧 Настройка Telegram бота для системы учета проблем")
    print("=" * 60)
    
    # Получаем токен
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        token = input("Введите токен бота (получите у @BotFather): ").strip()
    
    if not token:
        print("❌ Токен не указан!")
        return
    
    # Проверяем бота
    print("\n1. Проверяем бота...")
    bot_info = get_bot_info(token)
    
    if not bot_info.get('ok'):
        print(f"❌ Ошибка: {bot_info.get('description', 'Неизвестная ошибка')}")
        return
    
    bot_data = bot_info['result']
    print(f"✅ Бот найден: @{bot_data['username']} ({bot_data['first_name']})")
    
    # Получаем обновления
    print("\n2. Получаем chat_id...")
    print("📱 Отправьте любое сообщение боту в Telegram, затем нажмите Enter")
    input("Нажмите Enter после отправки сообщения боту...")
    
    updates = get_updates(token)
    
    if not updates.get('ok') or not updates.get('result'):
        print("❌ Не удалось получить сообщения. Убедитесь, что вы отправили сообщение боту.")
        return
    
    # Извлекаем chat_id из последнего сообщения
    chat_ids = set()
    for update in updates['result']:
        if 'message' in update and 'chat' in update['message']:
            chat_id = update['message']['chat']['id']
            chat_type = update['message']['chat']['type']
            chat_title = update['message']['chat'].get('title', 'Личный чат')
            chat_ids.add((chat_id, chat_type, chat_title))
    
    if not chat_ids:
        print("❌ Не найдено сообщений с chat_id")
        return
    
    print("\n📋 Найденные чаты:")
    for i, (chat_id, chat_type, title) in enumerate(chat_ids, 1):
        print(f"{i}. ID: {chat_id} | Тип: {chat_type} | Название: {title}")
    
    # Выбираем chat_id
    if len(chat_ids) == 1:
        selected_chat_id = list(chat_ids)[0][0]
        print(f"\n✅ Автоматически выбран chat_id: {selected_chat_id}")
    else:
        try:
            choice = int(input("\nВыберите номер чата: ")) - 1
            selected_chat_id = list(chat_ids)[choice][0]
        except (ValueError, IndexError):
            print("❌ Неверный выбор")
            return
    
    # Тестируем отправку сообщения
    print(f"\n3. Тестируем отправку сообщения в чат {selected_chat_id}...")
    test_result = send_test_message(token, selected_chat_id)
    
    if test_result.get('ok'):
        print("✅ Тестовое сообщение отправлено успешно!")
    else:
        print(f"❌ Ошибка отправки: {test_result.get('description')}")
        return
    
    # Выводим конфигурацию
    print("\n" + "=" * 60)
    print("🎉 Настройка завершена! Добавьте в файл .env:")
    print("=" * 60)
    print(f"TELEGRAM_BOT_TOKEN={token}")
    print(f"TELEGRAM_CHAT_ID={selected_chat_id}")
    print("=" * 60)
    
    # Создаем/обновляем .env файл
    env_file = ".env"
    env_content = []
    
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            env_content = f.readlines()
    
    # Обновляем или добавляем переменные
    token_updated = False
    chat_id_updated = False
    
    for i, line in enumerate(env_content):
        if line.startswith('TELEGRAM_BOT_TOKEN='):
            env_content[i] = f"TELEGRAM_BOT_TOKEN={token}\n"
            token_updated = True
        elif line.startswith('TELEGRAM_CHAT_ID='):
            env_content[i] = f"TELEGRAM_CHAT_ID={selected_chat_id}\n"
            chat_id_updated = True
    
    if not token_updated:
        env_content.append(f"TELEGRAM_BOT_TOKEN={token}\n")
    if not chat_id_updated:
        env_content.append(f"TELEGRAM_CHAT_ID={selected_chat_id}\n")
    
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(env_content)
    
    print(f"✅ Конфигурация сохранена в {env_file}")
    
    print("\n📝 Дальнейшие шаги:")
    print("1. Настройте Google Sheets (запустите setup_google_sheets.py)")
    print("2. Запустите приложение: python app.py")
    print("3. Сгенерируйте QR-коды: откройте /admin/qr_codes")

if __name__ == "__main__":
    main()