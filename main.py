import asyncio
import random
import json
import logging
import re

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from parser import get_quizzes

# =========================================================
# LOGGING
# =========================================================
logging.basicConfig(level=logging.INFO)

# =========================================================
# TOKEN
# =========================================================
TOKEN = "YOUR_BOT_TOKEN"

# =========================================================
# SETTINGS
# =========================================================
QUIZ_TIME = 60

SUBJECTS = {
    "Falsafa": "Falsafa.docx",
    "MT-V-A": "Mtuzilma.docx"
}

# =========================================================
# BOT
# =========================================================
bot = Bot(token=TOKEN)
dp = Dispatcher()

# =========================================================
# STORAGE
# =========================================================
user_sessions = {}

# =========================================================
# EFFECTS
# =========================================================
FIREWORK_EFFECT = "5046509860389126442"

RAIN_EMOJIS = [
    "🎉", "✨", "🔥", "🏆", "💥",
    "🌟", "🎊", "⚡", "👑", "🚀",
    "💫", "🎯", "🥇", "💎", "🎆"
]

SUCCESS_MESSAGES = [
    "🎉 TO‘G‘RI JAVOB!",
    "✨ SUPER!",
    "🎇 PERFECT!",
    "🏆 AJOYIB!",
    "💥 ZO‘R ISH!"
]

# =========================================================
# USERS
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
    low, high = 0, len(ALLOWED_IDS) - 1

    while low <= high:
        mid = (low + high) // 2
        if ALLOWED_IDS[mid] == user_id:
            return True
        elif ALLOWED_IDS[mid] < user_id:
            low = mid + 1
        else:
            high = mid - 1
    return False

# =========================================================
# MENU
# =========================================================
def get_private_menu():
    builder = ReplyKeyboardBuilder()

    for subject in SUBJECTS.keys():
        builder.add(types.KeyboardButton(text=f"📚 {subject}"))

    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# =========================================================
# START
# =========================================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):

    if not is_allowed(message.from_user.id):
        return await message.answer("🚫 Ruxsat yo‘q!")

    await message.answer(
        "🎓 TEST BOT\n📚 Fan tanlang:",
        reply_markup=get_private_menu()
    )

# =========================================================
# 🌧️ EMOJI RAIN
# =========================================================
async def emoji_rain(chat_id: int, count: int = 5):
    for _ in range(count):
        line = " ".join(random.choice(RAIN_EMOJIS) for _ in range(12))
        await bot.send_message(chat_id, line)
        await asyncio.sleep(0.2)

# =========================================================
# SUBJECT
# =========================================================
@dp.message(F.text.startswith("📚 "))
async def choose_count(message: types.Message):

    user_id = message.from_user.id

    if not is_allowed(user_id):
        return

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
        f"🎯 {subject_name}\n📊 Savollar: {total_count}",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

# =========================================================
# BACK
# =========================================================
@dp.message(F.text == "⬅️ Orqaga")
async def back_menu(message: types.Message):
    await cmd_start(message)

# =========================================================
# INIT QUIZ
# =========================================================
@dp.message(F.text.startswith("⚙️ ") | F.text.startswith("🚀 "))
async def init_quiz(message: types.Message):

    user_id = message.from_user.id

    if not is_allowed(user_id):
        return

    try:

        if message.text.startswith("🚀 "):
            parts = message.text.replace("🚀 ", "").split(" - ")
            subject = parts[0].strip()

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
            "timer_task": None
        }

        stop_btn = ReplyKeyboardBuilder()
        stop_btn.add(types.KeyboardButton(text="🛑 Testni to'xtatish"))

        await message.answer(
            f"🚀 TEST BOSHLANDI!\n📚 {subject}\n🔥 Omad!",
            reply_markup=stop_btn.as_markup(resize_keyboard=True)
        )

        await asyncio.sleep(1)
        await send_next_test(user_id)

    except Exception as e:
        await message.answer(f"Xatolik: {e}")

# =========================================================
# STOP
# =========================================================
@dp.message(F.text == "🛑 Testni to'xtatish")
async def stop_quiz(message: types.Message):

    user_id = message.from_user.id
    session = user_sessions.get(user_id)

    if not session:
        return await message.answer("❌ Aktiv test yo‘q!")

    if session["timer_task"]:
        session["timer_task"].cancel()

    del user_sessions[user_id]

    await message.answer("🛑 To‘xtatildi", reply_markup=get_private_menu())

# =========================================================
# SEND QUESTION
# =========================================================
async def send_next_test(user_id):

    session = user_sessions.get(user_id)
    if not session:
        return

    idx = session["current_index"]
    tests = session["tests"]

    if idx >= len(tests):
        return await show_results(user_id)

    q = tests[idx]

    options = list(q["options"])
    correct = options[q["correct"]]

    random.shuffle(options)
    correct_id = options.index(correct)

    session["current_correct_id"] = correct_id

    poll = await bot.send_poll(
        chat_id=user_id,
        question=f"❓ {q['question']}"[:300],
        options=options,
        correct_option_id=correct_id,
        type="quiz",
        is_anonymous=False,
        open_period=QUIZ_TIME
    )

    session["current_poll_id"] = poll.poll.id

# =========================================================
# ANSWER CHECK (🔥 UPDATED)
# =========================================================
@dp.poll_answer()
async def handle_poll_answer(poll_answer: types.PollAnswer):

    user_id = poll_answer.user.id
    session = user_sessions.get(user_id)

    if not session:
        return

    if poll_answer.poll_id != session["current_poll_id"]:
        return

    selected = poll_answer.option_ids[0]

    if selected == session["current_correct_id"]:

        session["correct_answers"] += 1

        await bot.send_message(
            user_id,
            random.choice(SUCCESS_MESSAGES),
            message_effect_id=FIREWORK_EFFECT
        )

        await emoji_rain(user_id, 5)

    else:
        await bot.send_message(user_id, "❌ Noto‘g‘ri!")

    session["current_index"] += 1
    await asyncio.sleep(1)
    await send_next_test(user_id)

# =========================================================
# RESULTS
# =========================================================
async def show_results(user_id):

    session = user_sessions[user_id]

    correct = session["correct_answers"]
    total = len(session["tests"])

    score = (correct / total) * 40

    await bot.send_message(
        user_id,
        f"""
🏁 TEST TUGADI

✅ To‘g‘ri: {correct}
❌ Xato: {total-correct}
📊 Ball: {score:.1f}/40

🔥 Yaxshi ish!
        """,
        message_effect_id=FIREWORK_EFFECT,
        reply_markup=get_private_menu()
    )

    del user_sessions[user_id]

# =========================================================
# MAIN
# =========================================================
async def main():
    print("BOT ISHGA TUSHDI 🚀")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
