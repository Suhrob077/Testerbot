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
                    options.append(option_text[:100]) # Telegram limiti
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
        # Separator va bo'sh qatorlarni tashlab faqat matnlarni olamiz
        raw_lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        clean_lines = []
        for line in raw_lines:
            if set(line).issubset({'=', '+', '-', '*', ' '}) and len(line) > 1:
                continue
            clean_lines.append(line)

        i = 0
        while i < len(clean_lines):
            line = clean_lines[i]
            # Savolni oxiridagi '?' yoki keyingi qator variant ekanligidan aniqlaymiz
            if line.endswith('?') or (i + 1 < len(clean_lines) and clean_lines[i+1].startswith('#')):
                question_text = line
                options = []
                correct_idx = 0
                i += 1
                
                temp_idx = 0
                # Keyingi savolga kelguncha variantlarni yig'amiz
                while i < len(clean_lines) and not clean_lines[i].endswith('?'):
                    # Agar yangi savol boshlanib qolsa (so'roqsiz bo'lsa ham)
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
    Falsafa va MT-V-A fanlari uchun parser.
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
# CHIZIQLAR VA ESKI FUNKSIYALARNING TAGIDAN SHUNDAYLIGICHA QO'SHIB QO'YING:

def get_quizzes_english_pdf_docx(docx_path, pdf_path):
    """
    Ingliz tili uchun yangi qo'shimcha parser.
    Mavjud parserlarga zarar yetkazmaydi.
    DOCX dan savol/variantlarni oladi, PDF dan qizil matnlarni indeks bo'yicha moslaydi.
    """
    try:
        # 1. PDF dan qizil rangli so'zlarni (to'g'ri javoblarni) tartib bilan yig'amiz
        pdf_answers = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                chars = page.chars
                current_word = []
                
                for char in chars:
                    # Rang parametrlarini tekshirish (non_stroking yoki stroking color)
                    color = char.get("non_stroking_color") or char.get("stroking_color")
                    is_red = False
                    
                    if color:
                        # Agar rang RGB formatida bo'lsa (0.0 - 1.0 yoki 0 - 255 oralig'ida)
                        if len(color) == 3:
                            r, g, b = color
                            if (r > 0.7 and g < 0.3 and b < 0.3) or (r == 255 and g == 0 and b == 0):
                                is_red = True
                    
                    if is_red:
                        current_word.append(char["text"])
                    else:
                        if current_word:
                            word_str = "".join(current_word).strip()
                            # Tartib raqamlar (1, 2, 3...) javob bo'lib kirmasligi uchun tekshiramiz
                            if word_str and not word_str.isdigit() and len(word_str) > 1:
                                pdf_answers.append(word_str.lower())
                            current_word = []
                
                if current_word:
                    word_str = "".join(current_word).strip()
                    if word_str and not word_str.isdigit() and len(word_str) > 1:
                        pdf_answers.append(word_str.lower())

        # 2. DOCX faylidan test strukturasini (4 qatorlik blok va chiziqlarni) o'qiymiz
        from docx import Document
        doc = Document(docx_path)
        quiz_data = []
        
        raw_lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        clean_lines = []
        for line in raw_lines:
            # Ajratuvchi pastki chiziqlar yoki keraksiz separatorlarni o'tkazib yuboramiz
            if set(line).issubset({'_', '=', '+', '-', '*', ' '}) and len(line) > 1:
                continue
            clean_lines.append(line)

        i = 0
        docx_quizzes = []
        
        while i < len(clean_lines):
            line = clean_lines[i]
            # Har bir test bloki 'choose' so'zi bilan boshlanadi
            if "choose the correct" in line.lower() or "choose the word" in line.lower():
                question_text = line
                options = []
                i += 1
                
                # Keyingi savol boshlanguncha variantlarni yig'ish (odatda 3 yoki 4 ta qator)
                while i < len(clean_lines) and not ("choose the correct" in clean_lines[i].lower() or "choose the word" in clean_lines[i].lower()):
                    options.append(clean_lines[i])
                    i += 1
                
                if len(options) >= 2:
                    docx_quizzes.append({
                        "question": question_text,
                        "options": options
                    })
            else:
                i += 1

        # 3. Indeks bo'yicha bog'lash (Index Mapping)
        for idx, docx_quiz in enumerate(docx_quizzes):
            correct_idx = 0  # Default qiymat
            
            if idx < len(pdf_answers):
                correct_answer_text = pdf_answers[idx]
                
                # PDF dan kelgan so'zni DOCX variantlari ichidan harflar bo'yicha qidiramiz
                for opt_idx, option in enumerate(docx_quiz["options"]):
                    if correct_answer_text in option.lower():
                        correct_idx = opt_idx
                        break
            
            quiz_data.append({
                "question": docx_quiz["question"][:250],
                "options": [opt[:100] for opt in docx_quiz["options"]][:10],
                "correct": correct_idx
            })

        return quiz_data
    except Exception as e:
        print(f"Ingliz tili PDF+DOCX kombinatsiyalangan parser xatosi: {e}")
        return []
