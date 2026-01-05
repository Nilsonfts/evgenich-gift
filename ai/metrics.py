# /ai/metrics.py
"""
Сбор метрик использования AI (токены, стоимость, время ответа)
"""
import logging
import json
from datetime import datetime, date
from pathlib import Path
from typing import Optional

logger = logging.getLogger("evgenich_ai")


class AIMetrics:
    """
    Сборщик метрик использования AI
    
    Логирует каждый запрос к OpenAI API с информацией о токенах,
    времени ответа и стоимости
    """
    
    # Цены за 1M токенов (актуально для GPT-4o на январь 2026)
    PRICES = {
        "gpt-4o": {
            "input": 2.50,   # $ за 1M input токенов
            "output": 10.00  # $ за 1M output токенов
        },
        "gpt-4o-mini": {
            "input": 0.15,
            "output": 0.60
        },
        "gpt-3.5-turbo": {
            "input": 0.50,
            "output": 1.50
        }
    }
    
    def __init__(self, log_file: str = "logs/ai_metrics.jsonl"):
        """
        Args:
            log_file: Путь к файлу для логирования метрик
        """
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(exist_ok=True, parents=True)
        logger.info(f"AIMetrics инициализирован, лог: {self.log_file}")
    
    def log_request(
        self,
        user_id: int,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        response_time: float,
        success: bool = True,
        error: Optional[str] = None
    ) -> None:
        """
        Залогировать запрос к AI
        
        Args:
            user_id: ID пользователя
            model: Модель (gpt-4o, gpt-3.5-turbo и т.д.)
            prompt_tokens: Количество токенов в запросе
            completion_tokens: Количество токенов в ответе
            response_time: Время ответа в секундах
            success: Успешен ли запрос
            error: Текст ошибки если была
        """
        total_tokens = prompt_tokens + completion_tokens
        
        # Вычисляем стоимость
        cost_usd = self._calculate_cost(model, prompt_tokens, completion_tokens)
        
        metric = {
            "timestamp": datetime.now().isoformat(),
            "date": date.today().isoformat(),
            "user_id": user_id,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "response_time_ms": round(response_time * 1000, 2),
            "cost_usd": round(cost_usd, 6),
            "success": success,
            "error": error
        }
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(metric, ensure_ascii=False) + '\n')
            
            logger.debug(
                f"Метрика залогирована: user={user_id}, tokens={total_tokens}, "
                f"cost=${cost_usd:.4f}, time={response_time:.2f}s"
            )
        except Exception as e:
            logger.error(f"Ошибка записи метрики: {e}")
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """
        Вычислить стоимость запроса
        
        Args:
            model: Название модели
            input_tokens: Токены в запросе
            output_tokens: Токены в ответе
            
        Returns:
            Стоимость в USD
        """
        if model not in self.PRICES:
            logger.warning(f"Неизвестная модель для расчёта стоимости: {model}")
            model = "gpt-4o"  # По умолчанию
        
        prices = self.PRICES[model]
        
        input_cost = (input_tokens / 1_000_000) * prices["input"]
        output_cost = (output_tokens / 1_000_000) * prices["output"]
        
        return input_cost + output_cost
    
    def get_daily_stats(self, target_date: Optional[date] = None) -> dict:
        """
        Получить статистику за день
        
        Args:
            target_date: Дата для статистики (по умолчанию сегодня)
            
        Returns:
            dict со статистикой
        """
        if target_date is None:
            target_date = date.today()
        
        target_date_str = target_date.isoformat()
        
        stats = {
            "date": target_date_str,
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_cost_usd": 0.0,
            "avg_response_time_ms": 0.0,
            "unique_users": set()
        }
        
        if not self.log_file.exists():
            return self._finalize_stats(stats)
        
        response_times = []
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        metric = json.loads(line)
                        
                        if metric.get("date") != target_date_str:
                            continue
                        
                        stats["total_requests"] += 1
                        
                        if metric.get("success", True):
                            stats["successful_requests"] += 1
                        else:
                            stats["failed_requests"] += 1
                        
                        stats["total_tokens"] += metric.get("total_tokens", 0)
                        stats["prompt_tokens"] += metric.get("prompt_tokens", 0)
                        stats["completion_tokens"] += metric.get("completion_tokens", 0)
                        stats["total_cost_usd"] += metric.get("cost_usd", 0)
                        stats["unique_users"].add(metric.get("user_id"))
                        
                        if "response_time_ms" in metric:
                            response_times.append(metric["response_time_ms"])
                    
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        logger.warning(f"Ошибка обработки строки метрики: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"Ошибка чтения файла метрик: {e}")
        
        if response_times:
            stats["avg_response_time_ms"] = sum(response_times) / len(response_times)
        
        return self._finalize_stats(stats)
    
    def _finalize_stats(self, stats: dict) -> dict:
        """Финализировать статистику (конвертировать set в int)"""
        stats["unique_users"] = len(stats["unique_users"])
        stats["total_cost_usd"] = round(stats["total_cost_usd"], 4)
        stats["avg_response_time_ms"] = round(stats["avg_response_time_ms"], 2)
        return stats
    
    def get_user_stats(self, user_id: int, days: int = 7) -> dict:
        """
        Получить статистику для конкретного пользователя
        
        Args:
            user_id: ID пользователя
            days: За сколько дней считать
            
        Returns:
            dict со статистикой пользователя
        """
        from datetime import timedelta
        
        cutoff_date = (date.today() - timedelta(days=days)).isoformat()
        
        stats = {
            "user_id": user_id,
            "period_days": days,
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "avg_tokens_per_request": 0
        }
        
        if not self.log_file.exists():
            return stats
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        metric = json.loads(line)
                        
                        if metric.get("user_id") != user_id:
                            continue
                        
                        if metric.get("date", "") < cutoff_date:
                            continue
                        
                        stats["total_requests"] += 1
                        stats["total_tokens"] += metric.get("total_tokens", 0)
                        stats["total_cost_usd"] += metric.get("cost_usd", 0)
                    
                    except:
                        continue
        
        except Exception as e:
            logger.error(f"Ошибка чтения статистики пользователя: {e}")
        
        if stats["total_requests"] > 0:
            stats["avg_tokens_per_request"] = stats["total_tokens"] // stats["total_requests"]
        
        stats["total_cost_usd"] = round(stats["total_cost_usd"], 4)
        
        return stats


# Глобальный экземпляр
ai_metrics = AIMetrics()
