import os
import asyncio
import sqlite3
import random
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from threading import Thread

# ========== FLASK ДЛЯ 24/7 ==========
app = Flask('')

@app.route('/')
def home():
    return "🎮 Nilters Bot is alive! 🚀"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# Запускаем Flask в отдельном потоке
Thread(target=run_flask, daemon=True).start()

# ========== НАСТРОЙКИ ==========
TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TOKEN:
    print("❌ ОШИБКА: TELEGRAM_TOKEN не установлен!")
    print("Добавьте TELEGRAM_TOKEN в Environment Variables на Render")
    exit(1)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ========== БАЗА ДАННЫХ ==========
def init_db():
    conn = sqlite3.connect('nilters.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            coins INTEGER DEFAULT 100,
            level INTEGER DEFAULT 1,
            health INTEGER DEFAULT 100,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_name TEXT,
            quantity INTEGER DEFAULT 1
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

# ========== КОМАНДЫ БОТА ==========

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    conn = sqlite3.connect('nilters.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM players WHERE user_id = ?', (user_id,))
    if not cursor.fetchone():
        cursor.execute('INSERT INTO players (user_id, username) VALUES (?, ?)', (user_id, username))
        cursor.execute('INSERT INTO inventory (user_id, item_name) VALUES (?, ?)', (user_id, "⚔️ Стартовый меч"))
        conn.commit()
        
        await message.answer(
            f"🎮 *Добро пожаловать в NILTERS SERVERS!*\n\n"
            f"👤 *{username}*, твой путь героя начинается!\n\n"
            f"💰 *Стартовые ресурсы:*\n"
            f"• 100 монет\n"
            f"• ⚔️ Стартовый меч\n"
            f"• 100 HP здоровья\n\n"
            f"⚔️ *Основные команды:*\n"
            f"/profile - твой профиль\n"
            f"/battle - битва с боссом\n"
            f"/shop - магазин\n"
            f"/work - заработок\n"
            f"/top - рейтинг\n"
            f"/help - помощь\n\n"
            f"*Удачи в приключениях!* 🛡️",
            parse_mode="Markdown"
        )
        print(f"✅ Новый игрок: {username}")
    else:
        await message.answer(f"С возвращением, {username}! 🎮")
    
    conn.close()

@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    conn = sqlite3.connect('nilters.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM players WHERE user_id = ?', (message.from_user.id,))
    player = cursor.fetchone()
    
    if player:
        cursor.execute('SELECT COUNT(*) FROM inventory WHERE user_id = ?', (message.from_user.id,))
        items_count = cursor.fetchone()[0]
        
        await message.answer(
            f"👤 *ПРОФИЛЬ ИГРОКА*\n\n"
            f"🏷️ Имя: {player[1]}\n"
            f"💰 Монеты: {player[2]} 🪙\n"
            f"⭐ Уровень: {player[3]}\n"
            f"❤️ Здоровье: {player[4]}/100\n"
            f"🎒 Предметов: {items_count}\n"
            f"📅 Играет с: {player[5][:10]}\n\n"
            f"⚔️ Готов к бою!",
            parse_mode="Markdown"
        )
    else:
        await message.answer("❌ Сначала напишите /start")
    
    conn.close()

@dp.message(Command("battle"))
async def cmd_battle(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧌 Гоблин (легкий)", callback_data="battle_goblin")],
        [InlineKeyboardButton(text="⚔️ Орк (средний)", callback_data="battle_orc")],
        [InlineKeyboardButton(text="🐉 Дракон (сложный)", callback_data="battle_dragon")]
    ])
    
    await message.answer(
        "⚔️ *ВЫБЕРИ БОССА:*\n\n"
        "• 🧌 Гоблин - 50 HP, награда 30 монет\n"
        "• ⚔️ Орк - 80 HP, награда 50 монет\n"
        "• 🐉 Дракон - 120 HP, награда 100 монет",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

@dp.callback_query(F.data.startswith("battle_"))
async def process_battle(callback_query: types.CallbackQuery):
    boss_type = callback_query.data.split("_")[1]
    
    bosses = {
        "goblin": {"name": "🧌 Гоблин", "reward": 30},
        "orc": {"name": "⚔️ Орк", "reward": 50},
        "dragon": {"name": "🐉 Дракон", "reward": 100}
    }
    
    boss = bosses[boss_type]
    
    # Простая логика битвы
    win_chance = random.random()
    
    conn = sqlite3.connect('nilters.db')
    cursor = conn.cursor()
    cursor.execute('SELECT coins FROM players WHERE user_id = ?', (callback_query.from_user.id,))
    player = cursor.fetchone()
    
    if player:
        if win_chance > 0.3:  # 70% шанс победы
            new_coins = player[0] + boss["reward"]
            cursor.execute('UPDATE players SET coins = ? WHERE user_id = ?', 
                         (new_coins, callback_query.from_user.id))
            conn.commit()
            
            result = f"🎉 *ПОБЕДА!*\n+{boss['reward']} монет\n💰 Всего: {new_coins}"
        else:
            penalty = 10
            new_coins = max(0, player[0] - penalty)
            cursor.execute('UPDATE players SET coins = ? WHERE user_id = ?', 
                         (new_coins, callback_query.from_user.id))
            conn.commit()
            
            result = f"💀 *ПОРАЖЕНИЕ*\n-{penalty} монет\n💰 Всего: {new_coins}"
        
        await callback_query.message.edit_text(
            f"⚔️ *Битва с {boss['name']}*\n\n{result}",
            parse_mode="Markdown"
        )
    
    conn.close()

@dp.message(Command("shop"))
async def cmd_shop(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧪 Зелье (50 🪙)", callback_data="buy_potion")],
        [InlineKeyboardButton(text="🗡️ Меч (100 🪙)", callback_data="buy_sword")],
        [InlineKeyboardButton(text="🛡️ Щит (80 🪙)", callback_data="buy_shield")]
    ])
    
    await message.answer(
        "🛒 *МАГАЗИН NILTERS*\n\n"
        "Выбери предмет для покупки:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback_query: types.CallbackQuery):
    item = callback_query.data.split("_")[1]
    
    prices = {
        "potion": {"name": "🧪 Зелье здоровья", "price": 50},
        "sword": {"name": "🗡️ Стальной меч", "price": 100},
        "shield": {"name": "🛡️ Железный щит", "price": 80}
    }
    
    if item not in prices:
        await callback_query.answer("Товар не найден", show_alert=True)
        return
    
    item_data = prices[item]
    
    conn = sqlite3.connect('nilters.db')
    cursor = conn.cursor()
    cursor.execute('SELECT coins FROM players WHERE user_id = ?', (callback_query.from_user.id,))
    player = cursor.fetchone()
    
    if player and player[0] >= item_data["price"]:
        new_coins = player[0] - item_data["price"]
        cursor.execute('UPDATE players SET coins = ? WHERE user_id = ?', 
                     (new_coins, callback_query.from_user.id))
        cursor.execute('INSERT INTO inventory (user_id, item_name) VALUES (?, ?)', 
                     (callback_query.from_user.id, item_data["name"]))
        conn.commit()
        
        await callback_query.answer(
            f"✅ Куплено: {item_data['name']}\n💰 Осталось: {new_coins} 🪙",
            show_alert=True
        )
    else:
        await callback_query.answer("❌ Недостаточно монет!", show_alert=True)
    
    conn.close()

@dp.message(Command("work"))
async def cmd_work(message: types.Message):
    earnings = random.randint(20, 50)
    jobs = ["⚒️ Шахтер", "🛒 Продавец", "🏦 Охранник", "📦 Курьер"]
    job = random.choice(jobs)
    
    conn = sqlite3.connect('nilters.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE players SET coins = coins + ? WHERE user_id = ?', 
                 (earnings, message.from_user.id))
    conn.commit()
    conn.close()
    
    await message.answer(f"{job}\n💰 Заработано: {earnings} монет")

@dp.message(Command("top"))
async def cmd_top(message: types.Message):
    conn = sqlite3.connect('nilters.db')
    cursor = conn.cursor()
    cursor.execute('SELECT username, coins FROM players ORDER BY coins DESC LIMIT 10')
    top = cursor.fetchall()
    conn.close()
    
    if top:
        text = "🏆 *ТОП ИГРОКОВ:*\n\n"
        for i, (name, coins) in enumerate(top, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} - {coins} 🪙\n"
        
        await message.answer(text, parse_mode="Markdown")
    else:
        await message.answer("🏆 Пока никто не играет...\nБудь первым! /start")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
🎮 *NILTERS SERVERS - ПОМОЩЬ*

⚔️ *ОСНОВНЫЕ КОМАНДЫ:*
/start - Начать игру
/profile - Ваш профиль
/battle - Битва с боссом
/shop - Магазин предметов
/work - Заработать монеты
/top - Рейтинг игроков
/help - Эта справка

💰 *КАК ИГРАТЬ:*
1. Начни игру: /start
2. Заработай монеты: /work
3. Купи предметы: /shop
4. Сразись с боссами: /battle
5. Стань лучшим: /top

💬 *ОБЩЕНИЕ:*
Пиши боту вопросы!
Он всегда ответит и поможет.

⚙️ *ТЕХНИЧЕСКОЕ:*
Бот работает 24/7 на Render.com
База данных: SQLite
    """
    
    await message.answer(help_text, parse_mode="Markdown")

@dp.message(Command("ping"))
async def cmd_ping(message: types.Message):
    await message.answer("🏓 Pong! Бот работает отлично!")

@dp.message()
async def handle_other_messages(message: types.Message):
    responses = [
        "Используй /help для списка команд! ⚔️",
        "Хочешь сразиться? /battle",
        "Проверь свой профиль: /profile",
        "Заработай монеты: /work",
        "Nilters Servers ждет твоих побед! 🎮"
    ]
    await message.answer(random.choice(responses))

# ========== ЗАПУСК БОТА ==========
async def main():
    # Инициализация БД
    init_db()
    
    # Удаляем старый вебхук
    await bot.delete_webhook()
    
    # Получаем информацию о боте
    bot_info = await bot.get_me()
    
    print("=" * 60)
    print("🎮 NILTERS SERVERS - Игровой Telegram бот")
    print("=" * 60)
    print(f"🤖 Бот: @{bot_info.username}")
    print(f"⭐ Имя: {bot_info.first_name}")
    print(f"🆔 ID: {bot_info.id}")
    print("🌐 Хостинг: Render.com")
    print("⏰ Режим: 24/7 онлайн")
    print("=" * 60)
    print("📱 Откройте Telegram и найдите бота")
    print("⚔️ Напишите /start для начала игры")
    print("=" * 60)
    
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
