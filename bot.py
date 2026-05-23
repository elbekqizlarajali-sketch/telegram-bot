"""
Telegram Referral Bot — aiogram 3.x
"""

import asyncio
import sqlite3
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
BOT_TOKEN = "8707735340:AAHSvRn1da2rO9FSTw_fsVsoEoXV5p_Od2Y"
CHANNEL_ID = "@DARVINGAMER_RASMIY"
CHANNEL_LINK = "https://t.me/DARVINGAMER_RASMIY"
STARS_PER_REFERRAL = 5
ADMIN_IDS = [8408160535]
# ============================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.executescript("""
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    full_name   TEXT,
    referred_by INTEGER DEFAULT NULL,
    stars       INTEGER DEFAULT 0,
    joined_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS referrals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id INTEGER,
    referred_id INTEGER,
    stars_given INTEGER,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")
conn.commit()

def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()

def add_user(user_id, username, full_name, referred_by=None):
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, full_name, referred_by) VALUES (?, ?, ?, ?)",
        (user_id, username, full_name, referred_by)
    )
    conn.commit()

def add_stars(user_id, amount):
    cursor.execute("UPDATE users SET stars = stars + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()

def get_stars(user_id):
    cursor.execute("SELECT stars FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 0

def get_referral_count(user_id):
    cursor.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))
    return cursor.fetchone()[0]

def get_total_users():
    cursor.execute("SELECT COUNT(*) FROM users")
    return cursor.fetchone()[0]

async def is_subscribed(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status not in (ChatMemberStatus.KICKED, ChatMemberStatus.LEFT)
    except TelegramBadRequest:
        return False

def sub_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="✅ Obuna bo'ldim, tekshir", callback_data="check_sub")]
    ])

def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Mening referal havolam", callback_data="my_referral")],
        [InlineKeyboardButton(text="⭐ Mening Starslarim", callback_data="my_stars")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="stats")],
    ])

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    args = message.text.split()
    referred_by = None

    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referred_by = int(args[1][4:])
            if referred_by == user.id:
                referred_by = None
        except ValueError:
            referred_by = None

    is_new = get_user(user.id) is None
    add_user(user.id, user.username or "", user.full_name, referred_by)

    if not await is_subscribed(user.id):
        await message.answer(
            f"👋 Salom, <b>{user.full_name}</b>!\n\n"
            "⚠️ Botdan foydalanish uchun avval kanalimizga obuna bo'lishingiz shart!\n\n"
            f"📢 <b>{CHANNEL_LINK}</b>",
            reply_markup=sub_keyboard(),
            parse_mode="HTML"
        )
        return

    if is_new and referred_by:
        referrer = get_user(referred_by)
        if referrer:
            add_stars(referred_by, STARS_PER_REFERRAL)
            cursor.execute(
                "INSERT INTO referrals (referrer_id, referred_id, stars_given) VALUES (?, ?, ?)",
                (referred_by, user.id, STARS_PER_REFERRAL)
            )
            conn.commit()
            try:
                await bot.send_message(
                    referred_by,
                    f"🎉 <b>Yangi referal!</b>\n\n"
                    f"👤 <b>{user.full_name}</b> sizning havolangiz orqali qo'shildi.\n"
                    f"⭐ <b>+{STARS_PER_REFERRAL} Stars</b> hisobingizga qo'shildi!",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    bot_info = await bot.get_me()
    stars = get_stars(user.id)
    ref_count = get_referral_count(user.id)

    await message.answer(
        f"✅ <b>Xush kelibsiz, {user.full_name}!</b>\n\n"
        f"⭐ Starslaringiz: <b>{stars}</b>\n"
        f"👥 Referallaringiz: <b>{ref_count} kishi</b>\n\n"
        f"🔗 Sizning referal havolangiz:\n"
        f"<code>https://t.me/{bot_info.username}?start=ref_{user.id}</code>\n\n"
        f"Har bir do'stingiz uchun <b>{STARS_PER_REFERRAL} ⭐ Stars</b> olasiz!",
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "check_sub")
async def check_sub(callback: CallbackQuery):
    user = callback.from_user
    if not await is_subscribed(user.id):
        await callback.answer("❌ Hali obuna bo'lmadingiz! Iltimos kanalga obuna bo'ling.", show_alert=True)
        return
    await callback.message.delete()
    # start ni qayta chaqirish
    class FakeMsg:
        text = "/start"
        from_user = user
        async def answer(self, *a, **kw):
            await callback.message.answer(*a, **kw)
    await cmd_start(FakeMsg())
    await callback.answer()

@dp.callback_query(F.data == "my_referral")
async def my_referral(callback: CallbackQuery):
    user_id = callback.from_user.id
    bot_info = await bot.get_me()
    ref_count = get_referral_count(user_id)
    stars = get_stars(user_id)
    link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"

    await callback.message.edit_text(
        f"🔗 <b>Sizning referal havolangiz:</b>\n\n"
        f"<code>{link}</code>\n\n"
        f"👥 Jalb qilganlar: <b>{ref_count} kishi</b>\n"
        f"⭐ Jami Stars: <b>{stars}</b>\n\n"
        f"Havolani do'stlaringizga yuboring va har biri uchun <b>{STARS_PER_REFERRAL} ⭐</b> oling!",
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "my_stars")
async def my_stars(callback: CallbackQuery):
    user_id = callback.from_user.id
    stars = get_stars(user_id)
    ref_count = get_referral_count(user_id)

    await callback.message.edit_text(
        f"⭐ <b>Sizning Starslaringiz: {stars}</b>\n\n"
        f"👥 Referallar: <b>{ref_count} kishi</b>\n"
        f"💰 Har referal: <b>{STARS_PER_REFERRAL} Stars</b>\n\n"
        f"Stars yig'ib, Telegram Premium va boshqa xizmatlardan foydalaning!",
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "stats")
async def stats(callback: CallbackQuery):
    user_id = callback.from_user.id
    ref_count = get_referral_count(user_id)
    stars = get_stars(user_id)
    total = get_total_users()

    await callback.message.edit_text(
        f"📊 <b>Statistika</b>\n\n"
        f"👤 Sizning referallaringiz: <b>{ref_count}</b>\n"
        f"⭐ Starslaringiz: <b>{stars}</b>\n"
        f"👥 Botdagi jami foydalanuvchilar: <b>{total}</b>",
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    total = get_total_users()
    cursor.execute("SELECT SUM(stars) FROM users")
    total_stars = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM referrals")
    total_refs = cursor.fetchone()[0]

    await message.answer(
        f"🛠 <b>Admin panel</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{total}</b>\n"
        f"🔗 Jami referallar: <b>{total_refs}</b>\n"
        f"⭐ Tarqatilgan Stars: <b>{total_stars}</b>",
        parse_mode="HTML"
    )

@dp.message(Command("broadcast"))
async def broadcast(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        await message.answer("Foydalanish: /broadcast Xabar matni")
        return
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    sent = 0
    for (uid,) in users:
        try:
            await bot.send_message(uid, text, parse_mode="HTML")
            sent += 1
        except Exception:
            pass
    await message.answer(f"✅ {sent}/{len(users)} foydalanuvchiga yuborildi.")

@dp.message(Command("addstars"))
async def add_stars_cmd(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Foydalanish: /addstars <user_id> <miqdor>")
        return
    try:
        uid, amount = int(parts[1]), int(parts[2])
        add_stars(uid, amount)
        await message.answer(f"✅ {uid} ga {amount} Stars qo'shildi.")
    except ValueError:
        await message.answer("❌ Noto'g'ri format.")

async def main():
    logger.info("✅ Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
