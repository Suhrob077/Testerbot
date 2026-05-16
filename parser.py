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
    # Faqat harflar va raqamlarni qoldirish
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    # Bir nechta bo'sh joyni bitta qilish
    text = re.sub(r'\s+', ' ', text)
    return text.strip().lower()

def get_quizzes_english_pdf_docx(docx_path, pdf_path):
    """
    Ingliz tili-{KIN} uchun PDF+DOCX parser.
    Harf-harf va uzunlik bo'yicha aniq taqqoslash.
    """
    try:
        print("\n" + "="*60)
        print("🔍 INGLIZ TILI PARSER BOSHLANDI")
        print("="*60)
        
        # =========================================================
        # 1-BOSQICH: PDF dan qizil rangli matnlarni olish
        # =========================================================
        pdf_answers = []
        pdf_answers_original = []  # Original holda saqlash (debug uchun)
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                chars = page.chars
                current_word = []
                
                for char in chars:
                    color = char.get("non_stroking_color") or char.get("stroking_color")
                    is_red = False
                    
                    if color and len(color) == 3:
                        r, g, b = color
                        # Qizil rangni aniqlash (kengaytirilgan chegaralar)
                        if (r > 0.6 and g < 0.4 and b < 0.4) or \
                           (isinstance(r, int) and r > 150 and g < 100 and b < 100):
                            is_red = True
                    
                    if is_red:
                        current_word.append(char["text"])
                    else:
                        if current_word:
                            word_str = "".join(current_word).strip()
                            # Raqamlar va juda qisqa matnlarni o'tkazib yuborish
                            if word_str and not word_str.isdigit() and len(word_str) > 1:
                                pdf_answers_original.append(word_str)
                                normalized = normalize_text(word_str)
                                if normalized:
                                    pdf_answers.append(normalized)
                            current_word = []
                
                # Sahifa oxirida qolgan so'zni tekshirish
                if current_word:
                    word_str = "".join(current_word).strip()
                    if word_str and not word_str.isdigit() and len(word_str) > 1:
                        pdf_answers_original.append(word_str)
                        normalized = normalize_text(word_str)
                        if normalized:
                            pdf_answers.append(normalized)
        
        print(f"\n✅ PDF dan topilgan javoblar: {len(pdf_answers)} ta")
        print("📋 Birinchi 10 ta javob:")
        for i in range(min(10, len(pdf_answers))):
            print(f"   [{i+1}] Original: '{pdf_answers_original[i]}' → Normalized: '{pdf_answers[i]}'")

        # =========================================================
        # 2-BOSQICH: DOCX dan savollar va variantlarni olish
        # =========================================================
        doc = Document(docx_path)
        raw_lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        
        # Separator chiziqlarni olib tashlash
        clean_lines = []
        for line in raw_lines:
            # Faqat chiziqlar va maxsus belgilardan iborat qatorlarni o'tkazib yuborish
            if set(line).issubset({'_', '=', '+', '-', '*', ' ', '—'}) and len(line) > 1:
                continue
            clean_lines.append(line)

        i = 0
        docx_quizzes = []
        
        while i < len(clean_lines):
            line = clean_lines[i]
            # Savolni aniqlash
            if "choose the correct" in line.lower() or "choose the word" in line.lower() or \
               "choose the best" in line.lower() or "select the correct" in line.lower():
                question_text = line
                options = []
                i += 1
                
                # Variantlarni yig'ish (keyingi savolga yetguncha)
                while i < len(clean_lines):
                    current_line = clean_lines[i]
                    # Yangi savol boshlanganini tekshirish
                    if "choose the correct" in current_line.lower() or \
                       "choose the word" in current_line.lower() or \
                       "choose the best" in current_line.lower() or \
                       "select the correct" in current_line.lower():
                        break
                    
                    # Agar qator variant bo'lsa (bo'sh emas va juda uzun emas)
                    if current_line and len(current_line) < 200:
                        options.append(current_line)
                    i += 1
                
                if len(options) >= 2:
                    docx_quizzes.append({
                        "question": question_text,
                        "options": options
                    })
            else:
                i += 1
        
        print(f"\n✅ DOCX dan topilgan savollar: {len(docx_quizzes)} ta")
        print("📋 Birinchi 3 ta savol:")
        for i in range(min(3, len(docx_quizzes))):
            print(f"   [{i+1}] {docx_quizzes[i]['question'][:60]}...")
            print(f"       Variantlar ({len(docx_quizzes[i]['options'])} ta): {docx_quizzes[i]['options']}")

        # =========================================================
        # 3-BOSQICH: HARF-HARF VA UZUNLIK BO'YICHA MAPPING
        # =========================================================
        quiz_data = []
        match_stats = {"perfect": 0, "partial": 0, "none": 0}
        
        for idx, docx_quiz in enumerate(docx_quizzes):
            correct_idx = 0  # Default birinchi variant
            match_type = "none"
            
            if idx < len(pdf_answers):
                pdf_answer = pdf_answers[idx]
                pdf_answer_len = len(pdf_answer)
                
                best_match_score = 0
                best_match_idx = 0
                
                # Har bir variantni tekshirish
                for opt_idx, option in enumerate(docx_quiz["options"]):
                    option_normalized = normalize_text(option)
                    option_len = len(option_normalized)
                    
                    # 1. TO'LIQ ANIQLIQ (100% mos kelish)
                    if pdf_answer == option_normalized:
                        correct_idx = opt_idx
                        match_type = "perfect"
                        best_match_score = 100
                        break
                    
                    # 2. PDF javobi variant ichida (substring)
                    if pdf_answer in option_normalized:
                        score = (pdf_answer_len / option_len) * 100
                        if score > best_match_score:
                            best_match_score = score
                            best_match_idx = opt_idx
                            match_type = "partial"
                    
                    # 3. Variant PDF javobi ichida (teskari substring)
                    if option_normalized in pdf_answer:
                        score = (option_len / pdf_answer_len) * 100
                        if score > best_match_score:
                            best_match_score = score
                            best_match_idx = opt_idx
                            match_type = "partial"
                
                # Agar to'liq mos kelish topilmasa, eng yaxshi qisman moslikni olish
                if match_type == "partial" and best_match_score >= 60:
                    correct_idx = best_match_idx
                
                match_stats[match_type] += 1
                
                # Debug ma'lumoti
                if idx < 5:  # Birinchi 5 ta uchun batafsil
                    print(f"\n🔗 Savol #{idx+1} Mapping:")
                    print(f"   PDF javob: '{pdf_answer}' (uzunlik: {pdf_answer_len})")
                    print(f"   DOCX variantlar:")
                    for opt_idx, opt in enumerate(docx_quiz["options"]):
                        opt_norm = normalize_text(opt)
                        marker = "✅" if opt_idx == correct_idx else "  "
                        print(f"   {marker} [{opt_idx}] '{opt}' → '{opt_norm}'")
                    print(f"   Match type: {match_type}, Score: {best_match_score:.1f}%")
            
            quiz_data.append({
                "question": docx_quiz["question"][:250],
                "options": [opt[:100] for opt in docx_quiz["options"]][:10],
                "correct": correct_idx
            })
        
        # =========================================================
        # YAKUNIY STATISTIKA
        # =========================================================
        print("\n" + "="*60)
        print("📊 YAKUNIY STATISTIKA:")
        print("="*60)
        print(f"✅ Jami testlar: {len(quiz_data)} ta")
        print(f"🎯 To'liq mos kelish (Perfect): {match_stats['perfect']} ta")
        print(f"⚠️ Qisman mos kelish (Partial): {match_stats['partial']} ta")
        print(f"❌ Mos kelish topilmadi: {match_stats['none']} ta")
        print(f"📈 Muvaffaqiyat darajasi: {((match_stats['perfect'] + match_stats['partial']) / len(quiz_data) * 100):.1f}%")
        print("="*60 + "\n")
        
        return quiz_data
        
    except Exception as e:
        print(f"❌ Ingliz tili PDF+DOCX parser xatosi: {e}")
        import traceback
        traceback.print_exc()
        return []
