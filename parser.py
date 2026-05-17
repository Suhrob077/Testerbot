import pdfplumber
from docx import Document
import re

def get_quizzes_programming(file_path):
    """
    Dasturlash fani uchun maxsus parser.
    To'g'ri javob har doim BIRINCHI variant (— bilan boshlanadi).
    """
    try:
        doc = Document(file_path)
        quiz_data = []
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        
        i = 0
        while i < len(paragraphs):
            if "Savol" in paragraphs[i] or "савол" in paragraphs[i].lower():
                question_parts = []
                i += 1
                while i < len(paragraphs) and not paragraphs[i].startswith("—"):
                    question_parts.append(paragraphs[i])
                    i += 1
                
                question_text = " ".join(question_parts).strip()
                options = []
                while i < len(paragraphs) and paragraphs[i].startswith("—"):
                    option_text = paragraphs[i].replace("—", "").strip()
                    options.append(option_text[:100])
                    i += 1
                
                if len(options) >= 2 and question_text:
                    quiz_data.append({
                        "question": question_text[:250],
                        "options": options[:10],
                        "correct": 0
                    })
            else:
                i += 1
        return quiz_data
    except Exception as e:
        print(f"Dasturlash parser xatosi: {e}")
        return []

def get_quizzes_dinshunoslik(file_path):
    """
    Dinshunoslik uchun universal parser.
    Separatorlarni (====, ++++) tozalaydi va # belgisini taniydi.
    """
    try:
        doc = Document(file_path)
        quiz_data = []
        raw_lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        clean_lines = []
        for line in raw_lines:
            if set(line).issubset({'=', '+', '-', '*', ' '}) and len(line) > 1:
                continue
            clean_lines.append(line)

        i = 0
        while i < len(clean_lines):
            line = clean_lines[i]
            if line.endswith('?') or (i + 1 < len(clean_lines) and clean_lines[i+1].startswith('#')):
                question_text = line
                options = []
                correct_idx = 0
                i += 1
                
                temp_idx = 0
                while i < len(clean_lines) and not clean_lines[i].endswith('?'):
                    if i + 1 < len(clean_lines) and not clean_lines[i].startswith('#') and \
                       not clean_lines[i+1].startswith('#') and len(options) >= 2:
                        break
                    
                    opt_text = clean_lines[i]
                    if opt_text.startswith('#'):
                        correct_idx = temp_idx
                        opt_text = opt_text.replace('#', '').strip()
                    
                    options.append(opt_text[:100])
                    temp_idx += 1
                    i += 1
                
                if len(options) >= 2:
                    quiz_data.append({
                        "question": question_text[:250],
                        "options": options[:10],
                        "correct": correct_idx
                    })
            else:
                i += 1
        return quiz_data
    except Exception as e:
        print(f"Dinshunoslik parser xatosi: {e}")
        return []

def get_quizzes(file_path):
    """
    Falsafa, MT-V-A va Ingliz tili-{Di} fanlari uchun parser.
    Format: ++++ va ==== bilan ajratilgan
    """
    try:
        doc = Document(file_path)
        full_text = "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])
        raw_questions = full_text.split("++++")
        quiz_data = []

        for item in raw_questions:
            item = item.strip()
            if not item: continue
            parts = item.split("====")
            if len(parts) < 2: continue
            
            question_text = parts[0].strip()
            options_raw = [p.strip() for p in parts[1:] if p.strip()]
            
            correct_index = 0
            final_options = []
            for i, opt in enumerate(options_raw):
                clean_opt = opt.replace("#", "").strip()
                if opt.startswith("#"):
                    correct_index = i
                final_options.append(clean_opt[:100])
            
            if len(final_options) >= 2:
                quiz_data.append({
                    "question": question_text[:250],
                    "options": final_options[:10],
                    "correct": correct_index
                })
        return quiz_data
    except Exception as e:
        print(f"Standart parser xatosi: {e}")
        return []

def normalize_text(text):
    """
    Matnni taqqoslash uchun normalizatsiya qiladi:
    - Kichik harfga o'tkazadi
    - Maxsus belgilarni olib tashlaydi
    - Ortiqcha bo'sh joylarni tozalaydi
    """
    if not text:
        return ""
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip().lower()

# Inglizcha savol prefixlarini uzbekchaga tarjima qilish
ENGLISH_QUESTION_TRANSLATIONS = {
    "choose the correct answer": "To'g'ri javobni tanlang",
    "choose the correct word": "To'g'ri so'zni tanlang",
    "choose the word closest in meaning to": "Ma'nosi eng yaqin so'zni tanlang",
    "choose the word closest in meaning": "Ma'nosi eng yaqin so'zni tanlang",
    "complete the sentence": "Gapni to'ldiring",
    "choose the correct alternative to": "To'g'ri muqobilni tanlang",
    "choose the correct translation of the word": "So'zning to'g'ri tarjimasini tanlang",
    "choose the correct preposition": "To'g'ri predlogni tanlang",
    "it is a group of people working together for illegal purposes": "Bu noqonuniy maqsadlarda birga ishlaydigan odamlar guruhi"
}

def translate_english_question(question_text):
    """
    Inglizcha savol matnini tarjima bilan qaytaradi.
    Format: {Tarjima = Inglizcha}
    """
    question_lower = question_text.lower().strip()
    
    for eng_phrase, uz_translation in ENGLISH_QUESTION_TRANSLATIONS.items():
        if eng_phrase in question_lower:
            # Inglizcha qismni topish
            start_idx = question_lower.find(eng_phrase)
            end_idx = start_idx + len(eng_phrase)
            
            # Original registrda inglizcha qismni olish
            original_eng = question_text[start_idx:end_idx]
            
            # Qolgan qismni ham qo'shish (agar bor bo'lsa)
            remaining = question_text[end_idx:].strip()
            
            if remaining:
                return f"{uz_translation} = {original_eng} {remaining}"
            else:
                return f"{uz_translation} = {original_eng}"
    
    # Agar mos kelish topilmasa, asl matnni qaytarish
    return question_text

def get_quizzes_english_pdf_docx(docx_path, pdf_path):
    """
    Ingliz tili-{KIN} uchun PDF+DOCX parser.
    Savollarga uzbekcha tarjima qo'shiladi.
    """
    try:
        print("\n" + "="*60)
        print("🔍 INGLIZ TILI PARSER BOSHLANDI")
        print("="*60)
        
        # PDF dan javoblarni olish
        pdf_answers = []
        pdf_answers_original = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                chars = page.chars
                current_word = []
                
                for char in chars:
                    color = char.get("non_stroking_color") or char.get("stroking_color")
                    is_red = False
                    
                    if color and len(color) == 3:
                        r, g, b = color
                        if (r > 0.6 and g < 0.4 and b < 0.4) or \
                           (isinstance(r, int) and r > 150 and g < 100 and b < 100):
                            is_red = True
                    
                    if is_red:
                        current_word.append(char["text"])
                    else:
                        if current_word:
                            word_str = "".join(current_word).strip()
                            if word_str and not word_str.isdigit() and len(word_str) > 1:
                                pdf_answers_original.append(word_str)
                                normalized = normalize_text(word_str)
                                if normalized:
                                    pdf_answers.append(normalized)
                            current_word = []
                
                if current_word:
                    word_str = "".join(current_word).strip()
                    if word_str and not word_str.isdigit() and len(word_str) > 1:
                        pdf_answers_original.append(word_str)
                        normalized = normalize_text(word_str)
                        if normalized:
                            pdf_answers.append(normalized)
        
        print(f"\n✅ PDF dan topilgan javoblar: {len(pdf_answers)} ta")

        # DOCX dan savollarni olish
        doc = Document(docx_path)
        raw_lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        
        clean_lines = []
        for line in raw_lines:
            if set(line).issubset({'_', '=', '+', '-', '*', ' ', '—'}) and len(line) > 1:
                continue
            clean_lines.append(line)

        i = 0
        docx_quizzes = []
        
        while i < len(clean_lines):
            line = clean_lines[i]
            if "choose the correct" in line.lower() or "choose the word" in line.lower() or \
               "choose the best" in line.lower() or "select the correct" in line.lower() or \
               "complete the sentence" in line.lower() or "it is a group" in line.lower():
                question_text = line
                options = []
                i += 1
                
                while i < len(clean_lines):
                    current_line = clean_lines[i]
                    if "choose the correct" in current_line.lower() or \
                       "choose the word" in current_line.lower() or \
                       "choose the best" in current_line.lower() or \
                       "select the correct" in current_line.lower() or \
                       "complete the sentence" in current_line.lower() or \
                       "it is a group" in current_line.lower():
                        break
                    
                    if current_line and len(current_line) < 200:
                        options.append(current_line)
                    i += 1
                
                if len(options) >= 2:
                    # ✅ Savolni tarjima bilan saqlash
                    translated_question = translate_english_question(question_text)
                    
                    docx_quizzes.append({
                        "question": translated_question,
                        "options": options,
                        "original_question": question_text  # Asl inglizcha savolni ham saqlash
                    })
            else:
                i += 1
        
        print(f"\n✅ DOCX dan topilgan savollar: {len(docx_quizzes)} ta")

        # Javoblarni moslashtirish
        quiz_data = []
        
        for idx, docx_quiz in enumerate(docx_quizzes):
            correct_idx = 0
            
            if idx < len(pdf_answers):
                pdf_answer = pdf_answers[idx]
                pdf_answer_len = len(pdf_answer)
                
                best_match_score = 0
                best_match_idx = 0
                
                for opt_idx, option in enumerate(docx_quiz["options"]):
                    option_normalized = normalize_text(option)
                    option_len = len(option_normalized)
                    
                    if pdf_answer == option_normalized:
                        correct_idx = opt_idx
                        best_match_score = 100
                        break
                    
                    if pdf_answer in option_normalized:
                        score = (pdf_answer_len / option_len) * 100
                        if score > best_match_score:
                            best_match_score = score
                            best_match_idx = opt_idx
                    
                    if option_normalized in pdf_answer:
                        score = (option_len / pdf_answer_len) * 100
                        if score > best_match_score:
                            best_match_score = score
                            best_match_idx = opt_idx
                
                if best_match_score >= 60 and best_match_score < 100:
                    correct_idx = best_match_idx
            
            quiz_data.append({
                "question": docx_quiz["question"][:300],  # Tarjima bilan birga
                "options": [opt[:100] for opt in docx_quiz["options"]][:10],
                "correct": correct_idx,
                "pdf_answer": pdf_answers_original[idx] if idx < len(pdf_answers_original) else ""  # PDF javobini saqlash
            })
        
        print(f"\n✅ Jami testlar: {len(quiz_data)} ta")
        print("="*60 + "\n")
        
        return quiz_data
        
    except Exception as e:
        print(f"❌ Ingliz tili PDF+DOCX parser xatosi: {e}")
        import traceback
        traceback.print_exc()
        return []
