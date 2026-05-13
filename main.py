import asyncio
import random
import json
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from parser import get_quizzes

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)

# --- SOZLAMALAR ---
TOKEN = "8636080560:AAF_rC_dscmRU0_R9z1XVZpSEgtX-6AOnh8"
QUIZ_TIME = 60 

SUBJECTS = {
    "Falsafa": "Falsafa.docx",
    "MT-V-A": "Mtuzilma.docx"
}

user_sessions = {}

# --- ID TEKSHIRISH (Binar qidiruv) ---
def load_allowed_ids():
    try:
        with open("users.json", "r") as f:
            data = json.load(f)
            return sorted(data.get("allowed_ids", []))
    except (FileNotFoundError, json.JSONDecodeError):
        return []

ALLOWED_IDS = load_allowed_ids()

def is_allowed(user_id: int):
    low, high = 0, len(ALLOWED_IDS) - 1
    while low <= high:
        mid = (low + high) // 2
        if ALLOWED_IDS[mid] == user_id: return True
        elif ALLOWED_IDS[mid] < user_id: low = mid + 1
        else: high = mid - 1
    return False

# --- BOT OBYEKTLARI ---
bot = Bot(token=TOKEN)
dp = Dispatcher()

def get_main_menu():
    builder = ReplyKeyboardBuilder()
    for sub in SUBJECTS.keys():
        builder.add(types.KeyboardButton(text=f"📚 {sub}"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# --- YANGI: Session uchun unique key yaratish ---
def get_session_key(user_id: int, chat_id: int) -> str:
    """
    Shaxsiy chat va guruh uchun alohida session yaratish
    """
    return f"{user_id}_{chat_id}"

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if not is_allowed(message.from_user.id):
        return await message.answer(
            f"🚫 Kirish taqiqlangan! ID: `{message.from_user.id}`", 
            parse_mode="Markdown"
        )

    # Guruh va shaxsiy chat uchun alohida javob
    if message.chat.type in ["group", "supergroup"]:
        # Guruhda
        await message.answer(
            "👋 **Salom!**\n\nBu guruhda testlarni boshlashingiz mumkin! 🔥\nFanni tanlang:",
            parse_mode="Markdown"
        )
    else:
        # Shaxsiy chatda
        await message.answer(
            "👋 **Salom, Bilimdon!**\n\nKreativ test platformasiga xush kelibsiz! 🔥\nFanni tanlang:",
            reply_markup=get_main_menu(),
            parse_mode="Markdown"
        )

@dp.message(F.text.startswith("📚 "))
async def choose_count(message: types.Message):
    if not is_allowed(message.from_user.id): return
    
    subject_name = message.text.replace("📚 ", "").strip()
    file_path = SUBJECTS.get(subject_name)
    
    if not file_path: 
        await message.answer("❌ Fan topilmadi!")
        return

    all_tests = get_quizzes(file_path)
    total_count = len(all_tests)

    if total_count == 0:
        await message.answer("❌ Bu fanda testlar topilmadi!")
        return

    builder = ReplyKeyboardBuilder()
    counts = [25, 30, 35, 40, 45, 50]
    for count in counts:
        if count <= total_count:
            builder.add(types.KeyboardButton(text=f"⚙️ {subject_name}:{count} ta savol"))
    
    builder.add(types.KeyboardButton(text=f"🚀 {subject_name} - Barchasini yechish ({total_count} ta)"))
    builder.add(types.KeyboardButton(text="⬅️ Orqaga"))
    
    builder.adjust(3, 1)
    
    # Shaxsiy chatda keyboard, guruhda yo'q
    if message.chat.type in ["group", "supergroup"]:
        await message.answer(
            f"🎯 **{subject_name}** fani tanlandi!\nBazadagi jami savollar: **{total_count}** ta.\n\nNechtasini yechishni xohlaysiz? 🧠",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            f"🎯 **{subject_name}** fani tanlandi!\nBazadagi jami savollar: **{total_count}** ta.\n\nNechtasini yechishni xohlaysiz? 🧠",
            reply_markup=builder.as_markup(resize_keyboard=True),
            parse_mode="Markdown"
        )

@dp.message(F.text == "⬅️ Orqaga")
async def back_to_main(message: types.Message):
    await cmd_start(message)

@dp.message(F.text.startswith("⚙️ ") | F.text.startswith("🚀 "))
async def init_quiz(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    if not is_allowed(user_id): return

    try:
        # Miqdorni va fanni aniqlash
        if "🚀 " in message.text:
            import re
            parts = message.text.replace("🚀 ", "").split(" - ")
            subject = parts[0].strip()
            count_match = re.search(r'\((\d+)', message.text)
            count = int(count_match.group(1)) if count_match else 50
        else:
            raw_text = message.text.replace("⚙️ ", "")
            parts = raw_text.split(":")
            subject = parts[0].strip()
            count = int(parts[1].split()[0])
        
        if subject not in SUBJECTS:
            await message.answer(f"❌ '{subject}' fani topilmadi!")
            return
        
        all_data = get_quizzes(SUBJECTS[subject])
        
        if not all_data: 
            return await message.answer(f"❌ '{subject}' fanida testlar topilmadi.")

        selected_tests = random.sample(all_data, min(count, len(all_data)))

        # MUHIM: Session key da chat_id ham bo'lishi kerak
        session_key = get_session_key(user_id, chat_id)
        
        user_sessions[session_key] = {
            "user_id": user_id,
            "chat_id": chat_id,  # Chat ID ni saqlash
            "subject": subject,
            "tests": selected_tests,
            "current_index": 0,
            "correct_answers": 0,
            "timer_task": None
        }

        # Shaxsiy chatda keyboard, guruhda yo'q
        if message.chat.type in ["group", "supergroup"]:
            await message.answer(
                f"⚡ **Tayyorgarlik ko'ring!**\n\nFan: *{subject}*\nSavollar: *{len(selected_tests)}* ta\n\nOmad yor bo'lsin! 🎊",
                parse_mode="Markdown"
            )
        else:
            stop_builder = ReplyKeyboardBuilder()
            stop_builder.add(types.KeyboardButton(text="🛑 Testni to'xtatish"))
            
            await message.answer(
                f"⚡ **Tayyorgarlik ko'ring!**\n\nFan: *{subject}*\nSavollar: *{len(selected_tests)}* ta\n\nOmad yor bo'lsin! 🎊",
                reply_markup=stop_builder.as_markup(resize_keyboard=True),
                parse_mode="Markdown"
            )
        
        await asyncio.sleep(1.5)
        await send_next_test(session_key)

    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await message.answer(f"⚠️ Xatolik: {e}")

@dp.message(F.text == "🛑 Testni to'xtatish")
async def stop_quiz(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    session_key = get_session_key(user_id, chat_id)
    
    if session_key in user_sessions:
        if user_sessions[session_key]["timer_task"]:
            user_sessions[session_key]["timer_task"].cancel()
        del user_sessions[session_key]
    
    await message.answer("🏠 Bosh menyuga qaytildi.", reply_markup=get_main_menu())

async def send_next_test(session_key):
    session = user_sessions.get(session_key)
    if not session: return

    chat_id = session["chat_id"]  # To'g'ri chat_id ni olish
    idx = session["current_index"]
    tests = session["tests"]

    if idx < len(tests):
        q_data = tests[idx]
        
        # Javoblarni randomizatsiya qilish
        options = list(q_data['options'])
        correct_text = options[q_data['correct']]
        random.shuffle(options)
        new_correct_id = options.index(correct_text)
        
        session["current_correct_id"] = new_correct_id

        question_number = f"❓ Savol {idx+1}/{len(tests)}"
        question_text = q_data['question']
        
        if len(question_text) > 200:
            await bot.send_message(
                chat_id=chat_id,
                text=f"{question_number}\n\n{question_text}",
                parse_mode="Markdown"
            )
            poll_question = f"Savol {idx+1}/{len(tests)}"
        else:
            poll_question = f"{question_number}\n\n{question_text}"
        
        # Poll yuborish - to'g'ri chat_id ga
        await bot.send_poll(
            chat_id=chat_id,
            question=poll_question,
            options=options,
            correct_option_id=new_correct_id,
            type='quiz',
            is_anonymous=False,
            open_period=QUIZ_TIME
        )
        
        session["timer_task"] = asyncio.create_task(
            wait_for_timeout(session_key, idx)
        )
    else:
        await show_results(session_key)

async def wait_for_timeout(session_key, index):
    await asyncio.sleep(QUIZ_TIME + 1)
    session = user_sessions.get(session_key)
    if session and session["current_index"] == index:
        session["current_index"] += 1
        await bot.send_message(session["chat_id"], "⌛ **Vaqt tugadi!**", parse_mode="Markdown")
        await send_next_test(session_key)

@dp.poll_answer()
async def handle_poll_answer(poll_answer: types.PollAnswer):
    user_id = poll_answer.user.id
    
    # Barcha sessionlarni tekshirish (guruh va shaxsiy chatlar)
    session_key = None
    for key in user_sessions.keys():
        if user_sessions[key]["user_id"] == user_id:
            session_key = key
            break
    
    if not session_key:
        return
    
    session = user_sessions[session_key]

    if session["timer_task"]:
        session["timer_task"].cancel()

    if poll_answer.option_ids[0] == session.get("current_correct_id"):
        session["correct_answers"] += 1
    
    session["current_index"] += 1
    await asyncio.sleep(0.5)
    await send_next_test(session_key)

async def show_results(session_key):
    session = user_sessions.get(session_key)
    if not session:
        return
        
    chat_id = session["chat_id"]
    correct = session["correct_answers"]
    total = len(session["tests"])
    
    score = (correct / total) * 40
    
    if score >= 36:
        res_msg = "Siz mutlaq g'olibsiz! 🏆"
        gift = "🔥🔥🔥 BAYRAM SHUKUHI! 🔥🔥🔥"
    elif score >= 25:
        res_msg = "Yaxshi natija! ⚡"
        gift = "👏 Barakalla!"
    else:
        res_msg = "Yana harakat qiling! 📖"
        gift = "💪 Bo'sh kelmang!"

    result_text = (
        f"🏁 **TEST TUGADI!**\n\n"
        f"✅ To'g'ri: `{correct}`\n"
        f"❌ Xato: `{total - correct}`\n"
        f"⚖️ Ball: `{score:.1f} / 40`\n\n"
        f"{res_msg}\n{gift}"
    )

    # Shaxsiy chatda keyboard, guruhda yo'q
    if chat_id == session["user_id"]:  # Shaxsiy chat
        await bot.send_message(
            chat_id, 
            result_text, 
            parse_mode="Markdown", 
            reply_markup=get_main_menu()
        )
    else:  # Guruh
        await bot.send_message(
            chat_id, 
            result_text, 
            parse_mode="Markdown"
        )
    
    if session_key in user_sessions: 
        del user_sessions[session_key]

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
