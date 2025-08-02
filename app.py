from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import json
import requests
from datetime import datetime
import logging
from google.oauth2.service_account import Credentials
import gspread
import qrcode
from io import BytesIO
import base64
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Конфигурация
class Config:
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
    GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
    BASE_URL = os.getenv('BASE_URL', 'https://example.com')
    
    # Типы проблем
    PROBLEM_TYPES = {
        'soap': '🧼 Закончилось мыло',
        'paper': '🧻 Закончились бумажные принадлежности',
        'trash': '🗑️ Вынести мусор',
        'cleaning': '🧽 Прибраться',
        'plumbing': '🚰 Проблемы с сантехникой',
        'electricity': '💡 Проблемы с электричеством',
        'heating': '🔥 Проблемы с отоплением',
        'other': '📝 Другая проблема'
    }
    
    # Типы помещений
    ROOM_TYPES = {
        'WC': 'Туалет',
        'KITCHEN': 'Кухня',
        'OFFICE': 'Офис',
        'MEETING': 'Переговорная',
        'STORAGE': 'Склад',
        'CORRIDOR': 'Коридор',
        'LOBBY': 'Холл'
    }

config = Config()

class TelegramBot:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
    
    def send_message(self, message):
        """Отправка сообщения в Telegram"""
        if not self.token or not self.chat_id:
            logger.warning("Telegram credentials not configured")
            return False
            
        url = f"{self.base_url}/sendMessage"
        data = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        try:
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            logger.info("Message sent to Telegram successfully")
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

class GoogleSheetsIntegration:
    def __init__(self, credentials_file, sheet_id):
        self.credentials_file = credentials_file
        self.sheet_id = sheet_id
        self.client = None
        self.worksheet = None
        self._initialize()
    
    def _initialize(self):
        """Инициализация Google Sheets API"""
        try:
            if os.path.exists(self.credentials_file):
                scope = ['https://spreadsheets.google.com/feeds',
                        'https://www.googleapis.com/auth/drive']
                
                creds = Credentials.from_service_account_file(
                    self.credentials_file, scopes=scope)
                self.client = gspread.authorize(creds)
                
                # Открываем таблицу
                sheet = self.client.open_by_key(self.sheet_id)
                self.worksheet = sheet.sheet1
                
                # Создаем заголовки если их нет
                self._setup_headers()
                logger.info("Google Sheets initialized successfully")
            else:
                logger.warning(f"Google credentials file not found: {self.credentials_file}")
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets: {e}")
    
    def _setup_headers(self):
        """Настройка заголовков таблицы"""
        headers = ['Дата', 'Время', 'Корпус', 'Этаж', 'Тип помещения', 
                  'Номер', 'Проблема', 'Описание', 'Статус']
        
        try:
            # Проверяем, есть ли уже заголовки
            existing_headers = self.worksheet.row_values(1)
            if not existing_headers:
                self.worksheet.insert_row(headers, 1)
        except Exception as e:
            logger.error(f"Failed to setup headers: {e}")
    
    def add_request(self, request_data):
        """Добавление заявки в таблицу"""
        if not self.worksheet:
            logger.warning("Google Sheets not initialized")
            return False
            
        try:
            row = [
                request_data['date'],
                request_data['time'],
                request_data['room']['building'],
                request_data['room']['floor'],
                request_data['room']['type'],
                request_data['room']['number'],
                request_data['problem_type'],
                request_data['description'],
                'Новая'
            ]
            
            self.worksheet.insert_row(row, 2)  # Вставляем после заголовков
            logger.info("Request added to Google Sheets successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to add request to Google Sheets: {e}")
            return False

# Инициализация интеграций
telegram_bot = TelegramBot(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
google_sheets = GoogleSheetsIntegration(config.GOOGLE_CREDENTIALS_FILE, config.GOOGLE_SHEET_ID)

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html', 
                         problem_types=config.PROBLEM_TYPES,
                         room_types=config.ROOM_TYPES)

@app.route('/room/<int:room_number>')
def room_form(room_number):
    """Форма для конкретного помещения"""
    # Здесь можно добавить логику получения данных о помещении из БД
    room_data = {
        'building': 'A',
        'floor': '02',
        'type': 'WC',
        'number': str(room_number).zfill(3),
        'name': config.ROOM_TYPES.get('WC', 'Помещение')
    }
    
    return render_template('room_form.html', 
                         room=room_data,
                         problem_types=config.PROBLEM_TYPES)

@app.route('/api/submit_request', methods=['POST'])
def submit_request():
    """API для отправки заявки"""
    try:
        data = request.get_json()
        
        # Валидация данных
        required_fields = ['room', 'problem_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing field: {field}'}), 400
        
        # Подготовка данных заявки
        now = datetime.now()
        request_data = {
            'room': data['room'],
            'problem_type': config.PROBLEM_TYPES.get(data['problem_type'], data['problem_type']),
            'description': data.get('description', ''),
            'date': now.strftime('%d.%m.%Y'),
            'time': now.strftime('%H:%M:%S'),
            'timestamp': now.isoformat()
        }
        
        # Формирование сообщения для Telegram
        room = request_data['room']
        telegram_message = f"""
🚨 <b>Новая заявка на обслуживание</b>

📍 <b>Помещение:</b> Корпус {room['building']}, {room['floor']} этаж, {room['type']} №{room['number']}
🔧 <b>Проблема:</b> {request_data['problem_type']}
📝 <b>Описание:</b> {request_data['description'] or 'Не указано'}
📅 <b>Дата:</b> {request_data['date']}
🕐 <b>Время:</b> {request_data['time']}

#заявка #помещение{room['number']}
        """.strip()
        
        # Отправка в Telegram и Google Sheets
        telegram_success = telegram_bot.send_message(telegram_message)
        sheets_success = google_sheets.add_request(request_data)
        
        if telegram_success or sheets_success:
            return jsonify({
                'success': True,
                'message': 'Заявка отправлена успешно!',
                'telegram_sent': telegram_success,
                'sheets_saved': sheets_success
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Ошибка при отправке заявки'
            }), 500
        
    except Exception as e:
        logger.error(f"Error submitting request: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/generate_qr/<int:room_number>')
def generate_qr(room_number):
    """Генерация QR-кода для помещения"""
    try:
        url = f"{config.BASE_URL}/room/{room_number}"
        
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
        
        # Конвертация в base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return jsonify({
            'success': True,
            'qr_code': f"data:image/png;base64,{img_str}",
            'url': url,
            'room_number': room_number
        })
        
    except Exception as e:
        logger.error(f"Error generating QR code: {e}")
        return jsonify({'error': 'Failed to generate QR code'}), 500

@app.route('/admin/qr_codes')
def admin_qr_codes():
    """Административная страница для генерации QR-кодов"""
    return render_template('admin_qr.html')

@app.route('/api/rooms')
def get_rooms():
    """API для получения списка помещений"""
    # Здесь можно добавить логику получения из БД
    # Пока возвращаем тестовые данные
    rooms = []
    for i in range(1, 101):  # 100 помещений
        rooms.append({
            'number': i,
            'building': 'A' if i <= 50 else 'B',
            'floor': str((i - 1) // 10 + 1).zfill(2),
            'type': 'WC' if i % 3 == 0 else 'OFFICE',
            'name': config.ROOM_TYPES.get('WC' if i % 3 == 0 else 'OFFICE')
        })
    
    return jsonify(rooms)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)