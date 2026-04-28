"""
Диагностика системы лояльности. Запуск:
    python scripts/check_loyalty.py +79991234567

Показывает:
  1. Что вернул GMB для этого телефона (raw JSON)
  2. Какой уровень определит наша утилита
  3. Прогресс до следующего уровня
  4. Какой текст увидит гость в боте
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if len(sys.argv) < 2:
    print("Использование: python scripts/check_loyalty.py <телефон>")
    print("Пример:        python scripts/check_loyalty.py +79991234567")
    sys.exit(1)

phone = sys.argv[1]

# ── 1. GMB API ──
from utils.gmb_client import gmb

if not gmb.is_configured():
    print("❌ GMB_API_KEY не установлен в окружении")
    sys.exit(1)

print(f"🔍 Запрос в GMB для телефона: {phone}")
print(f"📞 Нормализован: {gmb._normalize_phone(phone)}\n")

raw = gmb.find_client_by_phone(phone)

if not raw:
    print("❌ Клиент не найден в GMB (или ошибка API — смотри логи выше)")
    sys.exit(1)

print("=" * 60)
print("📦 RAW RESPONSE GMB:")
print("=" * 60)
print(json.dumps(raw, indent=2, ensure_ascii=False))

# ── 2. Извлекаем поля ──
client = raw.get('client', raw)
balance = client.get('balance', 0)
name = client.get('name', '?')
k_bonus = client.get('k_bonus', 0)
max_pay = client.get('maxPayBonusK', 0)
total_amount = (
    client.get('totalAmount')
    or client.get('total_amount')
    or client.get('totalAmountBonus')
    or 0
)

print("\n" + "=" * 60)
print("🔑 КЛЮЧЕВЫЕ ПОЛЯ:")
print("=" * 60)
print(f"  name          = {name}")
print(f"  balance       = {balance}")
print(f"  k_bonus (%)   = {k_bonus}")
print(f"  maxPayBonusK  = {max_pay}")
print(f"  totalAmount   = {total_amount}")

# ── 3. Уровень + прогресс ──
from utils.loyalty_levels import (
    get_level_by_total,
    get_level_by_k_bonus,
    get_progress_to_next,
    get_level_card_text,
)

if total_amount and float(total_amount) > 0:
    level = get_level_by_total(total_amount)
    src = "totalAmount"
else:
    level = get_level_by_k_bonus(k_bonus)
    src = "k_bonus (fallback)"

print("\n" + "=" * 60)
print(f"🎖  УРОВЕНЬ (определён по {src}):")
print("=" * 60)
print(f"  {level['emoji']} {level['name']} — {level['k_bonus']}% кэшбэка")
print(f"  {level['description']}")

progress = get_progress_to_next(total_amount or 0)
if progress:
    print(f"\n  → До «{progress['next_level']['name']}»: "
          f"осталось {progress['remaining_amount']:,} ₽ "
          f"({progress['progress_percent']}%)")
else:
    print(f"\n  🏆 Максимальный уровень")

# ── 4. Превью текста гостю ──
print("\n" + "=" * 60)
print("📱 ЧТО УВИДИТ ГОСТЬ В TELEGRAM:")
print("=" * 60)
print(get_level_card_text(
    name=name,
    balance=balance,
    total_amount=total_amount,
    k_bonus=k_bonus,
    max_pay_pct=max_pay,
))
