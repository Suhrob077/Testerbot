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
        return []
