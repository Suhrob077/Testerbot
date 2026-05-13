import asyncio
import random
import json
import logging

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.enums import ChatMemberStatus

from parser import get_quizzes

# =========================================================
# LOGGING
# =========================================================
logging.basicConfig(level=logging.INFO)

# =========================================================
# TOKEN
# =========================================================
TOKEN = "BOT_TOKENINGIZ"

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
# SESSIONS
# =========================================================
user_sessions = {}

# GURUHDA AKTIV TEST
group_active_quizzes = {}

# =========================================================
# USERS
# =========================================================
def load_allowed_ids():
    try:
        with open("users.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return sorted(data.get("allowed_ids", []))

    except (FileNotFoundError, json.JSONDecodeError):
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
# MENU
# =========================================================
def get_main_menu():

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
# SESSION KEY
# =========================================================
def get_session_key(user_id, chat_id):
    return f"{user_id}_{chat_id}"

# =========================================================
# ADMIN CHECK
# =========================================================
async def is_admin(chat_id: int, user_id: int):

    try:
        member = await bot.get_chat_member(
            chat_id,
            user_id
        )

        return member.status in [
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR
        ]

    except:
        return False

# =========================================================
# START
# =========================================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):

    user_id = message.from_user.id
    chat_id = message.chat.id

    if not is_allowed(user_id):

        return await message.answer(
            f"🚫 Sizga ruxsat berilmagan!\n\n"
            f"🆔 ID: `{user_id}`",
            parse_mode="Markdown"
        )

    # GURUHDA TEST BORMI
    if chat_id in group_active_quizzes:

        active = group_active_quizzes[chat_id]

        return await message.answer(
            f"⚠️ Guruhda aktiv test mavjud!\n\n"
            f"👤 Boshlagan: {active['starter_name']}"
        )

    await message.answer(
        "👋 Salom!\n\n"
        "📚 Fanlardan birini tanlang:",
        reply_markup=get_main_menu()
    )

# =========================================================
# SUBJECT
# =========================================================
@dp.message(F.text.startswith("📚 "))
async def choose_count(message: types.Message):

    user_id = message.from_user.id
    chat_id = message.chat.id

    if not is_allowed(user_id):
        return

    # GURUHDA AKTIV TEST
    if chat_id in group_active_quizzes:

        active = group_active_quizzes[chat_id]

        return await message.answer(
            f"⚠️ Test davom etmoqda!\n\n"
            f"👤 {active['starter_name']}"
        )

    subject_name = message.text.replace("📚 ", "").strip()

    file_path = SUBJECTS.get(subject_name)

    if not file_path:
        return await message.answer("❌ Fan topilmadi!")

    all_tests = get_quizzes(file_path)

    total_count = len(all_tests)

    if total_count == 0:
        return await message.answer("❌ Testlar topilmadi!")

    builder = ReplyKeyboardBuilder()

    counts = [25, 30, 35, 40]

    for count in counts:

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

    markup = builder.as_markup(
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await message.answer(
        f"🎯 {subject_name}\n\n"
        f"📊 Jami savollar: {total_count}\n\n"
        f"Nechta ishlamoqchisiz?",
        reply_markup=markup
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
    chat_id = message.chat.id

    if not is_allowed(user_id):
        return

    # GURUHDA TEST BOR
    if chat_id in group_active_quizzes:

        active = group_active_quizzes[chat_id]

        return await message.answer(
            f"⚠️ Test davom etmoqda!\n\n"
            f"👤 {active['starter_name']}"
        )

    try:

        # ==========================================
        # COUNT
        # ==========================================
        if message.text.startswith("🚀 "):

            import re

            parts = message.text.replace(
                "🚀 ",
                ""
            ).split(" - ")

            subject = parts[0].strip()

            count_match = re.search(
                r"\((\d+)\)",
                message.text
            )

            count = int(count_match.group(1))

        else:

            raw = message.text.replace(
                "⚙️ ",
                ""
            )

            parts = raw.split(":")

            subject = parts[0].strip()

            count = int(parts[1])

        # ==========================================
        # SUBJECT
        # ==========================================
        if subject not in SUBJECTS:
            return await message.answer(
                "❌ Fan topilmadi!"
            )

        all_tests = get_quizzes(
            SUBJECTS[subject]
        )

        if not all_tests:
            return await message.answer(
                "❌ Test topilmadi!"
            )

        selected_tests = random.sample(
            all_tests,
            min(count, len(all_tests))
        )

        session_key = get_session_key(
            user_id,
            chat_id
        )

        # ==========================================
        # SESSION
        # ==========================================
        user_sessions[session_key] = {

            "user_id": user_id,

            "chat_id": chat_id,

            "starter_name": message.from_user.full_name,

            "subject": subject,

            "tests": selected_tests,

            "current_index": 0,

            "correct_answers": 0,

            "timer_task": None,

            "participants": {}
        }

        # ==========================================
        # GROUP ACTIVE
        # ==========================================
        if message.chat.type in [
            "group",
            "supergroup"
        ]:

            group_active_quizzes[chat_id] = {

                "session_key": session_key,

                "starter_id": user_id,

                "starter_name": message.from_user.full_name
            }

        # ==========================================
        # STOP BUTTON
        # ==========================================
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
            f"⏳ Har savol: {QUIZ_TIME} sekund",
            reply_markup=stop_builder.as_markup(
                resize_keyboard=True
            )
        )

        await asyncio.sleep(1)

        await send_next_test(session_key)

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
    chat_id = message.chat.id

    found_session = None

    for key, session in user_sessions.items():

        if session["chat_id"] == chat_id:

            found_session = key

            break

    if not found_session:
        return await message.answer(
            "❌ Aktiv test yo'q!"
        )

    session = user_sessions[found_session]

    allowed = False

    # TEST OWNER
    if session["user_id"] == user_id:
        allowed = True

    # ADMIN
    elif await is_admin(chat_id, user_id):
        allowed = True

    if not allowed:

        return await message.answer(
            "🚫 Faqat admin yoki testni boshlagan odam to'xtata oladi!"
        )

    # TIMER CANCEL
    if session["timer_task"]:
        session["timer_task"].cancel()

    # DELETE
    del user_sessions[found_session]

    if chat_id in group_active_quizzes:
        del group_active_quizzes[chat_id]

    await message.answer(
        "🛑 Test to'xtatildi!",
        reply_markup=get_main_menu()
    )

# =========================================================
# SEND TEST
# =========================================================
async def send_next_test(session_key):

    session = user_sessions.get(session_key)

    if not session:
        return

    idx = session["current_index"]

    tests = session["tests"]

    chat_id = session["chat_id"]

    # ==========================================
    # FINISH
    # ==========================================
    if idx >= len(tests):
        return await show_results(session_key)

    q_data = tests[idx]

    options = list(q_data["options"])

    correct_text = options[q_data["correct"]]

    random.shuffle(options)

    new_correct_id = options.index(correct_text)

    session["current_correct_id"] = new_correct_id

    question = (
        f"❓ Savol {idx+1}/{len(tests)}\n\n"
        f"{q_data['question']}"
    )

    poll_message = await bot.send_poll(
        chat_id=chat_id,
        question=question[:300],
        options=options,
        correct_option_id=new_correct_id,
        type="quiz",
        is_anonymous=False,
        open_period=QUIZ_TIME
    )

    session["current_poll_id"] = poll_message.poll.id

    session["timer_task"] = asyncio.create_task(
        wait_for_timeout(session_key, idx)
    )

# =========================================================
# TIMEOUT
# =========================================================
async def wait_for_timeout(session_key, index):

    await asyncio.sleep(QUIZ_TIME + 1)

    session = user_sessions.get(session_key)

    if not session:
        return

    if session["current_index"] == index:

        session["current_index"] += 1

        await bot.send_message(
            session["chat_id"],
            "⌛ Vaqt tugadi!"
        )

        await send_next_test(session_key)

# =========================================================
# POLL ANSWER
# =========================================================
@dp.poll_answer()
async def handle_poll_answer(
    poll_answer: types.PollAnswer
):

    user_id = poll_answer.user.id

    for session_key, session in user_sessions.items():

        if poll_answer.poll_id != session.get("current_poll_id"):
            continue

        selected = poll_answer.option_ids[0]

        # ==========================================
        # PARTICIPANT
        # ==========================================
        if user_id not in session["participants"]:

            session["participants"][user_id] = {

                "name": poll_answer.user.full_name,

                "correct": 0,

                "wrong": 0
            }

        participant = session["participants"][user_id]

        # ==========================================
        # CHECK ANSWER
        # ==========================================
        if selected == session["current_correct_id"]:

            participant["correct"] += 1

        else:

            participant["wrong"] += 1

        # ==========================================
        # TEST OWNER SCORE
        # ==========================================
        if user_id == session["user_id"]:

            if selected == session["current_correct_id"]:
                session["correct_answers"] += 1

        # ==========================================
        # NEXT QUESTION
        # ==========================================
        if session["timer_task"]:
            session["timer_task"].cancel()

        session["current_index"] += 1

        await asyncio.sleep(0.5)

        await send_next_test(session_key)

        break

# =========================================================
# RESULTS
# =========================================================
async def show_results(session_key):

    session = user_sessions.get(session_key)

    if not session:
        return

    chat_id = session["chat_id"]

    correct = session["correct_answers"]

    total = len(session["tests"])

    score = (correct / total) * 40

    # ==========================================
    # RESULT TEXT
    # ==========================================
    result_text = (
        f"🏁 TEST TUGADI!\n\n"

        f"👤 {session['starter_name']}\n\n"

        f"✅ To'g'ri: {correct}\n"

        f"❌ Xato: {total - correct}\n"

        f"📊 Ball: {score:.1f}/40\n"
    )

    # ==========================================
    # STATISTICS
    # ==========================================
    if session["participants"]:

        result_text += "\n📈 GURUH STATISTIKASI\n"

        sorted_users = sorted(
            session["participants"].values(),
            key=lambda x: x["correct"],
            reverse=True
        )

        for i, user in enumerate(sorted_users, start=1):

            total_answers = (
                user["correct"] +
                user["wrong"]
            )

            # 40 BALL SYSTEM
            if total_answers in [25, 30, 35, 40]:

                ball = (
                    user["correct"] /
                    total_answers
                ) * 40

                result_text += (
                    f"\n{i}. {user['name']}\n"
                    f"✅ {user['correct']} | "
                    f"❌ {user['wrong']} | "
                    f"📊 {ball:.1f}/40\n"
                )

            else:

                result_text += (
                    f"\n{i}. {user['name']}\n"
                    f"✅ {user['correct']} | "
                    f"❌ {user['wrong']}\n"
                )

    # ==========================================
    # PRIVATE CHAT
    # ==========================================
    if chat_id == session["user_id"]:

        await bot.send_message(
            chat_id,
            result_text,
            reply_markup=get_main_menu()
        )

    # ==========================================
    # GROUP
    # ==========================================
    else:

        await bot.send_message(
            chat_id,
            result_text
        )

    # ==========================================
    # CLEAN
    # ==========================================
    if chat_id in group_active_quizzes:
        del group_active_quizzes[chat_id]

    if session_key in user_sessions:
        del user_sessions[session_key]

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
