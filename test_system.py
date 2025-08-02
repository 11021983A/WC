#!/usr/bin/env python3
"""
Скрипт для тестирования системы учета проблем
Проверяет все компоненты: Telegram, Google Sheets, QR-коды
"""

import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def test_telegram():
    """Тестирование Telegram бота"""
    print("🤖 Тестирование Telegram бота...")
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("❌ Не настроены TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID")
        return False
    
    try:
        # Проверяем бота
        url = f"https://api.telegram.org/bot{token}/getMe"
        response = requests.get(url, timeout=10)
        bot_info = response.json()
        
        if not bot_info.get('ok'):
            print(f"❌ Ошибка получения информации о боте: {bot_info.get('description')}")
            return False
        
        bot_data = bot_info['result']
        print(f"✅ Бот найден: @{bot_data['username']}")
        
        # Отправляем тестовое сообщение
        message = f"""
🧪 <b>Тестовое сообщение системы учета проблем</b>

📍 <b>Помещение:</b> Корпус A, 02 этаж, WC №001
🔧 <b>Проблема:</b> 🧼 Закончилось мыло
📝 <b>Описание:</b> Тестовая заявка для проверки системы
📅 <b>Дата:</b> {datetime.now().strftime('%d.%m.%Y')}
🕐 <b>Время:</b> {datetime.now().strftime('%H:%M:%S')}

#тест #помещение001
        """.strip()
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, data=data, timeout=10)
        result = response.json()
        
        if result.get('ok'):
            print("✅ Тестовое сообщение отправлено в Telegram")
            return True
        else:
            print(f"❌ Ошибка отправки сообщения: {result.get('description')}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка тестирования Telegram: {e}")
        return False

def test_google_sheets():
    """Тестирование Google Sheets"""
    print("\n📊 Тестирование Google Sheets...")
    
    credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    
    if not os.path.exists(credentials_file):
        print(f"❌ Файл {credentials_file} не найден")
        return False
    
    if not sheet_id:
        print("❌ Не настроен GOOGLE_SHEET_ID")
        return False
    
    try:
        from google.oauth2.service_account import Credentials
        import gspread
        
        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']
        
        creds = Credentials.from_service_account_file(credentials_file, scopes=scope)
        client = gspread.authorize(creds)
        
        # Открываем таблицу
        sheet = client.open_by_key(sheet_id)
        worksheet = sheet.sheet1
        
        print(f"✅ Подключение к таблице: {sheet.title}")
        
        # Добавляем тестовую запись
        test_row = [
            datetime.now().strftime('%d.%m.%Y'),
            datetime.now().strftime('%H:%M:%S'),
            'A',
            '02',
            'WC',
            '001',
            '🧼 Закончилось мыло',
            'Тестовая заявка для проверки системы',
            'Тест'
        ]
        
        worksheet.insert_row(test_row, 2)
        print("✅ Тестовая запись добавлена в Google Sheets")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования Google Sheets: {e}")
        return False

def test_qr_generation():
    """Тестирование генерации QR-кодов"""
    print("\n🔗 Тестирование генерации QR-кодов...")
    
    try:
        import qrcode
        from io import BytesIO
        import base64
        
        base_url = os.getenv('BASE_URL', 'https://example.com')
        room_number = 1
        url = f"{base_url}/room/{room_number}"
        
        # Создание QR-кода
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        # Создание изображения
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Сохранение тестового QR-кода
        img.save('test_qr.png')
        print(f"✅ QR-код сгенерирован для URL: {url}")
        print("✅ Тестовый QR-код сохранен как test_qr.png")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка генерации QR-кода: {e}")
        return False

def test_flask_app():
    """Тестирование Flask приложения"""
    print("\n🌐 Тестирование Flask приложения...")
    
    try:
        # Проверяем, запущено ли приложение
        response = requests.get('http://localhost:5000', timeout=5)
        
        if response.status_code == 200:
            print("✅ Flask приложение доступно на http://localhost:5000")
            
            # Тестируем API генерации QR
            qr_response = requests.get('http://localhost:5000/api/generate_qr/1', timeout=5)
            if qr_response.status_code == 200:
                print("✅ API генерации QR-кодов работает")
            else:
                print("⚠️ API генерации QR-кодов недоступен")
            
            return True
        else:
            print(f"❌ Flask приложение недоступно (код: {response.status_code})")
            return False
            
    except requests.ConnectionError:
        print("❌ Flask приложение не запущено")
        print("💡 Запустите приложение командой: python app.py")
        return False
    except Exception as e:
        print(f"❌ Ошибка тестирования Flask: {e}")
        return False

def main():
    print("🧪 Тестирование системы учета проблем в помещениях")
    print("=" * 60)
    
    results = []
    
    # Тестируем все компоненты
    results.append(("Telegram Bot", test_telegram()))
    results.append(("Google Sheets", test_google_sheets()))
    results.append(("QR Generation", test_qr_generation()))
    results.append(("Flask App", test_flask_app()))
    
    # Выводим результаты
    print("\n" + "=" * 60)
    print("📋 Результаты тестирования:")
    print("=" * 60)
    
    all_passed = True
    for component, passed in results:
        status = "✅ РАБОТАЕТ" if passed else "❌ НЕ РАБОТАЕТ"
        print(f"{component:20} {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("🎉 Все компоненты работают корректно!")
        print("\n📝 Следующие шаги:")
        print("1. Сгенерируйте QR-коды: http://localhost:5000/admin/qr_codes")
        print("2. Протестируйте отправку заявки: http://localhost:5000/room/1")
        print("3. Проверьте Telegram группу и Google Sheets")
    else:
        print("⚠️ Некоторые компоненты требуют настройки")
        print("\n📝 Рекомендации:")
        print("1. Проверьте файл .env")
        print("2. Убедитесь, что все зависимости установлены")
        print("3. Запустите скрипты настройки")
    
    # Очистка тестовых файлов
    if os.path.exists('test_qr.png'):
        os.remove('test_qr.png')
        print("\n🧹 Тестовые файлы удалены")

if __name__ == "__main__":
    main()