import asyncio
import random
import json
import logging
import re

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

# =========================================================
# CONFIG & SETTINGS
# =========================================================
TOKEN = "8810890132:AAEDf47oemfd-ascu4R8b4tOPFUBlewg9bY" 
QUIZ_TIME = 50
ADMIN_PASSWORD = "^02-25-Kin" # Admin tasdiqlash uchun promokod

SUBJECTS = {
    "Falsafa": "Falsafa.docx",
    "MT-V-A": "Mtuzilma.docx",
    "Dasturlash": "Dasturlash.docx",
    "Dinshunoslik": "Dinshunoslik.docx" # Yangi fan qo'shildi
}

# Parser funksiyalarini yuklash
try:
    from parser import get_quizzes, get_quizzes_programming, get_quizzes_dinshunoslik
except ImportError:
    def get_quizzes(p): return []
    def get_quizzes_programming(p): return []
    def get_quizzes_dinshunoslik(p): return []

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

FIREWORK_EFFECT = "5046509860389126442"
SUCCESS_MESSAGES = ["🎉 TO‘G‘RI JAVOB!", "✨ SUPER!", "🏆 AJOYIB!", "🔥 ZO‘R ISH!"]

# =========================================================
# UTILS & SESSION MANAGEMENT
# =========================================================
user_sessions = {}
temp_allowed_users = set() # /admin orqali ruxsat olganlar

def load_allowed_ids():
    try:
        with open("users.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return sorted([int(i) for i in data.get("allowed_ids", [])])
    except: return []

ALLOWED_IDS = load_allowed_ids()

def is_allowed(user_id: int):
    if user_id in temp_allowed_users: return True
    if not ALLOWED_IDS: return False  
    
    low, high = 0, len(ALLOWED_IDS) - 1
    while low <= high:
        mid = (low + high) // 2
        if ALLOWED_IDS[mid] == user_id: return True
        elif ALLOWED_IDS[mid] < user_id: low = mid + 1
        else: high = mid - 1
    return False

def format_quiz_text(text):
    """ Dasturlash kodlarini aniqlash va <code> formatiga o'tkazish """
    code_indicators = [';', '{', '}', 'print(', 'cout', 'int ', 'public ', 'void ', 'def ', 'class ']
    if any(ind in text for ind in code_indicators):
        return f"<code>{text}</code>"
    return text

# =========================================================
# KEYBOARDS
# =========================================================
def get_main_menu():
    builder = ReplyKeyboardBuilder()
    for subject in SUBJECTS.keys():
        builder.add(types.KeyboardButton(text=f"📚 {subject}"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# =========================================================
# BOT INITIALIZATION
# =========================================================
bot = Bot(token=TOKEN)
dp = Dispatcher()

# =========================================================
# ADMIN & AUTH HANDLERS
# =========================================================
@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    await message.answer("🔑 <b>Admin tasdiqlash.</b>\nIltimos, maxfiy kodni yuboring:", parse_mode="HTML")

@dp.message(F.text == ADMIN_PASSWORD)
async def process_admin_code(message: types.Message):
    temp_allowed_users.add(message.from_user.id)
    await message.answer("✅ <b>Ruxsat berildi!</b>\nEndi testlardan foydalanishingiz mumkin.", 
                         reply_markup=get_main_menu(), parse_mode="HTML")

# =========================================================
# MAIN HANDLERS
# =========================================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if not is_allowed(user_id):
        return await message.answer(
            f"🚫 <b>Ruxsat berilmagan!</b>\nID: <code>{user_id}</code>\n\nAdmin bo'lsangiz /admin buyrug'ini yozing.",
            parse_mode="HTML"
        )
    
    await message.answer(
        f"🎓 <b>PROFESSIONAL TEST BOT</b>\n\nAssalomu alaykum, {message.from_user.first_name}!\nFan tanlang:",
        reply_markup=get_main_menu(), parse_mode="HTML"
    )

@dp.message(F.text.startswith("📚 "))
async def choose_count(message: types.Message):
    if not is_allowed(message.from_user.id): return
    
    subject_name = message.text.replace("📚 ", "").strip()
    file_path = SUBJECTS.get(subject_name)

    try:
        if subject_name == "Dasturlash": all_tests = get_quizzes_programming(file_path)
        elif subject_name == "Dinshunoslik": all_tests = get_quizzes_dinshunoslik(file_path)
        else: all_tests = get_quizzes(file_path)
            
        if not all_tests: return await message.answer("⚠️ Savollar topilmadi.")

        total_count = len(all_tests)
        builder = ReplyKeyboardBuilder()
        for count in [20, 25, 30, 50, 100]:
            if count <= total_count: builder.add(types.KeyboardButton(text=f"⚙️ {subject_name}:{count}"))

        builder.add(types.KeyboardButton(text=f"🚀 {subject_name} - Barchasi ({total_count})"))
        builder.add(types.KeyboardButton(text="⬅️ Orqaga"))
        builder.adjust(2)

        await message.answer(f"🎯 <b>Fan:</b> {subject_name}\n📊 <b>Jami:</b> {total_count} ta", 
                             reply_markup=builder.as_markup(resize_keyboard=True), parse_mode="HTML")
    except Exception as e:
        await message.answer("❌ Ma'lumotlarni o'qishda xatolik.")

@dp.message(F.text == "⬅️ Orqaga")
async def back_to_home(message: types.Message): await cmd_start(message)

@dp.message(F.text.startswith("⚙️ ") | F.text.startswith("🚀 "))
async def init_quiz(message: types.Message):
    if not is_allowed(message.from_user.id): return

    try:
        if message.text.startswith("🚀 "):
            subject = message.text.split("🚀 ")[1].split(" - ")[0].strip()
            count = int(re.search(r"\((\d+)\)", message.text).group(1))
        else:
            raw = message.text.replace("⚙️ ", "")
            subject, c = raw.split(":")
            count = int(c)

        file_path = SUBJECTS[subject]
        if subject == "Dasturlash": all_tests = get_quizzes_programming(file_path)
        elif subject == "Dinshunoslik": all_tests = get_quizzes_dinshunoslik(file_path)
        else: all_tests = get_quizzes(file_path)
            
        selected = random.sample(all_tests, min(count, len(all_tests)))
        user_sessions[message.from_user.id] = {
            "subject": subject, "tests": selected, "current_index": 0,
            "correct_answers": 0, "current_poll_id": None
        }

        await message.answer(f"🚀 <b>{subject}</b> boshlandi!", 
                             reply_markup=ReplyKeyboardBuilder().add(types.KeyboardButton(text="🛑 Testni to'xtatish")).as_markup(resize_keyboard=True), 
                             parse_mode="HTML")
        await send_next_test(message.from_user.id)
    except: await message.answer("❌ Xatolik.")

# =========================================================
# CORE LOGIC: SEND NEXT TEST
# =========================================================
async def send_next_test(user_id):
    session = user_sessions.get(user_id)
    if not session: return

    idx, tests = session["current_index"], session["tests"]
    if idx >= len(tests): return await show_results(user_id)

    q = tests[idx]
    options = [str(opt)[:100] for opt in q["options"]]
    correct_text = options[q["correct"]]
    random.shuffle(options)
    correct_id = options.index(correct_text)
    session["current_correct_id"] = correct_id

    # Savolni formatlash (Kod bo'lsa <code> ichida chiqadi)
    q_text = format_quiz_text(q['question'].strip())
    
    try:
        if len(q_text) > 250:
            await bot.send_message(user_id, f"<b>Savol {idx + 1}/{len(tests)}:</b>\n\n{q_text}", parse_mode="HTML")
            poll_q = "To'g'ri javobni tanlang:"
        else:
            poll_q = f"({idx + 1}/{len(tests)}) {q['question']}"

        poll = await bot.send_poll(
            chat_id=user_id, question=poll_q[:300], options=options,
            correct_option_id=correct_id, type="quiz", is_anonymous=False, open_period=QUIZ_TIME
        )
        session["current_poll_id"] = poll.poll.id
    except:
        session["current_index"] += 1
        await send_next_test(user_id)

@dp.poll_answer()
async def handle_poll_answer(poll_answer: types.PollAnswer):
    user_id = poll_answer.user.id
    session = user_sessions.get(user_id)
    if not session or poll_answer.poll_id != session["current_poll_id"]: return

    if poll_answer.option_ids[0] == session["current_correct_id"]:
        session["correct_answers"] += 1
        try: await bot.send_message(user_id, random.choice(SUCCESS_MESSAGES), message_effect_id=FIREWORK_EFFECT)
        except: pass
    else:
        await bot.send_message(user_id, "❌ Noto‘g‘ri javob!")

    session["current_index"] += 1
    await asyncio.sleep(1.2)
    await send_next_test(user_id)

async def show_results(user_id):
    session = user_sessions.get(user_id)
    if not session: return
    correct, total = session["correct_answers"], len(session["tests"])
    score = (correct / total) * 40

    await bot.send_message(
        user_id, f"🏁 <b>YAKUNLANDI</b>\n✅ To'g'ri: {correct}\n🏆 Ball: {score:.1f}/40",
        parse_mode="HTML", reply_markup=get_main_menu()
    )
    user_sessions.pop(user_id, None)

@dp.message(F.text == "🛑 Testni to'xtatish")
async def stop_quiz(message: types.Message):
    user_sessions.pop(message.from_user.id, None)
    await message.answer("🛑 Test to‘xtatildi.", reply_markup=get_main_menu())

async def main():
    print("--- Bot ishga tushdi ---")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
