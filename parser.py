from docx import Document
import re

def get_quizzes_programming(file_path):
    """
    Dasturlash fani uchun maxsus parser.
    Format:
    - Savol matni (masalan: "Savol №\nString dan char ga o'tish uchun ... funksiyalaridan foydalaniladi?")
    - 4 ta variant (har biri "—" bilan boshlanadi)
    - To'g'ri javob har doim BIRINCHI variant
    """
    try:
        doc = Document(file_path)
        quiz_data = []
        
        # Barcha paragraflarni o'qish
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        
        i = 0
        while i < len(paragraphs):
            # Savol raqamini topish (masalan "Savol №")
            if "Savol" in paragraphs[i] or "савол" in paragraphs[i].lower():
                question_parts = []
                i += 1
                
                # Savol matnini yig'ish (— belgisiga yetguncha)
                while i < len(paragraphs) and not paragraphs[i].startswith("—"):
                    question_parts.append(paragraphs[i])
                    i += 1
                
                question_text = " ".join(question_parts).strip()
                
                # Variantlarni yig'ish
                options = []
                while i < len(paragraphs) and paragraphs[i].startswith("—"):
                    # "—" belgisini olib tashlash
                    option_text = paragraphs[i].replace("—", "").strip()
                    
                    # Telegram limiti: variant 100 belgidan oshmasligi kerak
                    if len(option_text) > 100:
                        option_text = option_text[:97] + "..."
                    
                    options.append(option_text)
                    i += 1
                
                # Agar kamida 2 ta variant bo'lsa, qo'shamiz
                if len(options) >= 2 and question_text:
                    # Savol matnini 250 belgigacha qisqartirish
                    if len(question_text) > 250:
                        question_text = question_text[:247] + "..."
                    
                    quiz_data.append({
                        "question": question_text,
                        "options": options[:10],  # Max 10 variant
                        "correct": 0  # To'g'ri javob har doim BIRINCHI variant
                    })
            else:
                i += 1
        
        return quiz_data
    except Exception as e:
        print(f"Dasturlash parser xatosi: {e}")
        return []


def get_quizzes(file_path):
    """
    Falsafa va MT-V-A fanlari uchun eski parser.
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
            question_text = parts[0].strip()
            options_raw = [p.strip() for p in parts[1:] if p.strip()]
            
            correct_index = 0
            final_options = []
            
            for i, opt in enumerate(options_raw):
                clean_opt = opt.replace("#", "").strip()
                # Telegram limiti: variant 100 belgidan oshmasligi kerak
                if len(clean_opt) > 100:
                    clean_opt = clean_opt[:97] + "..."
                
                if opt.startswith("#"):
                    correct_index = i
                
                final_options.append(clean_opt)
            
            if len(final_options) >= 2:
                # Savol matnini 250 belgigacha qisqartirish
                quiz_data.append({
                    "question": question_text[:250],
                    "options": final_options[:10],    # Max 10 variant
                    "correct": correct_index
                })
        return quiz_data
    except Exception as e:
        print(f"Parser xatosi: {e}")
        return []
