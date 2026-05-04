import asyncio
import sqlite3
import random
from datetime import datetime, timedelta
from contextlib import closing

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile

BOT_TOKEN = '8627076346:AAF0F9wLSZPNloGZux9nBZFLDmVAJ5O7-L8'
CHANNEL_LINK = "https://t.me/+yZM4dP7FeAgxZDQy"
ADMIN_IDS = [8035910686, 8403747223]
PAYMENT_LINK = "https://t.me/rupitic"
PHOTO_PATH = "photo.jpg"

def init_db():
    with closing(sqlite3.connect('snozer_bot.db')) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute('''CREATE TABLE IF NOT EXISTS users
                        (user_id INTEGER PRIMARY KEY,
                         username TEXT,
                         subscription_end INTEGER DEFAULT 0,
                         subscription_start INTEGER DEFAULT 0,
                         is_banned INTEGER DEFAULT 0,
                         has_passed_check INTEGER DEFAULT 0)''')
            
            try:
                cur.execute("ALTER TABLE users ADD COLUMN subscription_start INTEGER DEFAULT 0")
            except:
                pass
            
            try:
                cur.execute("ALTER TABLE users ADD COLUMN has_passed_check INTEGER DEFAULT 0")
            except:
                pass
            
            conn.commit()

init_db()

def get_user(user_id):
    with closing(sqlite3.connect('snozer_bot.db')) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("SELECT subscription_end, subscription_start, is_banned, has_passed_check FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            if row:
                return {
                    "subscription_end": row[0] if row[0] is not None else 0,
                    "subscription_start": row[1] if row[1] is not None else 0,
                    "is_banned": row[2] if row[2] is not None else 0,
                    "has_passed_check": row[3] if row[3] is not None else 0
                }
            return None

def add_user(user_id, username):
    with closing(sqlite3.connect('snozer_bot.db')) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("INSERT OR IGNORE INTO users (user_id, username, subscription_end, subscription_start, is_banned, has_passed_check) VALUES (?, ?, 0, 0, 0, 0)",
                        (user_id, username))
            conn.commit()

def set_subscription(user_id, days):
    end_time = int((datetime.now() + timedelta(days=days)).timestamp())
    start_time = int(datetime.now().timestamp())
    with closing(sqlite3.connect('snozer_bot.db')) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("UPDATE users SET subscription_end = ?, subscription_start = ? WHERE user_id = ?", (end_time, start_time, user_id))
            conn.commit()

def remove_subscription(user_id):
    with closing(sqlite3.connect('snozer_bot.db')) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("UPDATE users SET subscription_end = 0, subscription_start = 0 WHERE user_id = ?", (user_id,))
            conn.commit()

def ban_user(user_id):
    with closing(sqlite3.connect('snozer_bot.db')) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
            conn.commit()

def unban_user(user_id):
    with closing(sqlite3.connect('snozer_bot.db')) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
            conn.commit()

def set_check_passed(user_id):
    with closing(sqlite3.connect('snozer_bot.db')) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute("UPDATE users SET has_passed_check = 1 WHERE user_id = ?", (user_id,))
            conn.commit()

def is_subscribed(user_id):
    user = get_user(user_id)
    if user and user["subscription_end"] > int(datetime.now().timestamp()):
        return True
    return False

def get_subscription_start(user_id):
    user = get_user(user_id)
    if user and user["subscription_start"] and user["subscription_start"] > 0:
        return datetime.fromtimestamp(user["subscription_start"]).strftime("%Y-%m-%d %H:%M:%S")
    return "Нет"

def get_subscription_end(user_id):
    user = get_user(user_id)
    if user and user["subscription_end"] and user["subscription_end"] > 0:
        return datetime.fromtimestamp(user["subscription_end"]).strftime("%Y-%m-%d %H:%M:%S")
    return "Нет"

start_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Подписаться на канал", url=CHANNEL_LINK)],
    [InlineKeyboardButton(text="Проверка подписки", callback_data="check_sub")]
])

main_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🍕Pizza", callback_data="pizza_start")],
    [InlineKeyboardButton(text="Профиль", callback_data="profile"), InlineKeyboardButton(text="Канал", url=CHANNEL_LINK)]
])

admin_main_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🍕Pizza", callback_data="pizza_start")],
    [InlineKeyboardButton(text="Профиль", callback_data="profile"), InlineKeyboardButton(text="Канал", url=CHANNEL_LINK)],
    [InlineKeyboardButton(text="👑 Админ панель", callback_data="admin_panel")]
])

profile_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Пополнить баланс подписки", url=PAYMENT_LINK)],
    [InlineKeyboardButton(text="Вернуться назад", callback_data="back_to_main")]
])

admin_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Выдать подписку", callback_data="admin_give_sub")],
    [InlineKeyboardButton(text="Забрать подписку", callback_data="admin_remove_sub")],
    [InlineKeyboardButton(text="Бан пользователей", callback_data="admin_ban")],
    [InlineKeyboardButton(text="Разбан пользователей", callback_data="admin_unban")],
    [InlineKeyboardButton(text="Назад", callback_data="back_to_main")]
])

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

admin_states = {}
waiting_for_target = {}
user_last_message = {}

MAIN_MENU_TEXT = """Pizza lizing

Более 500р@ботающих Сессий

639Пр#Кси"""

async def send_main_menu(message, user_id):
    try:
        photo = FSInputFile(PHOTO_PATH)
        if user_id in ADMIN_IDS:
            msg = await message.answer_photo(photo=photo, caption=MAIN_MENU_TEXT, reply_markup=admin_main_menu)
        else:
            msg = await message.answer_photo(photo=photo, caption=MAIN_MENU_TEXT, reply_markup=main_menu)
        user_last_message[user_id] = msg.message_id
    except:
        if user_id in ADMIN_IDS:
            msg = await message.answer(MAIN_MENU_TEXT, reply_markup=admin_main_menu)
        else:
            msg = await message.answer(MAIN_MENU_TEXT, reply_markup=main_menu)
        user_last_message[user_id] = msg.message_id

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "no_username"
    add_user(user_id, username)
    await send_main_menu(message, user_id)

@dp.callback_query(F.data == "check_sub")
async def check_sub(callback: CallbackQuery):
    user_id = callback.from_user.id
    set_check_passed(user_id)
    await callback.answer("Подписка подтверждена!", show_alert=True)
    await callback.message.delete()
    await send_main_menu(callback.message, user_id)

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.delete()
    await send_main_menu(callback.message, user_id)

@dp.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    user_id = callback.from_user.id
    sub_status = "есть" if is_subscribed(user_id) else "нет"
    sub_start = get_subscription_start(user_id)
    sub_end = get_subscription_end(user_id)
    
    text = f"Ваш айди: {user_id}\nПодписка: {sub_status}\nДата выдачи: {sub_start}\nДата окончания: {sub_end}"
    
    if user_id in user_last_message:
        try:
            await bot.delete_message(chat_id=user_id, message_id=user_last_message[user_id])
        except:
            pass
    
    msg = await callback.message.answer(text, reply_markup=profile_menu)
    user_last_message[user_id] = msg.message_id
    await callback.answer()

@dp.callback_query(F.data == "pizza_start")
async def pizza_start(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not is_subscribed(user_id):
        await callback.answer("У вас нет подписки! Пополните баланс в профиле.", show_alert=True)
        return
    
    waiting_for_target[user_id] = True
    await callback.message.answer("Введите T@Rget Цель\nЮзернейм или айди")

@dp.message()
async def handle_target(message: types.Message):
    user_id = message.from_user.id
    
    if user_id in waiting_for_target:
        target = message.text.strip()
        del waiting_for_target[user_id]
        
        msg = await message.answer(f"🎯 Цель: {target}\n\nАтака началась...")
        
        await asyncio.sleep(180)
        
        successful = random.randint(300, 500)
        failed = random.randint(30, 100)
        
        await msg.edit_text(f"Удачных @так: {successful}\nНеудачных атак: {failed}\n\n🎯 Цель: {target}")
        return
    
    if user_id in ADMIN_IDS and user_id in admin_states:
        state = admin_states[user_id]
        target = message.text.strip()
        
        target_user_id = None
        if target.isdigit():
            target_user_id = int(target)
        elif target.startswith("@"):
            with closing(sqlite3.connect('snozer_bot.db')) as conn:
                with closing(conn.cursor()) as cur:
                    cur.execute("SELECT user_id FROM users WHERE username = ?", (target[1:],))
                    row = cur.fetchone()
                    if row:
                        target_user_id = row[0]
        
        if not target_user_id:
            await message.answer("Пользователь не найден!")
            del admin_states[user_id]
            return
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if state == "give_sub":
            set_subscription(target_user_id, 30)
            await message.answer(f"Выдана подписка (30 дней) пользователю {target}\nВремя выдачи: {now}")
        elif state == "remove_sub":
            remove_subscription(target_user_id)
            await message.answer(f"Подписка забрана у {target}\nВремя: {now}")
        elif state == "ban":
            ban_user(target_user_id)
            await message.answer(f"Пользователь {target} забанен\nВремя: {now}")
        elif state == "unban":
            unban_user(target_user_id)
            await message.answer(f"Пользователь {target} разбанен\nВремя: {now}")
        
        del admin_states[user_id]

@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in ADMIN_IDS:
        await callback.answer("У вас нет доступа!", show_alert=True)
        return
    
    if user_id in user_last_message:
        try:
            await bot.delete_message(chat_id=user_id, message_id=user_last_message[user_id])
        except:
            pass
    
    msg = await callback.message.answer("Админ панель:", reply_markup=admin_menu)
    user_last_message[user_id] = msg.message_id
    await callback.answer()

@dp.callback_query(F.data == "admin_give_sub")
async def admin_give_sub(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    admin_states[callback.from_user.id] = "give_sub"
    await callback.message.answer("Введите айди или юзернейм:")
    await callback.answer()

@dp.callback_query(F.data == "admin_remove_sub")
async def admin_remove_sub(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    admin_states[callback.from_user.id] = "remove_sub"
    await callback.message.answer("Введите айди или юзернейм:")
    await callback.answer()

@dp.callback_query(F.data == "admin_ban")
async def admin_ban(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    admin_states[callback.from_user.id] = "ban"
    await callback.message.answer("Введите айди или юзернейм для бана:")
    await callback.answer()

@dp.callback_query(F.data == "admin_unban")
async def admin_unban(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return
    admin_states[callback.from_user.id] = "unban"
    await callback.message.answer("Введите айди или юзернейм для разбана:")
    await callback.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())