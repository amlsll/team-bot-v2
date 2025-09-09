"""
Простая веб-панель для мониторинга бота.
Запускается отдельно от основного бота для просмотра логов и метрик.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from aiohttp import web, WSMsgType
import aiohttp_jinja2
import jinja2
import logging
import time

# Настройка базового логирования для веб-сервера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MonitoringDashboard:
    """Веб-панель мониторинга."""
    
    def __init__(self, port=8080):
        self.port = port
        self.app = web.Application()
        self.websockets = set()
        self.setup_routes()
        self.setup_templates()
    
    def setup_templates(self):
        """Настройка шаблонов."""
        # Создаем директорию для шаблонов
        templates_dir = Path(__file__).parent / 'templates'
        templates_dir.mkdir(exist_ok=True)
        
        # Настройка Jinja2
        aiohttp_jinja2.setup(
            self.app,
            loader=jinja2.FileSystemLoader(str(templates_dir))
        )
        
        # Создаем основной шаблон если его нет
        self.create_templates()
    
    def create_templates(self):
        """Создает HTML шаблоны."""
        templates_dir = Path(__file__).parent / 'templates'
        
        # Основной шаблон панели
        dashboard_html = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Мониторинг Team Bot</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            color: #333;
            line-height: 1.6;
        }
        
        .header {
            background: #2c3e50;
            color: white;
            padding: 1rem 2rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            font-size: 1.5rem;
            font-weight: 600;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin-bottom: 2rem;
        }
        
        .card {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-left: 4px solid #3498db;
        }
        
        .card.warning {
            border-left-color: #f39c12;
        }
        
        .card.critical {
            border-left-color: #e74c3c;
        }
        
        .card.healthy {
            border-left-color: #27ae60;
        }
        
        .card-title {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: #2c3e50;
        }
        
        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem 0;
            border-bottom: 1px solid #ecf0f1;
        }
        
        .metric:last-child {
            border-bottom: none;
        }
        
        .metric-label {
            color: #7f8c8d;
        }
        
        .metric-value {
            font-weight: 600;
            color: #2c3e50;
        }
        
        .status-badge {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .status-healthy {
            background: #d5f4e6;
            color: #27ae60;
        }
        
        .status-warning {
            background: #fef9e7;
            color: #f39c12;
        }
        
        .status-critical {
            background: #fadbd8;
            color: #e74c3c;
        }
        
        .logs-container {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-top: 2rem;
        }
        
        .logs-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        
        .logs-content {
            background: #2c3e50;
            color: #ecf0f1;
            padding: 1rem;
            border-radius: 4px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 0.9rem;
            height: 400px;
            overflow-y: auto;
            white-space: pre-wrap;
        }
        
        .refresh-btn {
            background: #3498db;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9rem;
        }
        
        .refresh-btn:hover {
            background: #2980b9;
        }
        
        .auto-refresh {
            font-size: 0.8rem;
            color: #7f8c8d;
            margin-left: 1rem;
        }
        
        .error { color: #e74c3c; }
        .warning { color: #f39c12; }
        .info { color: #3498db; }
        .debug { color: #95a5a6; }
        
        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }
            
            .grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 Мониторинг Team Bot</h1>
    </div>
    
    <div class="container">
        <!-- Общий статус -->
        <div class="grid">
            <div class="card {{ overall_status }}">
                <div class="card-title">🏥 Общее состояние</div>
                <div class="metric">
                    <span class="metric-label">Статус:</span>
                    <span class="status-badge status-{{ overall_status }}">{{ overall_status }}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Последняя проверка:</span>
                    <span class="metric-value">{{ last_check }}</span>
                </div>
            </div>
            
            <!-- Метрики производительности -->
            <div class="card">
                <div class="card-title">📊 Метрики</div>
                <div class="metric">
                    <span class="metric-label">Сообщений обработано:</span>
                    <span class="metric-value">{{ metrics.messages_processed or 0 }}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Callback'ов обработано:</span>
                    <span class="metric-value">{{ metrics.callbacks_processed or 0 }}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Ошибок:</span>
                    <span class="metric-value">{{ metrics.errors_count or 0 }}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Активных пользователей:</span>
                    <span class="metric-value">{{ metrics.active_users_count or 0 }}</span>
                </div>
            </div>
            
            <!-- Системные ресурсы -->
            <div class="card">
                <div class="card-title">💻 Система</div>
                <div class="metric">
                    <span class="metric-label">Время работы:</span>
                    <span class="metric-value">{{ uptime }}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Использование памяти:</span>
                    <span class="metric-value">{{ system_info.memory_percent or 'N/A' }}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Использование CPU:</span>
                    <span class="metric-value">{{ system_info.cpu_percent or 'N/A' }}%</span>
                </div>
            </div>
        </div>
        
        <!-- Детали проверок здоровья -->
        <div class="grid">
            {% for check_name, check in health_checks.items() %}
            <div class="card {{ check.status }}">
                <div class="card-title">{{ check_name.replace('_', ' ').title() }}</div>
                <div class="metric">
                    <span class="metric-label">Статус:</span>
                    <span class="status-badge status-{{ check.status }}">{{ check.status }}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Сообщение:</span>
                    <span class="metric-value">{{ check.message[:50] }}{% if check.message|length > 50 %}...{% endif %}</span>
                </div>
            </div>
            {% endfor %}
        </div>
        
        <!-- Логи -->
        <div class="logs-container">
            <div class="logs-header">
                <h2 class="card-title">📋 Последние логи</h2>
                <div>
                    <button class="refresh-btn" onclick="refreshLogs()">🔄 Обновить</button>
                    <span class="auto-refresh">Автообновление: <span id="countdown">30</span>с</span>
                </div>
            </div>
            <div class="logs-content" id="logs-content">
                {{ logs }}
            </div>
        </div>
    </div>
    
    <script>
        let countdown = 30;
        let websocket = null;
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            websocket = new WebSocket(protocol + '//' + window.location.host + '/ws');
            
            websocket.onmessage = function(event) {
                const data = JSON.parse(event.data);
                if (data.type === 'logs_update') {
                    document.getElementById('logs-content').textContent = data.content;
                    document.getElementById('logs-content').scrollTop = 
                        document.getElementById('logs-content').scrollHeight;
                }
                if (data.type === 'full_update') {
                    location.reload();
                }
            };
            
            websocket.onclose = function() {
                setTimeout(connectWebSocket, 5000);
            };
        }
        
        function refreshLogs() {
            fetch('/api/logs')
                .then(response => response.text())
                .then(data => {
                    document.getElementById('logs-content').textContent = data;
                    document.getElementById('logs-content').scrollTop = 
                        document.getElementById('logs-content').scrollHeight;
                });
        }
        
        function updateCountdown() {
            const countdownElement = document.getElementById('countdown');
            countdownElement.textContent = countdown;
            
            if (countdown <= 0) {
                refreshLogs();
                countdown = 30;
            } else {
                countdown--;
            }
        }
        
        // Запуск
        connectWebSocket();
        setInterval(updateCountdown, 1000);
        setInterval(() => location.reload(), 60000); // Полное обновление каждую минуту
    </script>
</body>
</html>'''
        
        with open(templates_dir / 'dashboard.html', 'w', encoding='utf-8') as f:
            f.write(dashboard_html)
    
    def setup_routes(self):
        """Настройка маршрутов."""
        self.app.router.add_get('/', self.dashboard)
        self.app.router.add_get('/api/metrics', self.api_metrics)
        self.app.router.add_get('/api/logs', self.api_logs)
        self.app.router.add_get('/api/health', self.api_health)
        self.app.router.add_get('/ws', self.websocket_handler)
    
    @aiohttp_jinja2.template('dashboard.html')
    async def dashboard(self, request):
        """Главная страница панели."""
        try:
            # Получаем метрики из файла (если бот работает)
            metrics = self.get_current_metrics()
            health_data = self.get_health_data()
            system_info = self.get_system_info()
            logs = self.get_recent_logs()
            
            # Время работы
            uptime = "N/A"
            if metrics.get('uptime_seconds'):
                uptime_seconds = int(metrics['uptime_seconds'])
                uptime = str(timedelta(seconds=uptime_seconds))
            
            return {
                'metrics': metrics,
                'health_checks': health_data.get('checks', {}),
                'overall_status': health_data.get('overall_status', 'unknown'),
                'last_check': datetime.now().strftime('%H:%M:%S'),
                'system_info': system_info,
                'uptime': uptime,
                'logs': logs
            }
        except Exception as e:
            logger.error(f"Ошибка в dashboard: {e}")
            return {
                'metrics': {},
                'health_checks': {},
                'overall_status': 'unknown',
                'last_check': 'Error',
                'system_info': {},
                'uptime': 'N/A',
                'logs': f'Ошибка загрузки логов: {str(e)}'
            }
    
    async def api_metrics(self, request):
        """API для получения метрик."""
        metrics = self.get_current_metrics()
        return web.json_response(metrics)
    
    async def api_health(self, request):
        """API для получения состояния здоровья."""
        health_data = self.get_health_data()
        return web.json_response(health_data)
    
    async def api_logs(self, request):
        """API для получения логов."""
        logs = self.get_recent_logs()
        return web.Response(text=logs, content_type='text/plain')
    
    async def websocket_handler(self, request):
        """WebSocket для обновлений в реальном времени."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websockets.add(ws)
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    if msg.data == 'close':
                        await ws.close()
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f'WebSocket error: {ws.exception()}')
        finally:
            self.websockets.discard(ws)
        
        return ws
    
    def get_current_metrics(self):
        """Получает текущие метрики."""
        try:
            # Пытаемся импортировать метрики из работающего бота
            from app.services.logger import get_metrics
            return get_metrics()
        except ImportError:
            # Если бот не запущен, возвращаем пустые метрики
            return {
                'messages_processed': 0,
                'callbacks_processed': 0,
                'errors_count': 0,
                'active_users_count': 0,
                'uptime_seconds': 0
            }
        except Exception as e:
            logger.error(f"Ошибка получения метрик: {e}")
            return {}
    
    def get_health_data(self):
        """Получает данные о здоровье."""
        try:
            from app.services.health_monitor import health_monitor
            return health_monitor.get_health_summary()
        except ImportError:
            return {
                'overall_status': 'unknown',
                'checks': {}
            }
        except Exception as e:
            logger.error(f"Ошибка получения данных здоровья: {e}")
            return {
                'overall_status': 'error',
                'checks': {}
            }
    
    def get_system_info(self):
        """Получает информацию о системе."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            cpu = psutil.cpu_percent()
            
            return {
                'memory_percent': round(memory.percent, 1),
                'cpu_percent': round(cpu, 1),
                'memory_available_gb': round(memory.available / (1024**3), 2)
            }
        except ImportError:
            return {}
        except Exception as e:
            logger.error(f"Ошибка получения системной информации: {e}")
            return {}
    
    def get_recent_logs(self, lines=50):
        """Получает последние строки из логов."""
        try:
            logs_dir = Path('logs')
            log_file = logs_dir / 'bot_all.log'
            
            if not log_file.exists():
                return "Файл логов не найден"
            
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                
            return ''.join(recent_lines)
        except Exception as e:
            logger.error(f"Ошибка чтения логов: {e}")
            return f"Ошибка чтения логов: {str(e)}"
    
    async def broadcast_update(self, data):
        """Отправляет обновления всем подключенным WebSocket."""
        if self.websockets:
            message = json.dumps(data)
            for ws in list(self.websockets):
                try:
                    await ws.send_str(message)
                except Exception as e:
                    logger.error(f"Ошибка отправки WebSocket сообщения: {e}")
                    self.websockets.discard(ws)
    
    async def start_background_updates(self):
        """Запускает фоновые обновления."""
        while True:
            try:
                await asyncio.sleep(30)  # Обновляем каждые 30 секунд
                
                # Отправляем обновление логов
                logs = self.get_recent_logs()
                await self.broadcast_update({
                    'type': 'logs_update',
                    'content': logs
                })
                
            except Exception as e:
                logger.error(f"Ошибка в фоновом обновлении: {e}")
    
    def run(self):
        """Запускает веб-сервер."""
        logger.info(f"🌐 Запуск панели мониторинга на http://localhost:{self.port}")
        
        # Запускаем фоновые обновления
        asyncio.create_task(self.start_background_updates())
        
        web.run_app(self.app, host='0.0.0.0', port=self.port)


if __name__ == '__main__':
    dashboard = MonitoringDashboard(port=8080)
    dashboard.run()
