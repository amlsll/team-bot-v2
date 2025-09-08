"""
Сервис автоматического обновления бота из GitHub репозитория.
"""

import os
import asyncio
import subprocess
import logging
import json
import hashlib
import hmac
from datetime import datetime
from typing import Dict, Optional, Tuple, List

logger = logging.getLogger(__name__)


class AutoUpdateService:
    """Сервис для автоматического обновления кода бота из GitHub."""
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = project_root or os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.github_secret = os.getenv('GITHUB_WEBHOOK_SECRET')
        self.auto_update_enabled = os.getenv('AUTO_UPDATE_ENABLED', 'false').lower() == 'true'
        self.update_branch = os.getenv('UPDATE_BRANCH', 'main')
        self.backup_dir = os.path.join(self.project_root, '.backups')
        
        # Создаем директорию для бэкапов
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def verify_github_signature(self, payload_body: bytes, signature_header: str) -> bool:
        """Проверяет подпись GitHub webhook'а."""
        if not self.github_secret:
            logger.warning("GITHUB_WEBHOOK_SECRET не настроен, пропускаем проверку подписи")
            return True
        
        if not signature_header.startswith('sha256='):
            return False
        
        expected_signature = hmac.new(
            self.github_secret.encode('utf-8'),
            payload_body,
            hashlib.sha256
        ).hexdigest()
        
        received_signature = signature_header[7:]  # Убираем 'sha256='
        
        return hmac.compare_digest(expected_signature, received_signature)
    
    def get_current_commit_info(self) -> Dict[str, Optional[str]]:
        """Получает информацию о текущем коммите."""
        try:
            # Текущий хеш коммита
            commit_hash = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            ).stdout.strip()
            
            # Информация о коммите
            commit_info = subprocess.run(
                ['git', 'log', '-1', '--format=%ci|%s|%an'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            ).stdout.strip()
            
            commit_parts = commit_info.split('|', 2)
            
            return {
                'hash': commit_hash,
                'short_hash': commit_hash[:8],
                'date': commit_parts[0] if len(commit_parts) > 0 else None,
                'message': commit_parts[1] if len(commit_parts) > 1 else None,
                'author': commit_parts[2] if len(commit_parts) > 2 else None
            }
        except Exception as e:
            logger.error(f"Ошибка получения информации о коммите: {e}")
            return {
                'hash': None,
                'short_hash': None,
                'date': None,
                'message': None,
                'author': None
            }
    
    def has_updates(self) -> Tuple[bool, Dict]:
        """Проверяет наличие обновлений в репозитории."""
        try:
            # Получаем текущий коммит
            current_info = self.get_current_commit_info()
            
            # Обновляем информацию о удаленном репозитории
            subprocess.run(
                ['git', 'fetch', 'origin', self.update_branch],
                cwd=self.project_root,
                capture_output=True,
                check=True
            )
            
            # Получаем хеш последнего коммита в удаленной ветке
            remote_hash = subprocess.run(
                ['git', 'rev-parse', f'origin/{self.update_branch}'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            ).stdout.strip()
            
            # Получаем информацию о удаленном коммите
            remote_info = subprocess.run(
                ['git', 'log', '-1', '--format=%ci|%s|%an', f'origin/{self.update_branch}'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            ).stdout.strip()
            
            remote_parts = remote_info.split('|', 2)
            
            remote_commit_info = {
                'hash': remote_hash,
                'short_hash': remote_hash[:8],
                'date': remote_parts[0] if len(remote_parts) > 0 else None,
                'message': remote_parts[1] if len(remote_parts) > 1 else None,
                'author': remote_parts[2] if len(remote_parts) > 2 else None
            }
            
            has_updates = current_info['hash'] != remote_hash
            
            return has_updates, {
                'current': current_info,
                'remote': remote_commit_info,
                'commits_behind': self._get_commits_behind() if has_updates else 0
            }
            
        except Exception as e:
            logger.error(f"Ошибка проверки обновлений: {e}")
            return False, {}
    
    def _get_commits_behind(self) -> int:
        """Получает количество коммитов, на которое отстает локальная ветка."""
        try:
            result = subprocess.run(
                ['git', 'rev-list', '--count', f'HEAD..origin/{self.update_branch}'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            return int(result.stdout.strip())
        except Exception:
            return 0
    
    def create_backup(self) -> Optional[str]:
        """Создает бэкап текущего состояния."""
        try:
            current_info = self.get_current_commit_info()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"backup_{timestamp}_{current_info['short_hash']}"
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            # Создаем stash с текущими изменениями
            subprocess.run(
                ['git', 'stash', 'push', '-m', f'Auto-backup before update {timestamp}'],
                cwd=self.project_root,
                capture_output=True
            )
            
            # Создаем информационный файл бэкапа
            backup_info = {
                'timestamp': timestamp,
                'commit_info': current_info,
                'backup_type': 'auto_update'
            }
            
            with open(f"{backup_path}.json", 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Создан бэкап: {backup_name}")
            return backup_name
            
        except Exception as e:
            logger.error(f"Ошибка создания бэкапа: {e}")
            return None
    
    def apply_update(self) -> Tuple[bool, str]:
        """Применяет обновления из репозитория."""
        try:
            # Проверяем, что репозиторий чистый
            status_result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            if status_result.stdout.strip():
                # Есть неcommitted изменения, создаем stash
                logger.info("Обнаружены локальные изменения, создаем stash...")
                subprocess.run(
                    ['git', 'stash', 'push', '-m', 'Auto-stash before update'],
                    cwd=self.project_root,
                    capture_output=True,
                    check=True
                )
            
            # Выполняем pull
            result = subprocess.run(
                ['git', 'pull', 'origin', self.update_branch],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info("Обновление применено успешно")
            return True, result.stdout
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Ошибка git pull: {e.stderr}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Критическая ошибка при обновлении: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def check_dependencies(self) -> Tuple[bool, List[str]]:
        """Проверяет, нужно ли обновлять зависимости."""
        try:
            # Проверяем изменения в requirements.txt
            result = subprocess.run(
                ['git', 'diff', 'HEAD~1', 'HEAD', '--name-only'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            changed_files = result.stdout.strip().split('\n')
            dependency_files = ['requirements.txt', 'pyproject.toml', 'poetry.lock']
            
            changed_deps = [f for f in changed_files if f in dependency_files]
            
            return len(changed_deps) > 0, changed_deps
            
        except Exception as e:
            logger.error(f"Ошибка проверки зависимостей: {e}")
            return False, []
    
    async def update_dependencies(self) -> Tuple[bool, str]:
        """Обновляет зависимости проекта."""
        try:
            logger.info("Обновляем зависимости...")
            
            # Обновляем pip пакеты
            process = await asyncio.create_subprocess_exec(
                'pip', 'install', '-r', 'requirements.txt', '--upgrade',
                cwd=self.project_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info("Зависимости обновлены успешно")
                return True, stdout.decode()
            else:
                error_msg = f"Ошибка обновления зависимостей: {stderr.decode()}"
                logger.error(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Критическая ошибка при обновлении зависимостей: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def parse_github_webhook(self, payload: Dict) -> Optional[Dict]:
        """Парсит webhook payload от GitHub."""
        try:
            if payload.get('ref') != f'refs/heads/{self.update_branch}':
                logger.info(f"Webhook для ветки {payload.get('ref')}, игнорируем")
                return None
            
            commits = payload.get('commits', [])
            if not commits:
                logger.info("Нет коммитов в webhook payload")
                return None
            
            latest_commit = commits[-1]
            
            return {
                'repository': payload.get('repository', {}).get('full_name'),
                'branch': self.update_branch,
                'commit': {
                    'id': latest_commit.get('id'),
                    'message': latest_commit.get('message'),
                    'author': latest_commit.get('author', {}).get('name'),
                    'timestamp': latest_commit.get('timestamp'),
                    'url': latest_commit.get('url')
                },
                'pusher': payload.get('pusher', {}).get('name'),
                'commits_count': len(commits)
            }
            
        except Exception as e:
            logger.error(f"Ошибка парсинга GitHub webhook: {e}")
            return None
    
    async def perform_full_update(self, force: bool = False) -> Dict:
        """Выполняет полное обновление бота."""
        result = {
            'success': False,
            'timestamp': datetime.now().isoformat(),
            'steps': [],
            'error': None,
            'restart_required': False
        }
        
        try:
            # Проверяем включено ли автообновление
            if not force and not self.auto_update_enabled:
                result['error'] = "Автообновление отключено"
                return result
            
            # Шаг 1: Проверяем обновления
            result['steps'].append({'step': 'check_updates', 'status': 'started'})
            has_updates, update_info = self.has_updates()
            
            if not has_updates and not force:
                result['steps'][-1]['status'] = 'completed'
                result['steps'][-1]['message'] = 'Обновления не найдены'
                result['success'] = True
                return result
            
            result['steps'][-1]['status'] = 'completed'
            result['steps'][-1]['update_info'] = update_info
            
            # Шаг 2: Создаем бэкап
            result['steps'].append({'step': 'create_backup', 'status': 'started'})
            backup_name = self.create_backup()
            if backup_name:
                result['steps'][-1]['status'] = 'completed'
                result['steps'][-1]['backup_name'] = backup_name
            else:
                result['steps'][-1]['status'] = 'failed'
                result['steps'][-1]['message'] = 'Не удалось создать бэкап'
            
            # Шаг 3: Применяем обновления
            result['steps'].append({'step': 'apply_update', 'status': 'started'})
            update_success, update_message = self.apply_update()
            
            if update_success:
                result['steps'][-1]['status'] = 'completed'
                result['steps'][-1]['message'] = update_message
            else:
                result['steps'][-1]['status'] = 'failed'
                result['steps'][-1]['error'] = update_message
                result['error'] = "Не удалось применить обновления"
                return result
            
            # Шаг 4: Проверяем зависимости
            result['steps'].append({'step': 'check_dependencies', 'status': 'started'})
            deps_changed, changed_files = self.check_dependencies()
            
            if deps_changed:
                result['steps'][-1]['status'] = 'completed'
                result['steps'][-1]['changed_files'] = changed_files
                
                # Обновляем зависимости
                result['steps'].append({'step': 'update_dependencies', 'status': 'started'})
                deps_success, deps_message = await self.update_dependencies()
                
                if deps_success:
                    result['steps'][-1]['status'] = 'completed'
                    result['steps'][-1]['message'] = deps_message
                    result['restart_required'] = True
                else:
                    result['steps'][-1]['status'] = 'failed'
                    result['steps'][-1]['error'] = deps_message
                    result['error'] = "Не удалось обновить зависимости"
                    return result
            else:
                result['steps'][-1]['status'] = 'completed'
                result['steps'][-1]['message'] = 'Зависимости не изменились'
            
            result['success'] = True
            result['restart_required'] = True  # После обновления кода всегда нужен перезапуск
            
            return result
            
        except Exception as e:
            result['error'] = f"Критическая ошибка обновления: {e}"
            logger.error(result['error'])
            return result
