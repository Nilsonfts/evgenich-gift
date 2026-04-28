"""
GetMeBack (GMB) API Client
Интеграция с системой лояльности evgenich.getmeback.ru

API endpoint: POST /rest/base/v33/validator/
Auth: api_key в теле запроса

Операции:
  - Поиск клиента по телефону / id_client / id_device
  - Начисление бонусов (type=bonus)
  - Выдача подарков   (type=gift)
"""

import os
import logging
import requests
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# ── Конфигурация ──
GMB_API_URL = os.getenv(
    'GMB_API_URL',
    'https://evgenich.getmeback.ru/rest/base/v33/validator/'
)
GMB_API_KEY = os.getenv('GMB_API_KEY', '')

# Таймаут для HTTP-запросов (секунды)
GMB_TIMEOUT = 10


class GMBClient:
    """Клиент для работы с GetMeBack REST API."""

    def __init__(self, api_key: str = None, api_url: str = None):
        self.api_key = api_key or GMB_API_KEY
        self.api_url = api_url or GMB_API_URL
        # Последний сырой ответ — для диагностики из админки
        self.last_raw_response = None
        self.last_raw_request = None
        self.last_raw_status = None

    def _call(self, data: dict) -> Optional[Any]:
        """Базовый вызов API. Возвращает parsed JSON или None."""
        if not self.api_key:
            logger.error("GMB API key не настроен (GMB_API_KEY)")
            return None

        payload = {'api_key': self.api_key}
        payload.update(data)

        # Сохраняем для диагностики (api_key маскируем)
        safe_payload = dict(payload)
        if 'api_key' in safe_payload:
            safe_payload['api_key'] = safe_payload['api_key'][:6] + '***'
        self.last_raw_request = safe_payload

        try:
            resp = requests.post(
                self.api_url,
                json=payload,
                timeout=GMB_TIMEOUT,
                headers={'Content-Type': 'application/json'}
            )
            self.last_raw_status = resp.status_code
            # Сохраняем сырой текст ДО raise_for_status — чтобы видеть тело ошибки
            raw_text = resp.text
            self.last_raw_response = raw_text[:2000]
            logger.info(f"GMB API [{resp.status_code}] req={safe_payload} resp={raw_text[:500]}")
            resp.raise_for_status()
            result = resp.json()
            return result
        except requests.Timeout:
            logger.error(f"GMB API timeout ({GMB_TIMEOUT}s)")
            self.last_raw_response = f"TIMEOUT after {GMB_TIMEOUT}s"
            return None
        except requests.RequestException as e:
            logger.error(f"GMB API error: {e}")
            return None
        except ValueError:
            logger.error(f"GMB API invalid JSON")
            return None

    # ───────────────────────────
    # Поиск клиента
    # ───────────────────────────
    def find_client_by_phone(self, phone: str) -> Optional[Dict]:
        """
        Ищет клиента по номеру телефона.

        В GMB телефон хранится как `login` (79991234567 без +).
        Пробуем несколько вариантов полей (в порядке вероятности):
          1. login=79XX     — основной, так хранится в GMB
          2. phone=79XX     — fallback, если API всё же ждёт phone
          3. id_device=79XX — fallback, если API ждёт id_device
        """
        clean_phone = self._normalize_phone(phone)
        if not clean_phone:
            return None

        # Порядок попыток (первый удачный — выходим)
        attempts = [
            {'login': clean_phone},
            {'phone': clean_phone},
            {'id_device': clean_phone},
        ]

        for payload in attempts:
            result = self._call(payload)
            parsed = self._parse_client_response(result)
            if parsed:
                logger.info(f"GMB клиент найден через {list(payload.keys())[0]}={clean_phone}")
                return parsed

        logger.warning(f"GMB клиент не найден ни по одному полю для {clean_phone}")
        return None

    def find_client_by_id(self, id_client: int) -> Optional[Dict]:
        """Ищет клиента по ID в системе GMB."""
        result = self._call({'id_client': id_client})
        return self._parse_client_response(result)

    def find_client_by_device(self, id_device: str) -> Optional[Dict]:
        """Ищет клиента по ID устройства (QR-код)."""
        result = self._call({'id_device': id_device})
        return self._parse_client_response(result)

    # ───────────────────────────
    # Бонусные операции
    # ───────────────────────────
    def accrue_bonus(
        self,
        id_client: int,
        order_price: int,
        id_branch: int = 1,
        id_manager: int = 1,
        manager_name: str = 'Web Panel',
        branch_name: str = 'Евгенич',
        invoice_num: str = '',
        bonus_value: int = None,
        paid_bonus: int = None,
        positions: List[Dict] = None
    ) -> Optional[Dict]:
        """
        Начисляет бонусы за покупку.

        Args:
            id_client: ID клиента в GMB
            order_price: Сумма заказа
            id_branch: ID филиала
            id_manager: ID сотрудника
            manager_name: Имя сотрудника
            branch_name: Название филиала
            invoice_num: Номер чека
            bonus_value: Кол-во бонусов (если None — рассчитывается GMB)
            paid_bonus: Сумма бонусов, списанных в оплату заказа
            positions: Массив позиций заказа

        Returns:
            dict с result='ok'/'error', bonus_value, bonus_id, client
        """
        data = {
            'type': 'bonus',
            'id_client': id_client,
            'order_price': order_price,
            'id_branch': id_branch,
            'id_manager': id_manager,
            'manager_name': manager_name,
            'branch_name': branch_name,
        }
        if invoice_num:
            data['invoice_num'] = invoice_num
        if bonus_value is not None:
            data['bonus_value'] = bonus_value
        if paid_bonus is not None:
            data['paid_bonus'] = paid_bonus
        if positions:
            data['positions'] = positions

        result = self._call(data)
        if result and isinstance(result, dict):
            return result
        return {'result': 'error', 'message': 'Пустой ответ от GMB'}

    def deduct_bonus(
        self,
        id_client: int,
        paid_bonus: int,
        order_price: int,
        id_branch: int = 1,
        id_manager: int = 1,
        manager_name: str = 'Web Panel',
        branch_name: str = 'Евгенич',
        invoice_num: str = ''
    ) -> Optional[Dict]:
        """Списание бонусов за оплату заказа."""
        return self.accrue_bonus(
            id_client=id_client,
            order_price=order_price,
            paid_bonus=paid_bonus,
            id_branch=id_branch,
            id_manager=id_manager,
            manager_name=manager_name,
            branch_name=branch_name,
            invoice_num=invoice_num
        )

    # ───────────────────────────
    # Подарки
    # ───────────────────────────
    def redeem_gift(
        self,
        id_client: int,
        id_gift: int,
        id_branch: int = 1,
        id_manager: int = 1,
        manager_name: str = 'Web Panel',
        branch_name: str = 'Евгенич'
    ) -> Optional[Dict]:
        """
        Выдаёт подарок клиенту.

        Args:
            id_client: ID клиента в GMB
            id_gift: ID подарка в GMB
        """
        data = {
            'type': 'gift',
            'id_client': id_client,
            'id_gift': id_gift,
            'id_branch': id_branch,
            'id_manager': id_manager,
            'manager_name': manager_name,
            'branch_name': branch_name,
        }
        result = self._call(data)
        if result and isinstance(result, dict):
            return result
        return {'result': 'error', 'message': 'Пустой ответ от GMB'}

    # ───────────────────────────
    # Утилиты
    # ───────────────────────────
    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Приводит телефон к числовому формату (без +, пробелов, скобок, дефисов)."""
        if not phone:
            return ''
        cleaned = ''.join(c for c in phone if c.isdigit())
        # Если начинается с 8 → заменяем на 7 (Россия)
        if len(cleaned) == 11 and cleaned.startswith('8'):
            cleaned = '7' + cleaned[1:]
        return cleaned

    @staticmethod
    def _parse_client_response(result) -> Optional[Dict]:
        """
        Парсит ответ API и извлекает данные клиента.
        Ответ может быть:
          - dict с ключом 'client' → возвращаем
          - list → берём первый элемент
          - пустой list / null → None
        """
        if result is None:
            return None
        if isinstance(result, list):
            if len(result) == 0:
                return None
            # Если list — берём первый элемент
            item = result[0]
            if isinstance(item, dict):
                return item
            return None
        if isinstance(result, dict):
            # Если есть ключ client — это ответ на операцию
            if 'client' in result:
                return result
            # Иначе сам dict — это клиент
            if 'id_client' in result or 'name' in result or 'phone' in result:
                return result
            return result
        return None

    def is_configured(self) -> bool:
        """Проверяет, настроен ли API ключ."""
        return bool(self.api_key)


# Глобальный экземпляр
gmb = GMBClient()
