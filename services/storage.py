# storage.py
import json
import os
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class UserStorage:
    def __init__(self, filename: str = "users.json"):
        """
        Инициализация хранилища пользователей
        
        Args:
            filename: имя файла для хранения данных
        """
        self.filename = filename
        self._users: Dict[int, dict] = {}
        self._load_from_file()
    
    def _load_from_file(self):
        """Загрузка данных из файла"""
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r', encoding='utf-8') as f:
                    # JSON хранит ключи как строки, конвертируем в int
                    data = json.load(f)
                    self._users = {int(k): v for k, v in data.items()}
                logger.info(f"Загружено {len(self._users)} пользователей из {self.filename}")
            else:
                logger.info(f"Файл {self.filename} не найден, создаем новое хранилище")
                self._users = {}
        except Exception as e:
            logger.error(f"Ошибка при загрузке из {self.filename}: {e}")
            self._users = {}
    
    def _save_to_file(self):
        """Сохранение данных в файл"""
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                # Конвертируем int ключи в строки для JSON
                data = {str(k): v for k, v in self._users.items()}
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Сохранено {len(self._users)} пользователей в {self.filename}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении в {self.filename}: {e}")
    
    def get_user(self, user_id: int) -> Optional[dict]:
        """Получить пользователя по ID"""
        return self._users.get(user_id)
    
    def save_user(self, user_id: int, name: str) -> None:
        """Сохранить пользователя"""
        self._users[user_id] = {
            "name": name,
            "telegram_id": user_id
        }
        self._save_to_file()
    
    def update_user(self, user_id: int, **kwargs) -> None:
        """Обновить данные пользователя"""
        if user_id in self._users:
            self._users[user_id].update(kwargs)
            self._save_to_file()
    
    def delete_user(self, user_id: int) -> None:
        """Удалить пользователя"""
        if user_id in self._users:
            del self._users[user_id]
            self._save_to_file()
    
    def get_all_users(self) -> Dict[int, dict]:
        """Получить всех пользователей"""
        return self._users.copy()
    
    def get_users_count(self) -> int:
        """Получить количество пользователей"""
        return len(self._users)

# Создаем глобальный экземпляр хранилища
user_storage = UserStorage()