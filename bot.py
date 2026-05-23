import logging
import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)

# ============================================================
BOT_TOKEN = "8707735340:AAHSvRn1da2rO9FSTw_fsVsoEoXV5p_Od2Y"
CHANNEL_ID = "@DARVINGAMER_RASMIY"
CHANNEL_LINK = "https://t.me/DARVINGAMER_RASMIY"
STARS_PER_REFERRAL = 5
ADMIN_IDS = [8408160535]
# ============================================================

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

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
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()

def add_user(user_id, username, full_name, referred_by=None):
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id,username,full_name,referred_by) VALUES (?,?,?,?)",
        (user_id, username, full_name, referred_by)
    )
    conn.commit()

def add_stars(user_id, amount):
    cursor.execute("UPDATE users SET stars=stars+? WHERE user_id=?", (amount, user_id))
    conn.commit()

def get_stars(user_id):
    cursor.execute("SELECT stars FROM users WHERE user_id=?", (user_id,))
    r = cursor.fetchone()
    return r[0] if r else 0

def get_ref_count(user_id):
    cursor.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (user_id,))
    return cursor.fetchone()[0]

def get_total_users():
    cursor.execute("SELECT COUNT(*) FROM users")
    return cursor.fetchone()[0]

async def is_subscribed(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status not in ["kicked", "left"]
    except:
        return False

def sub_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📢 Kanalga obuna bo'lish", url=CHANNEL_LINK))
    kb.add(InlineKeyboardButton("✅ Obuna bo'ldim, tekshir", callback_data="check_sub"))
    return kb

def main_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔗 Mening referal havolam", callback_data="my_referral"))
    kb.add(InlineKeyboardButton("⭐ Mening Starslarim", callback_data="my_stars"))
    kb.add(InlineKeyboardButton("📊 Statistika", callback_data="stats"))
    return kb

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    user = message.from_user
    args = message.get_args()
    referred_by = None

    if args.startswith("ref_"):
        try:
            referred_by = int(args[4:])
            if referred_by == user.id:
                referred_by = None
        except:
            referred_by = None

    is_new = get_user(user.id) is None
    add_user(user.id, user.username or "", user.full_name, referred_by)

    if not await is_subscribed(user.id):
        await message.answer(
            f"👋 Salom, <b>{user.full_name}</b>!\n\n"
            "⚠️ Botdan foydalanish uchun avval kanalimizga obuna bo'ling!\n\n"
            f"📢 <b>{CHANNEL_LINK}</b>",
            reply_markup=sub_keyboard()
        )
        return

    if is_new and referred_by:
        referrer = get_user(referred_by)
        if referrer:
            add_stars(referred_by, STARS_PER_REFERRAL)
            cursor.execute(
                "INSERT INTO referrals (referrer_id,referred_id,stars_given) VALUES (?,?,?)",
                (referred_by, user.id, STARS_PER_REFERRAL)
            )
            conn.commit()
            try:
                await bot.send_message(
                    referred_by,
                    f"🎉 <b>Yangi referal!</b>\n\n"
                    f"👤 <b>{user.full_name}</b> sizning havolangiz orqali qo'shildi.\n"
                    f"⭐ <b>+{STARS_PER_REFERRAL} Stars</b> qo'shildi!"
                )
            except:
                pass

    me = await bot.get_me()
    stars = get_stars(user.id)
    ref_count = get_ref_count(user.id)

    await message.answer(
        f"✅ <b>Xush kelibsiz, {user.full_name}!</b>\n\n"
        f"⭐ Starslaringiz: <b>{stars}</b>\n"
        f"👥 Referallaringiz: <b>{ref_count} kishi</b>\n\n"
        f"🔗 Sizning referal havolangiz:\n"
        f"<code>https://t.me/{me.username}?start=ref_{user.id}</code>\n\n"
        f"Har bir do'stingiz uchun <b>{STARS_PER_REFERRAL} ⭐ Stars</b> olasiz!",
        reply_markup=main_keyboard()
    )

@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def check_sub(callback: types.CallbackQuery):
    user = callback.from_user
    if not await is_subscribed(user.id):
        await callback.answer("❌ Hali obuna bo'lmadingiz!", show_alert=True)
        return
    await callback.message.delete()
    await cmd_start(callback.message)
    callback.message.from_user = user
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "my_referral")
async def my_referral(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    me = await bot.get_me()
    ref_count = get_ref_count(user_id)
    stars = get_stars(user_id)
    link = f"https://t.me/{me.username}?start=ref_{user_id}"
    await callback.message.edit_text(
        f"🔗 <b>Sizning referal havolangiz:</b>\n\n"
        f"<code>{link}</code>\n\n"
        f"👥 Jalb qilganlar: <b>{ref_count} kishi</b>\n"
        f"⭐ Jami Stars: <b>{stars}</b>\n\n"
        f"Har bir yangi a'zo uchun <b>{STARS_PER_REFERRAL} ⭐</b> olasiz!",
        reply_markup=main_keyboard()
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "my_stars")
async def my_stars(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    stars = get_stars(user_id)
    ref_count = get_ref_count(user_id)
    await callback.message.edit_text(
        f"⭐ <b>Sizning Starslaringiz: {stars}</b>\n\n"
        f"👥 Referallar: <b>{ref_count} kishi</b>\n"
        f"💰 Har referal: <b>{STARS_PER_REFERRAL} Stars</b>",
        reply_markup=main_keyboard()
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "stats")
async def stats(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    ref_count = get_ref_count(user_id)
    stars = get_stars(user_id)
    total = get_total_users()
    await callback.message.edit_text(
        f"📊 <b>Statistika</b>\n\n"
        f"👤 Sizning referallaringiz: <b>{ref_count}</b>\n"
        f"⭐ Starslaringiz: <b>{stars}</b>\n"
        f"👥 Botdagi jami foydalanuvchilar: <b>{total}</b>",
        reply_markup=main_keyboard()
    )
    await callback.answer()

@dp.message_handler(commands=["admin"])
async def admin_panel(message: types.Message):
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
        f"⭐ Tarqatilgan Stars: <b>{total_stars}</b>"
    )

@dp.message_handler(commands=["broadcast"])
async def broadcast(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    text = message.get_args()
    if not text:
        await message.answer("Foydalanish: /broadcast Xabar matni")
        return
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    sent = 0
    for (uid,) in users:
        try:
            await bot.send_message(uid, text)
            sent += 1
        except:
            pass
    await message.answer(f"✅ {sent}/{len(users)} ga yuborildi.")

@dp.message_handler(commands=["addstars"])
async def addstars(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = message.get_args().split()
    if len(parts) != 2:
        await message.answer("Foydalanish: /addstars <user_id> <miqdor>")
        return
    try:
        uid, amount = int(parts[0]), int(parts[1])
        add_stars(uid, amount)
        await message.answer(f"✅ {uid} ga {amount} Stars qo'shildi.")
    except:
        await message.answer("❌ Noto'g'ri format.")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)

