#!/usr/bin/env python3
"""
Скрипт для настройки Google Sheets интеграции
Помогает создать таблицу и настроить доступ
"""

import os
import json
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
import gspread

load_dotenv()

def create_credentials_template():
    """Создать шаблон файла credentials.json"""
    template = {
        "type": "service_account",
        "project_id": "your-project-id",
        "private_key_id": "your-private-key-id",
        "private_key": "-----BEGIN PRIVATE KEY-----\nyour-private-key\n-----END PRIVATE KEY-----\n",
        "client_email": "your-service-account@your-project.iam.gserviceaccount.com",
        "client_id": "your-client-id",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com"
    }
    
    with open('credentials_template.json', 'w', encoding='utf-8') as f:
        json.dump(template, f, indent=2, ensure_ascii=False)
    
    print("✅ Создан шаблон credentials_template.json")

def test_credentials(credentials_file):
    """Тестировать учетные данные Google"""
    try:
        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']
        
        creds = Credentials.from_service_account_file(credentials_file, scopes=scope)
        client = gspread.authorize(creds)
        
        print("✅ Учетные данные Google действительны")
        return client
    except Exception as e:
        print(f"❌ Ошибка проверки учетных данных: {e}")
        return None

def create_spreadsheet(client, title="Система учета проблем"):
    """Создать новую таблицу Google Sheets"""
    try:
        spreadsheet = client.create(title)
        print(f"✅ Создана таблица: {title}")
        print(f"📋 ID таблицы: {spreadsheet.id}")
        print(f"🔗 Ссылка: https://docs.google.com/spreadsheets/d/{spreadsheet.id}")
        
        # Настраиваем первый лист
        worksheet = spreadsheet.sheet1
        worksheet.update_title("Заявки")
        
        # Добавляем заголовки
        headers = [
            'Дата', 'Время', 'Корпус', 'Этаж', 'Тип помещения', 
            'Номер', 'Проблема', 'Описание', 'Статус'
        ]
        worksheet.insert_row(headers, 1)
        
        # Форматируем заголовки
        worksheet.format('A1:I1', {
            'backgroundColor': {'red': 0.2, 'green': 0.4, 'blue': 0.9},
            'textFormat': {'foregroundColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0}, 'bold': True}
        })
        
        print("✅ Заголовки добавлены и отформатированы")
        
        return spreadsheet
    except Exception as e:
        print(f"❌ Ошибка создания таблицы: {e}")
        return None

def setup_permissions(spreadsheet, email=None):
    """Настроить права доступа к таблице"""
    try:
        if email:
            # Предоставляем доступ конкретному email
            spreadsheet.share(email, perm_type='user', role='writer')
            print(f"✅ Предоставлен доступ для {email}")
        else:
            # Делаем таблицу доступной по ссылке (только для чтения)
            spreadsheet.share('', perm_type='anyone', role='reader')
            print("✅ Таблица доступна всем по ссылке (только чтение)")
    except Exception as e:
        print(f"❌ Ошибка настройки прав доступа: {e}")

def add_sample_data(worksheet):
    """Добавить примеры данных"""
    sample_data = [
        ['01.01.2024', '10:30:00', 'A', '02', 'WC', '001', '🧼 Закончилось мыло', 'В дозаторе нет мыла', 'Новая'],
        ['01.01.2024', '11:15:00', 'B', '03', 'OFFICE', '205', '💡 Проблемы с электричеством', 'Не работает освещение', 'В работе'],
        ['01.01.2024', '14:20:00', 'A', '01', 'KITCHEN', '101', '🧽 Прибраться', 'Требуется уборка после мероприятия', 'Выполнена']
    ]
    
    for i, row in enumerate(sample_data, 2):
        worksheet.insert_row(row, i)
    
    print("✅ Добавлены примеры данных")

def main():
    print("📊 Настройка Google Sheets для системы учета проблем")
    print("=" * 60)
    
    # Проверяем наличие файла учетных данных
    credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
    
    if not os.path.exists(credentials_file):
        print(f"❌ Файл {credentials_file} не найден")
        print("\n📝 Для настройки Google Sheets API:")
        print("1. Перейдите в Google Cloud Console: https://console.cloud.google.com/")
        print("2. Создайте новый проект или выберите существующий")
        print("3. Включите Google Sheets API и Google Drive API")
        print("4. Создайте Service Account")
        print("5. Скачайте JSON файл с ключами и сохраните как credentials.json")
        print()
        
        create_template = input("Создать шаблон credentials.json? (y/n): ").lower().strip()
        if create_template == 'y':
            create_credentials_template()
            print(f"\n📝 Заполните credentials_template.json своими данными и переименуйте в {credentials_file}")
        
        return
    
    # Тестируем учетные данные
    print(f"\n1. Проверяем файл {credentials_file}...")
    client = test_credentials(credentials_file)
    
    if not client:
        return
    
    # Проверяем существующую таблицу
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    
    if sheet_id:
        print(f"\n2. Проверяем существующую таблицу {sheet_id}...")
        try:
            spreadsheet = client.open_by_key(sheet_id)
            print(f"✅ Таблица найдена: {spreadsheet.title}")
            print(f"🔗 Ссылка: https://docs.google.com/spreadsheets/d/{sheet_id}")
            
            use_existing = input("Использовать существующую таблицу? (y/n): ").lower().strip()
            if use_existing != 'y':
                sheet_id = None
        except Exception as e:
            print(f"❌ Ошибка доступа к таблице: {e}")
            sheet_id = None
    
    # Создаем новую таблицу если нужно
    if not sheet_id:
        print("\n3. Создаем новую таблицу...")
        title = input("Введите название таблицы (по умолчанию: Система учета проблем): ").strip()
        if not title:
            title = "Система учета проблем"
        
        spreadsheet = create_spreadsheet(client, title)
        if not spreadsheet:
            return
        
        sheet_id = spreadsheet.id
        
        # Настраиваем права доступа
        print("\n4. Настраиваем права доступа...")
        email = input("Введите email для предоставления доступа (или Enter для пропуска): ").strip()
        setup_permissions(spreadsheet, email if email else None)
        
        # Добавляем примеры данных
        add_sample = input("Добавить примеры данных? (y/n): ").lower().strip()
        if add_sample == 'y':
            add_sample_data(spreadsheet.sheet1)
    
    # Обновляем .env файл
    print("\n5. Обновляем конфигурацию...")
    env_file = ".env"
    env_content = []
    
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            env_content = f.readlines()
    
    # Обновляем или добавляем GOOGLE_SHEET_ID
    sheet_id_updated = False
    
    for i, line in enumerate(env_content):
        if line.startswith('GOOGLE_SHEET_ID='):
            env_content[i] = f"GOOGLE_SHEET_ID={sheet_id}\n"
            sheet_id_updated = True
            break
    
    if not sheet_id_updated:
        env_content.append(f"GOOGLE_SHEET_ID={sheet_id}\n")
    
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(env_content)
    
    print(f"✅ ID таблицы сохранен в {env_file}")
    
    # Выводим итоговую конфигурацию
    print("\n" + "=" * 60)
    print("🎉 Настройка Google Sheets завершена!")
    print("=" * 60)
    print(f"GOOGLE_SHEET_ID={sheet_id}")
    print(f"GOOGLE_CREDENTIALS_FILE={credentials_file}")
    print("=" * 60)
    
    print("\n📝 Дальнейшие шаги:")
    print("1. Убедитесь, что Telegram бот настроен")
    print("2. Запустите приложение: python app.py")
    print("3. Протестируйте отправку заявки")

if __name__ == "__main__":
    main()