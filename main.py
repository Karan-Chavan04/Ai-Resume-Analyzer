from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
import pdfplumber
import sqlite3
import os
import re
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ADMIN_SECRET = "my_super_secret_123" 

@app.delete("/delete_job/{job_id}")
async def delete_job(job_id: int, secret: str = None):
    if secret != ADMIN_SECRET:
        return {"status": "error", "message": "Unauthorized! You don't have the key."}
    
    conn = sqlite3.connect('platform.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Job deleted"}

@app.delete("/delete_candidate/{c_id}")
async def delete_candidate(c_id: int, secret: str = None):
    if secret != ADMIN_SECRET:
        return {"status": "error", "message": "Unauthorized!"}
    
    conn = sqlite3.connect('platform.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM candidates WHERE id = ?", (c_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Profile deleted"}

def init_db():
    conn = sqlite3.connect('platform.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS candidates 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT, skills TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS jobs 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, company TEXT, 
                       description TEXT, required_skills TEXT, created_at TEXT)''')
    conn.commit()
    conn.close()

init_db()

SKILL_BANK = ["python", "c++", "java", "javascript", "react", "html", "css", "sql", "node.js", "data structure", "algorithms", "c", "ms office", "vs code"]

def extract_skills_advanced(text):
    text = text.lower()
    found = []
    for skill in SKILL_BANK:
        # Using Regex boundaries to ensure we don't match 'c' inside 'cloud'
        pattern = rf"\b{re.escape(skill)}\b"
        if re.search(pattern, text):
            found.append(skill)
    return list(set(found))

@app.post("/register_candidate")
async def register_candidate(name: str = Form(...), email: str = Form(...), file: UploadFile = File(...)):
    with open("temp.pdf", "wb") as buffer:
        buffer.write(await file.read())
    with pdfplumber.open("temp.pdf") as pdf:
        resume_text = " ".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    os.remove("temp.pdf")
    
    resume_skills = extract_skills_advanced(resume_text)
    
    conn = sqlite3.connect('platform.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO candidates (name, email, skills) VALUES (?, ?, ?)", 
                   (name, email, ",".join(resume_skills)))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Candidate {name} registered!"}

@app.post("/post_job")
async def post_job(title: str = Form(...), company: str = Form(...), description: str = Form(...)):
    required_skills = extract_skills_advanced(description)
    timestamp = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    
    conn = sqlite3.connect('platform.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO jobs (title, company, description, required_skills, created_at) VALUES (?, ?, ?, ?, ?)", 
                   (title, company, description, ",".join(required_skills), timestamp))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Job posted!"}

@app.get("/list_jobs")
async def list_jobs():
    conn = sqlite3.connect('platform.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, company, created_at FROM jobs ORDER BY id DESC")
    jobs = cursor.fetchall()
    conn.close()
    return [{"id": j[0], "title": j[1], "company": j[2], "date": j[3]} for j in jobs]

@app.get("/list_candidates")
async def list_candidates():
    conn = sqlite3.connect('platform.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM candidates ORDER BY id DESC")
    candidates = cursor.fetchall()
    conn.close()
    return [{"id": c[0], "name": c[1]} for c in candidates]

@app.get("/get_matches_for_job/{job_id}")
async def get_matches_for_job(job_id: int):
    conn = sqlite3.connect('platform.db')
    cursor = conn.cursor()
    cursor.execute("SELECT title, required_skills FROM jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    if not job: return {"error": "Job not found"}
    job_title, job_skills_str = job
    job_skills_set = set(job_skills_str.split(",")) if job_skills_str else set()
    cursor.execute("SELECT name, email, skills FROM candidates")
    candidates = cursor.fetchall()
    results = []
    for name, email, c_skills in candidates:
        c_set = set(c_skills.split(",")) if c_skills else set()
        matches = c_set.intersection(job_skills_set)
        score = (len(matches) / len(job_skills_set)) * 100 if job_skills_set else 0
        results.append({"name": name, "email": email, "score": round(score, 2)})
    conn.close()
    return {"job_title": job_title, "results": sorted(results, key=lambda x: x['score'], reverse=True)}

@app.get("/get_jobs_for_candidate/{candidate_id}")
async def get_jobs_for_candidate(candidate_id: int):
    conn = sqlite3.connect('platform.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, skills FROM candidates WHERE id = ?", (candidate_id,))
    cand = cursor.fetchone()
    if not cand: return {"error": "Not found"}
    name, c_skills = cand
    c_set = set(c_skills.split(",")) if c_skills else set()
    cursor.execute("SELECT id, title, company, required_skills FROM jobs")
    jobs = cursor.fetchall()
    matches = []
    for j_id, title, comp, r_skills in jobs:
        r_set = set(r_skills.split(",")) if r_skills else set()
        score = (len(c_set.intersection(r_set)) / len(r_set)) * 100 if r_set else 0
        matches.append({"title": title, "company": comp, "score": round(score, 2), "missing": list(r_set - c_set)})
    conn.close()
    return {"candidate_name": name, "available_jobs": sorted(matches, key=lambda x: x['score'], reverse=True)}

@app.get("/export_job_report/{job_id}", response_class=PlainTextResponse)
async def export_report(job_id: int):
    data = await get_matches_for_job(job_id)
    report = f"MATCH REPORT: {data['job_title']}\n" + "="*30 + "\n"
    for r in data['results']:
        report += f"{r['score']}% - {r['name']} ({r['email']})\n"
    return report