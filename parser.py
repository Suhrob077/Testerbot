from docx import Document

def get_quizzes(file_path):
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
                else:
                    final_options.append(clean_opt)
            
            if len(final_options) >= 2:
                quiz_data.append({
                    "question": question_text[:300], # Savol limiti 300
                    "options": final_options[:10],    # Max 10 variant
                    "correct": correct_index
                })
        return quiz_data
    except Exception as e:
        print(f"Parser xatosi: {e}")
        return []