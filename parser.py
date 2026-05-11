import pdfplumber
import spacy

# 1. Initialize the NLP Engine
# This loads the 'Brain' we downloaded (en_core_web_sm)
nlp = spacy.load("en_core_web_sm")

def extract_resume_info(pdf_path):
    # 2. PDF Extraction Logic
    # We open the PDF and extract every character into a single Python string
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
    
    # 3. NLP Processing
    # We pass the text to SpaCy. It breaks the text into 'Tokens' (words/entities)
    doc = nlp(text.lower()) # We use .lower() for uniform matching

    # 4. Skill Extraction Logic
    # In a real project, this list would be huge or come from a database.
    # For now, let's use these common tech skills:
    # Expanded Skill Bank to match your actual resume
    skill_bank = [
        "python", "c++", "java", "javascript", "react", "html", "css", "sql", "node.js",
        "data structure and algorithms", "ms office", "vs code", "c"
    ]
    
    found_skills = []
    # Check for multi-word phrases first (like 'Data Structure and Algorithms')
    for skill in skill_bank:
        if skill in text.lower():
            if skill not in found_skills:
                found_skills.append(skill)
            
    return found_skills

# --- Main Execution ---
# Replace 'my_resume.pdf' with the name of your actual PDF file!
filename = "my_resume.pdf" 

print(f"--- Analyzing: {filename} ---")
try:
    results = extract_resume_info(filename)
    print("Skills identified by AI:", results)
except FileNotFoundError:
    print(f"Error: Could not find {filename}. Please put it in the AI_engine folder.")