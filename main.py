import asyncio
import random
import json
import logging
import re

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# Parser funksiyasini import qilish (faylingiz mavjudligiga ishonch hosil qiling)
try:
    from parser import get_quizzes
except ImportError:
    def get_quizzes(path):
        return []

# =========================================================
# LOGGING & CONFIG
# =========================================================
logging.basicConfig(level=logging.INFO)

TOKEN = "8636080560:AAF_rC_dscmRU0_R9z1XVZpSEgtX-6AOnh8"
QUIZ_TIME = 60

SUBJECTS = {
    "Falsafa": "Falsafa.docx",
    "MT-V-A": "Mtuzilma.docx"
}

# Telegram standart effekt IDlari
FIREWORK_EFFECT = "5046509860389126442" # Mushak effekti

SUCCESS_MESSAGES = [
    "🎉 TO‘G‘RI JAVOB!",
    "✨ SUPER!",
    "🏆 AJOYIB!",
    "🔥 ZO‘R ISH!"
]

# =========================================================
# BOT INITIALIZATION
# =========================================================
bot = Bot(token=TOKEN)
dp = Dispatcher()
user_sessions = {}

# =========================================================
# ALLOWED USERS CHECK
# =========================================================
def load_allowed_ids():
    try:
        with open("users.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return sorted(data.get("allowed_ids", []))
    except:
        return []

ALLOWED_IDS = load_allowed_ids()

def is_allowed(user_id: int):
    # Agar users.json bo'sh bo'lsa, hamma kirsin desa bo'ladi yoki faqat ro'yxatdagilar
    if not ALLOWED_IDS: return True 
    low, high = 0, len(ALLOWED_IDS) - 1
    while low <= high:
        mid = (low + high) // 2
        if ALLOWED_IDS[mid] == user_id: return True
        elif ALLOWED_IDS[mid] < user_id: low = mid + 1
        else: high = mid - 1
    return False

# =========================================================
# KEYBOARDS
# =========================================================
def get_private_menu():
    builder = ReplyKeyboardBuilder()
    for subject in SUBJECTS.keys():
        builder.add(types.KeyboardButton(text=f"📚 {subject}"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# =========================================================
# HANDLERS
# =========================================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if not is_allowed(message.from_user.id):
        return await message.answer("🚫 Ruxsat yo‘q!")
    
    await message.answer(
        "🎓 TEST BOT\n📚 Fan tanlang:",
        reply_markup=get_private_menu()
    )

@dp.message(F.text.startswith("📚 "))
async def choose_count(message: types.Message):
    if not is_allowed(message.from_user.id): return
    
    subject_name = message.text.replace("📚 ", "").strip()
    file_path = SUBJECTS.get(subject_name)

    if not file_path:
        return await message.answer("❌ Fan topilmadi!")

    all_tests = get_quizzes(file_path)
    total_count = len(all_tests)

    builder = ReplyKeyboardBuilder()
    for count in [25, 30, 35, 40]:
        if count <= total_count:
            builder.add(types.KeyboardButton(text=f"⚙️ {subject_name}:{count}"))

    builder.add(types.KeyboardButton(text=f"🚀 {subject_name} - Barchasi ({total_count})"))
    builder.add(types.KeyboardButton(text="⬅️ Orqaga"))
    builder.adjust(2)

    await message.answer(
        f"🎯 {subject_name}\n📊 Jami savollar: {total_count}\nNechta test yechasiz?",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

@dp.message(F.text == "⬅️ Orqaga")
async def back_menu(message: types.Message):
    await cmd_start(message)

@dp.message(F.text.startswith("⚙️ ") | F.text.startswith("🚀 "))
async def init_quiz(message: types.Message):
    user_id = message.from_user.id
    if not is_allowed(user_id): return

    try:
        if message.text.startswith("🚀 "):
            subject = message.text.split("🚀 ")[1].split(" - ")[0].strip()
            count_match = re.search(r"\((\d+)\)", message.text)
            count = int(count_match.group(1))
        else:
            raw = message.text.replace("⚙️ ", "")
            subject, c = raw.split(":")
            count = int(c)

        all_tests = get_quizzes(SUBJECTS[subject])
        selected = random.sample(all_tests, min(count, len(all_tests)))

        user_sessions[user_id] = {
            "subject": subject,
            "tests": selected,
            "current_index": 0,
            "correct_answers": 0,
            "current_poll_id": None
        }

        stop_btn = ReplyKeyboardBuilder()
        stop_btn.add(types.KeyboardButton(text="🛑 Testni to'xtatish"))

        await message.answer(
            f"🚀 TEST BOSHLANDI!\n📚 {subject}\n🔢 Savollar soni: {len(selected)} ta",
            reply_markup=stop_btn.as_markup(resize_keyboard=True)
        )
        
        await asyncio.sleep(1)
        await send_next_test(user_id)

    except Exception as e:
        await message.answer(f"Xatolik yuz berdi: {e}")

@dp.message(F.text == "🛑 Testni to'xtatish")
async def stop_quiz(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
        await message.answer("🛑 Test to‘xtatildi.", reply_markup=get_private_menu())
    else:
        await message.answer("❌ Aktiv test mavjud emas.")

# =========================================================
# CORE LOGIC
# =========================================================
async def send_next_test(user_id):
    session = user_sessions.get(user_id)
    if not session: return

    idx = session["current_index"]
    tests = session["tests"]
    total = len(tests)

    if idx >= total:
        return await show_results(user_id)

    q = tests[idx]
    options = list(q["options"])
    correct_text = options[q["correct"]]
    
    random.shuffle(options)
    correct_id = options.index(correct_text)
    session["current_correct_id"] = correct_id

    # Savol tartib raqamini yuborish
    await bot.send_message(user_id, f"<b>Savol {idx + 1}/{total}</b>", parse_mode="HTML")

    poll = await bot.send_poll(
        chat_id=user_id,
        question=f"{q['question']}"[:300],
        options=options,
        correct_option_id=correct_id,
        type="quiz",
        is_anonymous=False,
        open_period=QUIZ_TIME
    )
    session["current_poll_id"] = poll.poll.id

@dp.poll_answer()
async def handle_poll_answer(poll_answer: types.PollAnswer):
    user_id = poll_answer.user.id
    session = user_sessions.get(user_id)

    if not session or poll_answer.poll_id != session["current_poll_id"]:
        return

    selected = poll_answer.option_ids[0]
    
    if selected == session["current_correct_id"]:
        session["correct_answers"] += 1
        await bot.send_message(
            user_id, 
            random.choice(SUCCESS_MESSAGES),
            message_effect_id=FIREWORK_EFFECT
        )
    else:
        await bot.send_message(user_id, "❌ Noto‘g‘ri javob!")

    session["current_index"] += 1
    await asyncio.sleep(1.5) # Keyingi savolgacha biroz kutish
    await send_next_test(user_id)

async def show_results(user_id):
    session = user_sessions.get(user_id)
    if not session: return

    correct = session["correct_answers"]
    total = len(session["tests"])
    score = (correct / total) * 40

    await bot.send_message(
        user_id,
        f"🏁 <b>TEST TUGADI</b>\n\n"
        f"✅ To‘g‘ri javob: {correct}\n"
        f"❌ Noto‘g‘ri javob: {total - correct}\n"
        f"📊 Umumiy ball: {score:.1f}/40",
        parse_mode="HTML",
        message_effect_id=FIREWORK_EFFECT,
        reply_markup=get_private_menu()
    )
    del user_sessions[user_id]

# =========================================================
# MAIN RUNNER
# =========================================================
async def main():
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi")
