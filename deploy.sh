#!/bin/bash

# Скрипт для развертывания системы учета проблем в помещениях
# Использование: ./deploy.sh [production|development]

set -e  # Выход при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции для цветного вывода
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Проверка аргументов
ENVIRONMENT=${1:-development}

if [[ "$ENVIRONMENT" != "production" && "$ENVIRONMENT" != "development" ]]; then
    print_error "Неверное окружение. Используйте: production или development"
    exit 1
fi

print_info "🚀 Развертывание системы учета проблем в помещениях"
print_info "📦 Окружение: $ENVIRONMENT"
echo "=================================================="

# Проверка Python
print_info "Проверка Python..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 не установлен"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
print_success "Python $PYTHON_VERSION найден"

# Создание виртуального окружения
print_info "Создание виртуального окружения..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Виртуальное окружение создано"
else
    print_warning "Виртуальное окружение уже существует"
fi

# Активация виртуального окружения
print_info "Активация виртуального окружения..."
source venv/bin/activate

# Обновление pip
print_info "Обновление pip..."
pip install --upgrade pip > /dev/null 2>&1

# Установка зависимостей
print_info "Установка зависимостей..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    print_success "Зависимости установлены"
else
    print_error "Ошибка установки зависимостей"
    exit 1
fi

# Создание .env файла если его нет
if [ ! -f ".env" ]; then
    print_info "Создание файла конфигурации..."
    cp .env.example .env
    print_warning "Файл .env создан. Необходимо заполнить конфигурацию!"
    print_info "Отредактируйте файл .env и добавьте:"
    echo "  - TELEGRAM_BOT_TOKEN"
    echo "  - TELEGRAM_CHAT_ID"
    echo "  - GOOGLE_SHEET_ID"
    echo "  - BASE_URL"
fi

# Проверка конфигурации
print_info "Проверка конфигурации..."
source .env

MISSING_CONFIG=false

if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ "$TELEGRAM_BOT_TOKEN" = "your_bot_token_here" ]; then
    print_warning "TELEGRAM_BOT_TOKEN не настроен"
    MISSING_CONFIG=true
fi

if [ -z "$TELEGRAM_CHAT_ID" ] || [ "$TELEGRAM_CHAT_ID" = "your_chat_id_here" ]; then
    print_warning "TELEGRAM_CHAT_ID не настроен"
    MISSING_CONFIG=true
fi

if [ -z "$GOOGLE_SHEET_ID" ] || [ "$GOOGLE_SHEET_ID" = "your_google_sheet_id_here" ]; then
    print_warning "GOOGLE_SHEET_ID не настроен"
    MISSING_CONFIG=true
fi

if [ ! -f "credentials.json" ]; then
    print_warning "credentials.json не найден"
    MISSING_CONFIG=true
fi

if [ "$MISSING_CONFIG" = true ]; then
    print_warning "Некоторые параметры конфигурации не настроены"
    print_info "Запустите скрипты настройки:"
    echo "  python setup_telegram_bot.py"
    echo "  python setup_google_sheets.py"
fi

# Создание папок
print_info "Создание необходимых папок..."
mkdir -p logs
mkdir -p static/css
mkdir -p static/js
mkdir -p templates

# Настройка для продакшена
if [ "$ENVIRONMENT" = "production" ]; then
    print_info "Настройка для продакшена..."
    
    # Установка gunicorn если не установлен
    pip install gunicorn
    
    # Создание systemd сервиса
    print_info "Создание systemd сервиса..."
    
    SERVICE_FILE="/etc/systemd/system/room-issues.service"
    CURRENT_DIR=$(pwd)
    USER=$(whoami)
    
    if [ "$USER" = "root" ]; then
        USER="www-data"
    fi
    
    sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=Room Issues System
After=network.target

[Service]
Type=exec
User=$USER
Group=$USER
WorkingDirectory=$CURRENT_DIR
Environment=PATH=$CURRENT_DIR/venv/bin
ExecStart=$CURRENT_DIR/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 app:app
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
EOF

    print_success "Systemd сервис создан: $SERVICE_FILE"
    
    # Перезагрузка systemd
    sudo systemctl daemon-reload
    sudo systemctl enable room-issues.service
    
    print_info "Создание nginx конфигурации..."
    
    NGINX_CONFIG="/etc/nginx/sites-available/room-issues"
    DOMAIN=${BASE_URL:-"your-domain.com"}
    DOMAIN=${DOMAIN#https://}
    DOMAIN=${DOMAIN#http://}
    
    sudo tee $NGINX_CONFIG > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static/ {
        alias $CURRENT_DIR/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

    # Активация сайта nginx
    sudo ln -sf $NGINX_CONFIG /etc/nginx/sites-enabled/
    
    print_success "Nginx конфигурация создана"
    print_info "Не забудьте перезапустить nginx: sudo systemctl reload nginx"
    
    # SSL сертификат
    if command -v certbot &> /dev/null; then
        print_info "Certbot найден. Для получения SSL сертификата выполните:"
        echo "  sudo certbot --nginx -d $DOMAIN"
    else
        print_warning "Certbot не найден. Рекомендуется установить SSL сертификат"
    fi
fi

# Тестирование системы
print_info "Запуск тестов..."
if python test_system.py; then
    print_success "Базовые тесты пройдены"
else
    print_warning "Некоторые тесты не прошли. Проверьте конфигурацию"
fi

# Финальные инструкции
echo "=================================================="
print_success "🎉 Развертывание завершено!"

if [ "$ENVIRONMENT" = "development" ]; then
    print_info "Для запуска в режиме разработки:"
    echo "  source venv/bin/activate"
    echo "  python app.py"
    echo ""
    print_info "Приложение будет доступно по адресу: http://localhost:5000"
else
    print_info "Для запуска в продакшене:"
    echo "  sudo systemctl start room-issues"
    echo "  sudo systemctl status room-issues"
    echo ""
    print_info "Приложение будет доступно по адресу: http://$DOMAIN"
fi

print_info "📝 Дальнейшие шаги:"
echo "1. Настройте Telegram бота: python setup_telegram_bot.py"
echo "2. Настройте Google Sheets: python setup_google_sheets.py"
echo "3. Сгенерируйте QR-коды: /admin/qr_codes"
echo "4. Протестируйте систему: python test_system.py"

print_info "📚 Документация:"
echo "- README.md - основная документация"
echo "- ALTERNATIVES.md - альтернативные решения"

print_success "Система готова к использованию! 🚀"