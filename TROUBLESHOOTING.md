# 🔧 Руководство по устранению неполадок Team-Bot

## 🚨 Проблема: "Запущено несколько экземпляров бота"

### 📋 Быстрое решение
```bash
# 1. Остановить все экземпляры
python stop_all_bots.py

# 2. Запустить заново
python run_bot.py
```

### 🔍 Диагностика проблемы

#### Шаг 1: Проверить запущенные процессы
```bash
python stop_all_bots.py --list
```

#### Шаг 2: Полная диагностика
```bash
python bot_health_check.py
```

#### Шаг 3: Ручная проверка (Linux/macOS)
```bash
# Найти все процессы Python с ботом
ps aux | grep -E "python.*[team_bot|start_bot|app]"

# Проверить использование портов (если используется webhook)
lsof -i :3000
```

### 🛠️ Методы устранения

#### Метод 1: Автоматический (рекомендуется)
```bash
python run_bot.py --force
```

#### Метод 2: Пошаговый
```bash
# Остановить все
python stop_all_bots.py

# Проверить что все остановлено
python stop_all_bots.py --list

# Запустить заново
python run_bot.py
```

#### Метод 3: Принудительный
```bash
# Принудительная остановка всех процессов
python stop_all_bots.py --force

# Или ручными командами
pkill -9 -f "team_bot|start_bot|python.*app"
```

#### Метод 4: Перезагрузка системы (крайняя мера)
```bash
sudo reboot
```

## 🔍 Частые причины конфликтов

### 1. Множественные терминалы
**Проблема:** Запуск бота в нескольких окнах терминала
**Решение:** Всегда проверяйте запущенные процессы перед новым запуском

### 2. Фоновые процессы
**Проблема:** Бот запущен в фоне через `nohup`, `screen` или `tmux`
**Диагностика:**
```bash
# Проверить screen сессии
screen -ls

# Проверить tmux сессии
tmux list-sessions

# Проверить nohup процессы
ps aux | grep nohup
```

**Решение:**
```bash
# Завершить screen сессии
screen -X -S session_name quit

# Завершить tmux сессии
tmux kill-session -t session_name
```

### 3. IDE конфликты
**Проблема:** Запуск одновременно в IDE и консоли
**Решение:** Остановите процесс в IDE перед консольным запуском

### 4. Системные службы
**Проблема:** Бот настроен как systemd сервис
**Диагностика:**
```bash
systemctl status team-bot
systemctl is-active team-bot
```

**Решение:**
```bash
sudo systemctl stop team-bot
sudo systemctl disable team-bot
```

### 5. Планировщики задач
**Проблема:** Автозапуск через cron или планировщик
**Диагностика:**
```bash
crontab -l
sudo crontab -l
```

**Решение:** Удалите или закомментируйте соответствующие задания

## 🚀 Лучшие практики

### 1. Всегда используйте безопасный запуск
```bash
python run_bot.py  # Вместо python start_bot.py
```

### 2. Проверяйте перед запуском
```bash
python stop_all_bots.py --list
```

### 3. Настройте алиасы для удобства
Добавьте в `~/.bashrc` или `~/.zshrc`:
```bash
alias bot-start="cd /path/to/team-bot && python run_bot.py"
alias bot-stop="cd /path/to/team-bot && python stop_all_bots.py"
alias bot-status="cd /path/to/team-bot && python stop_all_bots.py --list"
alias bot-check="cd /path/to/team-bot && python bot_health_check.py"
```

### 4. Используйте логи для отладки
```bash
# Просмотр логов запуска
tail -f bot_startup.log

# Просмотр основных логов
tail -f bot.log
```

## 🐛 Специфические ошибки

### Ошибка: "Permission denied"
```bash
# Проверить права доступа
ls -la *.py

# Сделать файлы исполняемыми
chmod +x run_bot.py stop_all_bots.py
```

### Ошибка: "Port already in use" (webhook режим)
```bash
# Найти процесс использующий порт
lsof -i :3000

# Завершить процесс
kill -9 PID
```

### Ошибка: "Bot token invalid"
```bash
# Проверить токен
python test_bot.py

# Проверить .env файл
cat .env | grep BOT_TOKEN
```

### Ошибка: "Module not found"
```bash
# Установить зависимости
pip install -r requirements.txt

# Проверить установку
python -c "import aiogram, psutil; print('OK')"
```

## 📊 Мониторинг работы

### Создание скрипта мониторинга
```bash
#!/bin/bash
# monitor_bot.sh

while true; do
    if ! python stop_all_bots.py --list | grep -q "PID:"; then
        echo "$(date): Бот не запущен, запускаем..."
        python run_bot.py &
    fi
    sleep 60
done
```

### Системный мониторинг
```bash
# Добавить в crontab для проверки каждые 5 минут
*/5 * * * * /path/to/team-bot/monitor_bot.sh >> /var/log/bot-monitor.log 2>&1
```

## 📞 Получение помощи

1. **Логи:** Всегда прикладывайте содержимое `bot_startup.log` и `bot.log`
2. **Диагностика:** Выполните `python bot_health_check.py` и приложите результат
3. **Процессы:** Покажите вывод `python stop_all_bots.py --list`
4. **Система:** Укажите ОС, версию Python и способ запуска

Горячая линия конкурса: **+7 (499) 722⁠-69⁠-99**
