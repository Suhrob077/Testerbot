import asyncio
import random
import json
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from parser import get_quizzes

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)

# --- SOZLAMALAR ---
TOKEN = "8636080560:AAF_rC_dscmRU0_R9z1XVZpSEgtX-6AOnh8"
QUIZ_TIME = 60  # soniya

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

def binary_search_id(arr, target_id):
    low, high = 0, len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target_id: return True
        elif arr[mid] < target_id: low = mid + 1
        else: high = mid - 1
    return False

ALLOWED_IDS = load_allowed_ids()

def is_allowed(user_id: int):
    return binary_search_id(ALLOWED_IDS, user_id)

# --- ASOSIY LOGIKA ---
bot = Bot(token=TOKEN)
dp = Dispatcher()

def get_main_menu():
    builder = ReplyKeyboardBuilder()
    for sub in SUBJECTS.keys():
        builder.add(types.KeyboardButton(text=f"📚 {sub}"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if not is_allowed(message.from_user.id):
        return await message.answer(
            f"🚫 **Kirish taqiqlangan!**\n\nSizning ID: `{message.from_user.id}`\nAdmin bilan bog'laning. 🔐", 
            parse_mode="Markdown"
        )

    await message.answer(
        "👋 **Salom, Bilimdon!**\n\nBugun o'z mahoratingizni sinab ko'rishga tayyormisiz? 🔥\n"
        "Quyidagi fanlardan birini tanlang va sarguzashtni boshlang! 👇",
        reply_markup=get_main_menu()
    )

@dp.message(F.text.startswith("📚 "))
async def choose_count(message: types.Message):
    if not is_allowed(message.from_user.id): return
    
    subject = message.text.replace("📚 ", "")
    builder = ReplyKeyboardBuilder()
    counts = [25, 30, 35, 40, 45, 50]
    for count in counts:
        builder.add(types.KeyboardButton(text=f"⚙️ {subject}:{count} ta savol"))
    
    builder.add(types.KeyboardButton(text="⬅️ Orqaga"))
    builder.adjust(3, 1)
    
    await message.answer(
        f"🎯 **{subject}** fani tanlandi!\n\nQancha savol bilan o'zingizni qiynamoqchisiz? 😅🧠",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

@dp.message(F.text == "⬅️ Orqaga")
async def back_to_main(message: types.Message):
    await cmd_start(message)

@dp.message(F.text.startswith("⚙️ "))
async def init_quiz(message: types.Message):
    user_id = message.from_user.id
    if not is_allowed(user_id): return

    try:
        raw_text = message.text.replace("⚙️ ", "")
        parts = raw_text.split(":")
        subject = parts[0]
        count = int(parts[1].split()[0])
        
        all_data = get_quizzes(SUBJECTS[subject])
        if not all_data: 
            return await message.answer("❌ Afsuski, bazada testlar topilmadi.")

        random.shuffle(all_data)
        selected_tests = all_data[:count]

        user_sessions[user_id] = {
            "subject": subject,
            "tests": selected_tests,
            "current_index": 0,
            "correct_answers": 0,
            "timer_task": None
        }

        # Test to'xtatish tugmasi
        stop_builder = ReplyKeyboardBuilder()
        stop_builder.add(types.KeyboardButton(text="🛑 Testni to'xtatish"))
        
        await message.answer(
            f"🚀 **Tayyorlaning!**\n\nFan: *{subject}*\nSavollar soni: *{count}* ta\nVaqt: Har bir savolga *{QUIZ_TIME}* soniya!\n\nOmad yor bo'lsin! ✨",
            reply_markup=stop_builder.as_markup(resize_keyboard=True),
            parse_mode="Markdown"
        )
        
        await asyncio.sleep(2)
        await send_next_test(user_id, message.chat.id)

    except Exception as e:
        await message.answer(f"⚠️ Xatolik yuz berdi: {e}")

@dp.message(F.text == "🛑 Testni to'xtatish")
async def stop_quiz(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_sessions:
        if user_sessions[user_id]["timer_task"]:
            user_sessions[user_id]["timer_task"].cancel()
        del user_sessions[user_id]
    
    await message.answer("📥 Test to'xtatildi. Bosh menyuga qaytamiz.", reply_markup=get_main_menu())

async def send_next_test(user_id, chat_id):
    session = user_sessions.get(user_id)
    if not session: return

    idx = session["current_index"]
    tests = session["tests"]

    if idx < len(tests):
        q = tests[idx]
        progress_bar = "🔵" * (idx + 1) + "⚪" * (len(tests) - idx - 1)
        
        await bot.send_poll(
            chat_id=chat_id,
            question=f"❓ Savol {idx+1}/{len(tests)}\n\n{q['question']}\n\n{progress_bar}",
            options=q['options'],
            correct_option_id=q['correct'],
            type='quiz',
            is_anonymous=False,
            open_period=QUIZ_TIME
        )
        
        session["timer_task"] = asyncio.create_task(wait_for_timeout(user_id, chat_id, idx))
    else:
        await show_results(user_id, chat_id)

async def wait_for_timeout(user_id, chat_id, index):
    await asyncio.sleep(QUIZ_TIME + 1)
    session = user_sessions.get(user_id)
    
    if session and session["current_index"] == index:
        session["current_index"] += 1
        await bot.send_message(chat_id, "⏰ **Vaqt tugadi!** Keyingi savolga o'tamiz...⏭")
        await send_next_test(user_id, chat_id)

@dp.poll_answer()
async def handle_poll_answer(poll_answer: types.PollAnswer):
    user_id = poll_answer.user.id
    session = user_sessions.get(user_id)

    if session:
        if session["timer_task"]:
            session["timer_task"].cancel()

        current_test = session["tests"][session["current_index"]]
        
        # To'g'ri javob bersa bayramona effekt
        if poll_answer.option_ids[0] == current_test["correct"]:
            session["correct_answers"] += 1
            # Kichik xabar o'rniga faqat pauza yoki stiker yuborsa ham bo'ladi
        
        session["current_index"] += 1
        await asyncio.sleep(0.8) # Foydalanuvchi natijasini ko'rishi uchun qisqa pauza
        await send_next_test(user_id, user_id)

async def show_results(user_id, chat_id):
    session = user_sessions.get(user_id)
    correct = session["correct_answers"]
    total = len(tests := session["tests"])
    
    # 40 ballik tizimga o'tkazish
    score = (correct / total) * 40
    
    # Kreativ natija ssenariysi
    if score >= 36:
        status = "Dahosiz! 🔥 Sizni to'xtatib bo'lmaydi! 🏆"
        emoji = "🎊👑🤴"
    elif score >= 30:
        status = "Ajoyib natija! Juda aqllisiz! ⭐"
        emoji = "😎👏📈"
    elif score >= 20:
        status = "Yaxshi, lekin yana ozgina harakat kerak! 📚"
        emoji = "👨‍💻📖👍"
    else:
        status = "Xafa bo'lmang, bilim olishdan to'xtamang! 💪"
        emoji = "⚓💡🔄"

    result_text = (
        f"🏁 **TEST YAKUNLANDI!** 🏁\n\n"
        f"📊 **Natijangiz:**\n"
        f"✅ To'g'ri javoblar: `{correct}` ta\n"
        f"❌ Xato javoblar: `{total - correct}` ta\n"
        f"💯 Umumiy ball: `{score:.1f} / 40` ball\n\n"
        f"🎭 **Xulosa:** {status} {emoji}\n\n"
        f"Yana urinib ko'rasizmi?"
    )

    await bot.send_message(chat_id, result_text, parse_mode="Markdown", reply_markup=get_main_menu())
    if user_id in user_sessions:
        del user_sessions[user_id]

async def main():
    print("Bot ishga tushdi... 🚀")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())