# Руководство по автоматическому обновлению

Этот документ описывает настройку системы автоматического обновления Telegram-бота из GitHub репозитория.

## Возможности

- 🔄 **Автоматическое обновление кода** при push в GitHub
- 📦 **Обновление зависимостей** при изменении requirements.txt
- 🔄 **Безопасный перезапуск** без потери данных
- 🛡️ **Проверка подписи** GitHub webhook'ов
- 📊 **Админские команды** для управления обновлениями
- 🔍 **Мониторинг статуса** бота

## Настройка

### 1. Переменные окружения

Добавьте в ваш `.env` файл:

```bash
# Включить автоматическое обновление
AUTO_UPDATE_ENABLED=true

# Ветка для обновлений (обычно main или master)
UPDATE_BRANCH=main

# Секретный ключ GitHub webhook (рекомендуется)
GITHUB_WEBHOOK_SECRET=ваш_секретный_ключ

# Если используете webhook режим
USE_WEBHOOK=true
WEBHOOK_URL=https://yourdomain.com
PORT=3000
```

### 2. Настройка GitHub Webhook

1. Перейдите в настройки вашего GitHub репозитория
2. Выберите **Settings** → **Webhooks** → **Add webhook**
3. Заполните поля:
   - **Payload URL**: `https://yourdomain.com/github-webhook`
   - **Content type**: `application/json`
   - **Secret**: тот же ключ, что в `GITHUB_WEBHOOK_SECRET`
   - **Events**: выберите "Just the push event"
4. Нажмите **Add webhook**

### 3. Настройка сервера

#### Вариант A: Ручной запуск с мониторингом

```bash
# Запуск с автоматическим перезапуском
python auto_deploy.py

# Или с дополнительными опциями
python auto_deploy.py --check-interval 10 --debug
```

#### Вариант B: Systemd сервис (Linux)

Создайте файл `/etc/systemd/system/team-bot.service`:

```ini
[Unit]
Description=Team Bot Auto Deploy Service
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/team-bot
ExecStart=/usr/bin/python3 auto_deploy.py
Restart=always
RestartSec=10
Environment=PATH=/usr/bin:/usr/local/bin
Environment=PYTHONPATH=/path/to/team-bot

[Install]
WantedBy=multi-user.target
```

Затем запустите сервис:

```bash
sudo systemctl enable team-bot
sudo systemctl start team-bot
sudo systemctl status team-bot
```

#### Вариант C: Docker (рекомендуется для продакшена)

Создайте `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "auto_deploy.py"]
```

И `docker-compose.yml`:

```yaml
version: '3.8'
services:
  team-bot:
    build: .
    restart: unless-stopped
    volumes:
      - .:/app
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - AUTO_UPDATE_ENABLED=true
      - GITHUB_WEBHOOK_SECRET=${GITHUB_WEBHOOK_SECRET}
```

## Админские команды

### Команды управления обновлениями

- `/adm_update_check` — проверить наличие обновлений
- `/adm_update_apply` — применить доступные обновления  
- `/adm_update_force` — принудительное обновление
- `/adm_update_status` — показать статус автообновления

### Команды управления ботом

- `/adm_restart` — перезапустить бота
- `/adm_shutdown` — остановить бота
- `/adm_status` — показать статус бота (uptime, память, CPU)

## Как это работает

### Схема автообновления

1. **GitHub Push** → Webhook отправляется на ваш сервер
2. **Проверка подписи** → Валидация безопасности
3. **Проверка ветки** → Только указанная ветка (`UPDATE_BRANCH`)
4. **Git pull** → Загрузка изменений из репозитория  
5. **Проверка зависимостей** → Обновление requirements.txt при необходимости
6. **Уведомление админов** → Сообщение в Telegram
7. **Перезапуск бота** → Безопасное применение изменений

### Флаги управления

Система использует файлы-флаги для управления состоянием:

- `.restart_required` — сигнал о необходимости перезапуска
- `.shutdown_required` — сигнал об остановке бота

### Мониторинг процесса

Скрипт `auto_deploy.py` постоянно следит за:

- Работоспособностью бота
- Наличием флагов перезапуска/остановки  
- Автоматическим перезапуском при сбоях

## Безопасность

### Проверка подписи

Обязательно настройте `GITHUB_WEBHOOK_SECRET` для защиты от поддельных запросов:

```bash
# Сгенерируйте случайный ключ
openssl rand -hex 32

# Добавьте в .env
GITHUB_WEBHOOK_SECRET=your_generated_secret
```

### Ограничение доступа

- Webhook endpoint доступен только по HTTPS
- Админские команды требуют прав администратора  
- Автообновление можно отключить (`AUTO_UPDATE_ENABLED=false`)

## Отладка

### Логи

Проверьте файлы логов:

```bash
# Основные логи бота
tail -f bot.log

# Логи автодеплоя
tail -f auto_deploy.log

# Логи запуска
tail -f bot_startup.log
```

### Проверка webhook'а

Тестирование webhook'а вручную:

```bash
curl -X POST https://yourdomain.com/github-webhook \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=signature" \
  -d '{"ref":"refs/heads/main","commits":[{"id":"abc123"}]}'
```

### Проверка обновлений

```bash
# Проверка Git репозитория
cd /path/to/team-bot
git status
git log --oneline -5

# Проверка процессов
ps aux | grep team-bot
```

## Troubleshooting

### Проблема: Webhook не срабатывает

1. Проверьте URL в настройках GitHub
2. Убедитесь, что сервер доступен из интернета
3. Проверьте логи webhook'ов в GitHub (Settings → Webhooks)

### Проблема: Обновления не применяются

1. Проверьте `AUTO_UPDATE_ENABLED=true`
2. Убедитесь в правильности ветки `UPDATE_BRANCH`  
3. Проверьте права на запись в директории проекта

### Проблема: Бот не перезапускается

1. Проверьте наличие файла `.restart_required`
2. Убедитесь, что `auto_deploy.py` запущен
3. Проверьте логи на ошибки

### Проблема: Ошибки Git

```bash
# Сброс локальных изменений
git stash
git reset --hard HEAD

# Принудительное обновление
git fetch origin main
git reset --hard origin/main
```

## Примеры использования

### Типичный рабочий процесс

1. Разработчик делает изменения в коде
2. Коммитит и пушит в ветку `main`
3. GitHub отправляет webhook на сервер
4. Бот автоматически обновляется и перезапускается
5. Админы получают уведомление об обновлении

### Ручное управление

```bash
# Проверить обновления через команду
/adm_update_check

# Применить обновления
/adm_update_apply

# Принудительный перезапуск
/adm_restart
```

## Рекомендации

### Для стабильной работы

- Используйте отдельную ветку для продакшена (например, `production`)
- Тестируйте изменения перед merge в основную ветку
- Настройте мониторинг работоспособности бота
- Создавайте бэкапы данных регулярно

### Для безопасности

- Всегда используйте HTTPS для webhook'ов
- Настройте `GITHUB_WEBHOOK_SECRET`
- Ограничьте доступ к серверу
- Регулярно обновляйте зависимости

### Для удобства

- Настройте уведомления админов
- Используйте staging окружение для тестов
- Автоматизируйте резервное копирование
- Мониторьте использование ресурсов
