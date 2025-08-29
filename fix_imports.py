#!/usr/bin/env python3
"""
Скрипт для автоматического исправления импортов после реорганизации проекта
"""
import os
import re

def fix_imports_in_file(filepath):
    """Исправляет импорты в одном файле"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Исправления для config
    content = re.sub(r'from config import', 'from core.config import', content)
    content = re.sub(r'^import config$', 'import core.config as config', content, flags=re.MULTILINE)
    
    # Исправления для database
    content = re.sub(r'^import database$', 'import core.database as database', content, flags=re.MULTILINE)
    content = re.sub(r'from database import', 'from core.database import', content)
    
    # Исправления для utilities
    content = re.sub(r'from qr_generator import', 'from utils.qr_generator import', content)
    content = re.sub(r'from export_to_sheets import', 'from utils.export_to_sheets import', content)
    content = re.sub(r'from social_bookings_export import', 'from utils.social_bookings_export import', content)
    content = re.sub(r'from referral_notifications import', 'from utils.referral_notifications import', content)
    
    # Исправления для modules
    content = re.sub(r'from games import', 'from modules.games import', content)
    content = re.sub(r'from daily_activities import', 'from modules.daily_activities import', content)
    content = re.sub(r'from staff_manager import', 'from modules.staff_manager import', content)
    content = re.sub(r'from marketing_templates import', 'from modules.marketing_templates import', content)
    content = re.sub(r'from food_menu import', 'from modules.food_menu import', content)
    content = re.sub(r'from menu_nastoiki import', 'from modules.menu_nastoiki import', content)
    
    # Исправления для knowledge_base
    content = re.sub(r'from knowledge_base import', 'from ai.knowledge_base import', content)
    content = re.sub(r'^import knowledge_base$', 'import ai.knowledge_base as knowledge_base', content, flags=re.MULTILINE)
    
    # Исправления для delayed_tasks_processor
    content = re.sub(r'from delayed_tasks_processor import', 'from core.delayed_tasks_processor import', content)
    
    # Исправления для settings_manager
    content = re.sub(r'from settings_manager import', 'from core.settings_manager import', content)
    content = re.sub(r'^import settings_manager$', 'import core.settings_manager as settings_manager', content, flags=re.MULTILINE)
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Исправлен: {filepath}")
        return True
    return False

def main():
    """Основная функция"""
    print("🔧 Исправление импортов после реорганизации...")
    
    # Папки для обработки
    folders_to_process = [
        'handlers',
        'keyboards',
        'texts', 
        'ai',
        'utils',
        'modules',
        'core',
        'web',
        'db'
    ]
    
    # Файлы в корне
    root_files = ['main.py']
    
    fixed_count = 0
    
    # Обрабатываем корневые файлы
    for filename in root_files:
        filepath = f"/workspaces/evgenich-gift/{filename}"
        if os.path.exists(filepath):
            if fix_imports_in_file(filepath):
                fixed_count += 1
    
    # Обрабатываем папки
    for folder in folders_to_process:
        folder_path = f"/workspaces/evgenich-gift/{folder}"
        if os.path.exists(folder_path):
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.endswith('.py'):
                        filepath = os.path.join(root, file)
                        if fix_imports_in_file(filepath):
                            fixed_count += 1
    
    print(f"\n🎉 Готово! Исправлено файлов: {fixed_count}")

if __name__ == "__main__":
    main()
