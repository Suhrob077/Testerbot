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
TOKEN = "8636080560:AAF_rC_dscmRU0_R9z1XVZpSEgtX-6AOnh8"

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
# LOAD USERS
# =========================================================
def load_allowed_ids():

    try:
        with open(
            "users.json",
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

            return sorted(
                data.get("allowed_ids", [])
            )

    except:
        return []

ALLOWED_IDS = load_allowed_ids()

# =========================================================
# BINARY SEARCH
# =========================================================
def is_allowed(user_id: int):

    low = 0
    high = len(ALLOWED_IDS) - 1

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
# PRIVATE MENU
# =========================================================
def get_private_menu():

    builder = ReplyKeyboardBuilder()

    for subject in SUBJECTS.keys():

        builder.add(
            types.KeyboardButton(
                text=f"📚 {subject}"
            )
        )

    builder.adjust(2)

    return builder.as_markup(
        resize_keyboard=True
    )

# =========================================================
# START
# =========================================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):

    user_id = message.from_user.id

    if not is_allowed(user_id):

        return await message.answer(
            f"🚫 Sizga ruxsat yo'q!\n\n"
            f"🆔 `{user_id}`",
            parse_mode="Markdown"
        )

    await message.answer(
        "🎓 TEST BOTIGA XUSH KELIBSIZ!\n\n"
        "📚 Fan tanlang:",
        reply_markup=get_private_menu()
    )

# =========================================================
# SUBJECT
# =========================================================
@dp.message(F.text.startswith("📚 "))
async def choose_count(message: types.Message):

    user_id = message.from_user.id

    if not is_allowed(user_id):
        return

    subject_name = message.text.replace(
        "📚 ",
        ""
    ).strip()

    file_path = SUBJECTS.get(subject_name)

    if not file_path:
        return await message.answer(
            "❌ Fan topilmadi!"
        )

    all_tests = get_quizzes(file_path)

    total_count = len(all_tests)

    if total_count == 0:
        return await message.answer(
            "❌ Savollar topilmadi!"
        )

    builder = ReplyKeyboardBuilder()

    for count in [25, 30, 35, 40]:

        if count <= total_count:

            builder.add(
                types.KeyboardButton(
                    text=f"⚙️ {subject_name}:{count}"
                )
            )

    builder.add(
        types.KeyboardButton(
            text=f"🚀 {subject_name} - Barchasi ({total_count})"
        )
    )

    builder.add(
        types.KeyboardButton(
            text="⬅️ Orqaga"
        )
    )

    builder.adjust(2)

    await message.answer(
        f"🎯 {subject_name}\n\n"
        f"📊 Jami savollar: {total_count}\n\n"
        f"Nechta ishlamoqchisiz?",
        reply_markup=builder.as_markup(
            resize_keyboard=True,
            one_time_keyboard=True
        )
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
@dp.message(
    F.text.startswith("⚙️ ") |
    F.text.startswith("🚀 ")
)
async def init_quiz(message: types.Message):

    user_id = message.from_user.id

    if not is_allowed(user_id):
        return

    try:

        # ======================================
        # PARSE
        # ======================================
        if message.text.startswith("🚀 "):

            parts = message.text.replace(
                "🚀 ",
                ""
            ).split(" - ")

            subject = parts[0].strip()

            count_match = re.search(
                r"\((\d+)\)",
                message.text
            )

            count = int(
                count_match.group(1)
            )

        else:

            raw = message.text.replace(
                "⚙️ ",
                ""
            )

            parts = raw.split(":")

            subject = parts[0].strip()

            count = int(parts[1])

        # ======================================
        # TESTS
        # ======================================
        if subject not in SUBJECTS:

            return await message.answer(
                "❌ Fan topilmadi!"
            )

        all_tests = get_quizzes(
            SUBJECTS[subject]
        )

        if not all_tests:

            return await message.answer(
                "❌ Savollar topilmadi!"
            )

        selected_tests = random.sample(
            all_tests,
            min(count, len(all_tests))
        )

        # ======================================
        # SESSION
        # ======================================
        user_sessions[user_id] = {

            "user_id": user_id,

            "subject": subject,

            "tests": selected_tests,

            "current_index": 0,

            "correct_answers": 0,

            "timer_task": None
        }

        # ======================================
        # STOP BUTTON
        # ======================================
        stop_builder = ReplyKeyboardBuilder()

        stop_builder.add(
            types.KeyboardButton(
                text="🛑 Testni to'xtatish"
            )
        )

        await message.answer(
            f"🚀 TEST BOSHLANDI!\n\n"
            f"📚 Fan: {subject}\n"
            f"📊 Savollar: {len(selected_tests)}\n"
            f"⏳ Har savol: {QUIZ_TIME} sekund\n\n"
            f"🔥 Omad tilaymiz!"
            ,
            reply_markup=stop_builder.as_markup(
                resize_keyboard=True
            )
        )

        await asyncio.sleep(1)

        await send_next_test(user_id)

    except Exception as e:

        logging.error(e)

        await message.answer(
            f"⚠️ Xatolik:\n{e}"
        )

# =========================================================
# STOP QUIZ
# =========================================================
@dp.message(F.text == "🛑 Testni to'xtatish")
async def stop_quiz(message: types.Message):

    user_id = message.from_user.id

    session = user_sessions.get(user_id)

    if not session:

        return await message.answer(
            "❌ Aktiv test yo'q!"
        )

    if session["timer_task"]:
        session["timer_task"].cancel()

    del user_sessions[user_id]

    await message.answer(
        "🛑 Test to'xtatildi!",
        reply_markup=get_private_menu()
    )

# =========================================================
# SEND NEXT TEST
# =========================================================
async def send_next_test(user_id):

    session = user_sessions.get(user_id)

    if not session:
        return

    idx = session["current_index"]

    tests = session["tests"]

    # FINISH
    if idx >= len(tests):
        return await show_results(user_id)

    q_data = tests[idx]

    options = list(q_data["options"])

    correct_text = options[
        q_data["correct"]
    ]

    random.shuffle(options)

    new_correct_id = options.index(
        correct_text
    )

    session[
        "current_correct_id"
    ] = new_correct_id

    question = (
        f"❓ Savol {idx+1}/{len(tests)}\n\n"
        f"{q_data['question']}"
    )

    poll_message = await bot.send_poll(
        chat_id=user_id,

        question=question[:300],

        options=options,

        correct_option_id=new_correct_id,

        type="quiz",

        is_anonymous=False,

        open_period=QUIZ_TIME
    )

    session[
        "current_poll_id"
    ] = poll_message.poll.id

    session["timer_task"] = asyncio.create_task(
        wait_for_timeout(
            user_id,
            idx
        )
    )

# =========================================================
# TIMEOUT
# =========================================================
async def wait_for_timeout(
    user_id,
    index
):

    await asyncio.sleep(QUIZ_TIME + 1)

    session = user_sessions.get(user_id)

    if not session:
        return

    if session["current_index"] == index:

        session["current_index"] += 1

        await bot.send_message(
            user_id,
            "⌛ Vaqt tugadi!"
        )

        await send_next_test(user_id)

# =========================================================
# POLL ANSWER
# =========================================================
@dp.poll_answer()
async def handle_poll_answer(
    poll_answer: types.PollAnswer
):

    user_id = poll_answer.user.id

    session = user_sessions.get(user_id)

    if not session:
        return

    if poll_answer.poll_id != session.get(
        "current_poll_id"
    ):
        return

    selected = poll_answer.option_ids[0]

    # ======================================
    # CHECK ANSWER
    # ======================================
    if selected == session["current_correct_id"]:

        session["correct_answers"] += 1

        await bot.send_message(
            user_id,

            "🎉 TO‘G‘RI JAVOB! 🎉\n\n"
            "✨ Ajoyib!\n"
            "🔥 Davom eting!\n"
            "🏆 Siz zo'rsiz!\n"
            "🎊 🎊 🎊"
        )

    else:

        await bot.send_message(
            user_id,

            "❌ Noto‘g‘ri javob!\n\n"
            "💪 Keyingi savolda omad!"
        )

    # NEXT
    if session["timer_task"]:
        session["timer_task"].cancel()

    session["current_index"] += 1

    await asyncio.sleep(1)

    await send_next_test(user_id)

# =========================================================
# RESULTS
# =========================================================
async def show_results(user_id):

    session = user_sessions.get(user_id)

    if not session:
        return

    correct = session["correct_answers"]

    total = len(session["tests"])

    score = (
        correct / total
    ) * 40

    if score >= 35:

        rank = "👑 SUPER!"
        celebration = "🎆 🎇 🏆 🎊"

    elif score >= 25:

        rank = "🔥 ZO'R!"
        celebration = "🎉 🎉 🎉"

    else:

        rank = "💪 YAXSHI!"
        celebration = "✨ ✨ ✨"

    result_text = (
        f"{celebration}\n\n"

        f"🏁 TEST TUGADI!\n\n"

        f"{rank}\n\n"

        f"✅ To'g'ri: {correct}\n"

        f"❌ Xato: {total-correct}\n"

        f"📊 Ball: {score:.1f}/40\n\n"

        f"🚀 Davom etishda davom eting!"
    )

    await bot.send_message(
        user_id,
        result_text,
        reply_markup=get_private_menu()
    )

    del user_sessions[user_id]

# =========================================================
# MAIN
# =========================================================
async def main():

    print("✅ BOT ISHGA TUSHDI!")

    await dp.start_polling(bot)

# =========================================================
# RUN
# =========================================================
if __name__ == "__main__":
    asyncio.run(main())
