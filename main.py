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
TOKEN = "8636080560:AAF_rC_dscmRU0_R9z1XVZpSEgtX-6AOnh8" # O'zingizning API tokengizni qo'ying
QUIZ_TIME = 50

SUBJECTS = {
    "Falsafa": "Falsafa.docx",
    "MT-V-A": "Mtuzilma.docx"
}

# Parser funksiyasini yuklash
try:
    from parser import get_quizzes
except ImportError:
    def get_quizzes(path):
        # Test uchun namuna ma'lumot (agar fayl topilmasa)
        return [{"question": "Namuna savol " * 40, "options": ["A", "B", "C", "D"], "correct": 0}]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

FIREWORK_EFFECT = "5046509860389126442"
SUCCESS_MESSAGES = ["🎉 TO‘G‘RI JAVOB!", "✨ SUPER!", "🏆 AJOYIB!", "🔥 ZO‘R ISH!"]

# =========================================================
# UTILS & SESSION MANAGEMENT
# =========================================================
user_sessions = {}

def load_allowed_ids():
    try:
        with open("users.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return sorted(data.get("allowed_ids", []))
    except (FileNotFoundError, json.JSONDecodeError):
        return []

ALLOWED_IDS = load_allowed_ids()

def is_allowed(user_id: int):
    if not ALLOWED_IDS: return True  # Agar ro'yxat bo'sh bo'lsa hamma kirsin
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
# HANDLERS
# =========================================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if not is_allowed(message.from_user.id):
        return await message.answer("🚫 Kechirasiz, sizga botdan foydalanishga ruxsat berilmagan.")
    
    await message.answer(
        "🎓 <b>PROFESSIONAL TEST BOT</b>\n\nBilimingizni sinash uchun quyidagi fanlardan birini tanlang:",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )

@dp.message(F.text.startswith("📚 "))
async def choose_count(message: types.Message):
    if not is_allowed(message.from_user.id): return
    
    subject_name = message.text.replace("📚 ", "").strip()
    file_path = SUBJECTS.get(subject_name)

    if not file_path:
        return await message.answer("❌ Xatolik: Fan ma'lumotnomasi topilmadi.")

    try:
        all_tests = get_quizzes(file_path)
        if not all_tests:
            return await message.answer("⚠️ Ushbu fan bo'yicha savollar hali yuklanmagan.")

        total_count = len(all_tests)
        builder = ReplyKeyboardBuilder()
        for count in [25, 30, 50, 100]:
            if count <= total_count:
                builder.add(types.KeyboardButton(text=f"⚙️ {subject_name}:{count}"))

        builder.add(types.KeyboardButton(text=f"🚀 {subject_name} - Barchasi ({total_count})"))
        builder.add(types.KeyboardButton(text="⬅️ Orqaga"))
        builder.adjust(2)

        await message.answer(
            f"🎯 <b>Fan:</b> {subject_name}\n📊 <b>Jami savollar:</b> {total_count} ta\n\nNechta test yechishni xohlaysiz?",
            reply_markup=builder.as_markup(resize_keyboard=True),
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Error in choose_count: {e}")
        await message.answer("❌ Ma'lumotlarni o'qishda xatolik yuz berdi.")

@dp.message(F.text == "⬅️ Orqaga")
async def back_to_home(message: types.Message):
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
            f"🚀 <b>TEST BOSHLANDI!</b>\n\n📚 <b>Fan:</b> {subject}\n🔢 <b>Savollar:</b> {len(selected)} ta\n\n<i>Omad tilaymiz!</i>",
            reply_markup=stop_btn.as_markup(resize_keyboard=True),
            parse_mode="HTML"
        )
        
        await asyncio.sleep(1)
        await send_next_test(user_id)

    except Exception as e:
        logging.error(f"Quiz Init Error: {e}")
        await message.answer("❌ Testni boshlashda xatolik yuz berdi. Iltimos qaytadan urinib ko'ring.")

@dp.message(F.text == "🛑 Testni to'xtatish")
async def stop_quiz(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
        await message.answer("🛑 Test to‘xtatildi. Bosh menyuga qaytdingiz.", reply_markup=get_main_menu())
    else:
        await message.answer("❓ Hozirda faol test yo'q.", reply_markup=get_main_menu())

# =========================================================
# CORE LOGIC: SEND NEXT TEST
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

    question_text = q['question'].strip()
    
    try:
        # AGAR SAVOL 300 BELGIDAN OSHSA
        if len(question_text) > 300:
            # 1. Savolni matn ko'rinishida yuboramiz
            await bot.send_message(
                user_id, 
                f"<b>Savol {idx + 1}/{total}</b>\n\n{question_text}", 
                parse_mode="HTML"
            )
            # 2. Pollni faqat javob variantlari bilan yuboramiz
            poll_question = f"Savol {idx + 1}/{total} javobini belgilang:"
        else:
            poll_question = f"({idx + 1}/{total}) {question_text}"

        poll = await bot.send_poll(
            chat_id=user_id,
            question=poll_question,
            options=options,
            correct_option_id=correct_id,
            type="quiz",
            is_anonymous=False,
            open_period=QUIZ_TIME
        )
        session["current_poll_id"] = poll.poll.id

    except TelegramBadRequest as e:
        logging.error(f"Telegram API Error: {e}")
        await bot.send_message(user_id, "⚠️ Bu savolni yuborishda texnik xatolik (masalan, variantlar juda uzun) yuz berdi. Keyingisiga o'tamiz.")
        session["current_index"] += 1
        await send_next_test(user_id)

@dp.poll_answer()
async def handle_poll_answer(poll_answer: types.PollAnswer):
    user_id = poll_answer.user.id
    session = user_sessions.get(user_id)

    if not session or poll_answer.poll_id != session["current_poll_id"]:
        return

    selected = poll_answer.option_ids[0]
    
    if selected == session["current_correct_id"]:
        session["correct_answers"] += 1
        try:
            await bot.send_message(
                user_id, 
                random.choice(SUCCESS_MESSAGES),
                message_effect_id=FIREWORK_EFFECT
            )
        except: pass # Effekt xatolik bersa e'tiborsiz qoldiramiz
    else:
        await bot.send_message(user_id, "❌ Noto‘g‘ri javob!")

    session["current_index"] += 1
    await asyncio.sleep(1.2)
    await send_next_test(user_id)

async def show_results(user_id):
    session = user_sessions.get(user_id)
    if not session: return

    correct = session["correct_answers"]
    total = len(session["tests"])
    score = (correct / total) * 40

    result_text = (
        f"🏁 <b>TEST YAKUNLANDI</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📚 Fan: {session['subject']}\n"
        f"✅ To‘g‘ri javob: {correct}\n"
        f"❌ Noto‘g‘ri javob: {total - correct}\n"
        f"📊 Foiz: {(correct/total)*100:.1f}%\n"
        f"🏆 <b>Umumiy ball: {score:.1f}/40</b>\n"
        f"━━━━━━━━━━━━━━━"
    )

    await bot.send_message(
        user_id,
        result_text,
        parse_mode="HTML",
        message_effect_id=FIREWORK_EFFECT if score > 20 else None,
        reply_markup=get_main_menu()
    )
    
    if user_id in user_sessions:
        del user_sessions[user_id]

# =========================================================
# RUNNER
# =========================================================
async def main():
    try:
        print("--- Bot ishga tushdi ---")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")
