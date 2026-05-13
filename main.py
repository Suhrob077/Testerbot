import asyncio
import random
import json
import logging
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)

# --- SOZLAMALAR ---
TOKEN = "8636080560:AAF_rC_dscmRU0_R9z1XVZpSEgtX-6AOnh8"  # DIQQAT: Tokenni BotFather orqali yangilang!
QUIZ_TIME = 60 

SUBJECTS = {
    "Falsafa": "Falsafa.docx",
    "MT-V-A": "Mtuzilma.docx"
}

# Sessionlar: chat_id -> session_data
active_sessions = {}

# --- ID TEKSHIRISH ---
def load_allowed_ids():
    try:
        with open("users.json", "r") as f:
            data = json.load(f)
            return sorted(data.get("allowed_ids", []))
    except (FileNotFoundError, json.JSONDecodeError):
        return []

ALLOWED_IDS = load_allowed_ids()

def is_allowed(user_id: int):
    # Binary search
    import bisect
    index = bisect.bisect_left(ALLOWED_IDS, user_id)
    return index < len(ALLOWED_IDS) and ALLOWED_IDS[index] == user_id

# --- MOCK PARSER (Sizning parser.py dan keladi) ---
# Agar parser bo'lmasa, xato bermasligi uchun:
def get_quizzes(file_path):
    # Bu yerda haqiqiy parseringiz ishlaydi
    return [
        {"question": f"{file_path} dagi 1-savol?", "options": ["A", "B", "C", "D"], "correct": 0},
        {"question": f"{file_path} dagi 2-savol?", "options": ["X", "Y", "Z", "W"], "correct": 1},
    ]

# --- BOT OBYEKTLARI ---
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- KEYBOARDS ---
def get_main_menu():
    builder = ReplyKeyboardBuilder()
    for sub in SUBJECTS.keys():
        builder.add(types.KeyboardButton(text=f"📚 {sub}"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_count_menu(subject_name, total_count):
    builder = ReplyKeyboardBuilder()
    counts = [10, 20, 30, 50]
    for count in counts:
        if count <= total_count:
            builder.add(types.KeyboardButton(text=f"⚙️ {subject_name}:{count} ta"))
    builder.add(types.KeyboardButton(text=f"🚀 {subject_name}:Barchasi"))
    builder.add(types.KeyboardButton(text="⬅️ Orqaga"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# --- ADMIN TEKSHIRUVI ---
async def is_admin_or_creator(message: types.Message):
    if message.chat.type == "private":
        return True
    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    return member.status in ["administrator", "creator"]

# --- HANDLERS ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if not is_allowed(message.from_user.id):
        return await message.answer(f"🚫 Kirish taqiqlangan! ID: `{message.from_user.id}`", parse_mode="Markdown")

    if message.chat.id in active_sessions:
        return await message.answer("⚠️ Hozirda test davom etmoqda. Tugashini kuting!")

    welcome_text = (
        "👋 **Xush kelibsiz!**\n\n"
        "Guruhda testni faqat ruxsati borlar boshlay oladi.\n"
        "To'xtatish esa faqat **Adminlar** uchun.\n\n"
        "Fanni tanlang:"
    )
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

@dp.message(F.text.startswith("📚 "))
async def choose_count(message: types.Message):
    if not is_allowed(message.from_user.id): return
    if message.chat.id in active_sessions: return

    subject_name = message.text.replace("📚 ", "").strip()
    file_path = SUBJECTS.get(subject_name)
    
    if not file_path: return

    # Parserdan ma'lumot olish
    all_tests = get_quizzes(file_path)
    total_count = len(all_tests)

    await message.answer(
        f"🎯 **{subject_name}** tanlandi.\nBazadagi jami savollar: {total_count} ta.\nNechtasini yechamiz?",
        reply_markup=get_count_menu(subject_name, total_count)
    )

@dp.message(F.text == "⬅️ Orqaga")
async def back_to_main(message: types.Message):
    if message.chat.id in active_sessions: return
    await cmd_start(message)

@dp.message(F.text.startswith("⚙️ ") | F.text.startswith("🚀 "))
async def init_quiz(message: types.Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not is_allowed(user_id): return
    if chat_id in active_sessions:
        return await message.answer("❌ Test allaqachon boshlangan!")

    # Fan va sonni ajratib olish
    try:
        if "🚀" in message.text:
            subject = message.text.split(":")[0].replace("🚀 ", "").strip()
            count = 999 # Hammasi
        else:
            raw = message.text.replace("⚙️ ", "")
            subject, count_raw = raw.split(":")
            count = int(re.search(r'\d+', count_raw).group())

        all_data = get_quizzes(SUBJECTS[subject])
        selected_tests = random.sample(all_data, min(count, len(all_data)))

        # SESSION YARATISH
        active_sessions[chat_id] = {
            "starter_id": user_id,
            "subject": subject,
            "tests": selected_tests,
            "current_index": 0,
            "results": {}, # user_id -> correct_count
            "timer_task": None,
            "current_poll_id": None
        }

        stop_btn = ReplyKeyboardBuilder()
        stop_btn.add(types.KeyboardButton(text="🛑 Testni to'xtatish (Faqat Admin)"))
        
        await message.answer(
            f"🚀 **Test boshlanmoqda!**\nFan: {subject}\nSavollar: {len(selected_tests)} ta\n\n"
            f"Guruhdagilar, tayyor turing!",
            reply_markup=stop_btn.as_markup(resize_keyboard=True),
            parse_mode="Markdown"
        )
        
        await asyncio.sleep(2)
        await send_next_test(chat_id)

    except Exception as e:
        logging.error(f"Init error: {e}")

@dp.message(F.text == "🛑 Testni to'xtatish (Faqat Admin)")
async def stop_quiz(message: types.Message):
    chat_id = message.chat.id
    if chat_id not in active_sessions:
        return await message.answer("Hozirda faol test yo'q.")

    # Faqat admin yoki testni boshlagan odam to'xtata oladi
    if await is_admin_or_creator(message) or message.from_user.id == active_sessions[chat_id]["starter_id"]:
        session = active_sessions[chat_id]
        if session["timer_task"]:
            session["timer_task"].cancel()
        
        del active_sessions[chat_id]
        await message.answer("🛑 Test majburiy to'xtatildi.", reply_markup=get_main_menu())
    else:
        await message.answer("⚠️ Faqat adminlar testni to'xtata oladi!")

async def send_next_test(chat_id):
    session = active_sessions.get(chat_id)
    if not session: return

    idx = session["current_index"]
    tests = session["tests"]

    if idx < len(tests):
        q_data = tests[idx]
        options = list(q_data['options'])
        correct_text = options[q_data['correct']]
        random.shuffle(options)
        new_correct_id = options.index(correct_text)
        
        session["current_correct_id"] = new_correct_id

        poll = await bot.send_poll(
            chat_id=chat_id,
            question=f"Savol {idx+1}/{len(tests)}:\n{q_data['question']}",
            options=options,
            correct_option_id=new_correct_id,
            type='quiz',
            is_anonymous=False, # Kim yechganini bilish uchun
            open_period=QUIZ_TIME
        )
        
        session["current_poll_id"] = poll.poll.id
        session["timer_task"] = asyncio.create_task(wait_for_timeout(chat_id, idx))
    else:
        await show_results(chat_id)

async def wait_for_timeout(chat_id, index):
    await asyncio.sleep(QUIZ_TIME + 2)
    session = active_sessions.get(chat_id)
    if session and session["current_index"] == index:
        session["current_index"] += 1
        await send_next_test(chat_id)

@dp.poll_answer()
async def handle_poll_answer(poll_answer: types.PollAnswer):
    # Har bir javobni hisoblab boramiz
    for chat_id, session in active_sessions.items():
        if session.get("current_poll_id") == poll_answer.poll_id:
            user_id = poll_answer.user.id
            if user_id not in session["results"]:
                session["results"][user_id] = {"name": poll_answer.user.full_name, "score": 0}
            
            if poll_answer.option_ids[0] == session["current_correct_id"]:
                session["results"][user_id]["score"] += 1
            break

async def show_results(chat_id):
    session = active_sessions.get(chat_id)
    if not session: return

    results = session["results"]
    subject = session["subject"]
    
    text = f"🏁 **TEST TUGADI!**\nFan: {subject}\n\n**Natijalar:**\n"
    
    if not results:
        text += "Hech kim qatnashmadi. 🤷‍♂️"
    else:
        # Ballar bo'yicha saralash
        sorted_res = sorted(results.values(), key=lambda x: x["score"], reverse=True)
        for i, res in enumerate(sorted_res[:10], 1): # Top 10 talik
            text += f"{i}. {res['name']} — {res['score']} ta ✅\n"

    await bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=get_main_menu())
    del active_sessions[chat_id]

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
