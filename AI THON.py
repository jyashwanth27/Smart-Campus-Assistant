"""
Campus Chatbot (single-file Flask app)

Features:
- Simple web chat UI (served from `GET /`)
- /api/chat endpoint for conversational queries
- SQLite campus database with tables for faqs, schedules, dining, facilities, library
- Lightweight retrieval from the DB (keyword matching) + optional OpenAI fallback if OPENAI_API_KEY is set
- Admin endpoint /admin/init_db to create and populate sample data (run once)

How to run:
1. python3 -m venv venv
2. source venv/bin/activate  (or venv\Scripts\activate on Windows)
3. pip install flask openai
4. python campus_chatbot.py
5. Visit http://127.0.0.1:5000/ and chat

Note: Using the OpenAI fallback is optional. If you want the app to call OpenAI, set env var OPENAI_API_KEY.
"""
from flask import Flask, request, jsonify, render_template_string, g
import sqlite3
import os
import re
import json
try:
    import openai
except Exception:
    openai = None

DATABASE = 'campus.db'
app = Flask(__name__)

# ------------------------- Database helpers -------------------------

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

# ------------------------- Simple retrieval logic -------------------------

def normalize_text(s):
    return re.sub(r"[^a-z0-9 ]", " ", s.lower())

def retrieve_from_faqs(user_text, limit=3):
    # Tokenize and try to match keywords in question/answer text
    tokens = [t for t in normalize_text(user_text).split() if len(t) > 2]
    if not tokens:
        return []

    # Build dynamic SQL to score rows by number of matched tokens (simple)
    sql = "SELECT id, category, question, answer, ("
    sql += " + ".join([f"(question LIKE '%' || ? || '%' OR answer LIKE '%' || ? || '%')" for _ in tokens])
    sql += ") AS score FROM faqs WHERE "
    sql += " OR ".join([f"question LIKE '%' || ? || '%' OR answer LIKE '%' || ? || '%'" for _ in tokens])
    sql += " ORDER BY score DESC LIMIT ?"

    # params: for score piece (tokens repeated) then for where clause then limit
    params = tokens * 4 + [limit]
    rows = query_db(sql, params)
    # filter rows with zero score
    results = [dict(r) for r in rows if r['score'] and r['score'] > 0]
    return results

# Utility to fetch schedule/facility/dining/library using keywords

def retrieve_by_table(user_text, table, searchable_cols, limit=3):
    tokens = [t for t in normalize_text(user_text).split() if len(t) > 2]
    if not tokens:
        return []

    sql = f"SELECT * FROM {table} WHERE " + " OR ".join([" OR ".join([f"{col} LIKE '%' || ? || '%'" for col in searchable_cols]) for _ in tokens]) + " LIMIT ?"
    params = []
    for t in tokens:
        params.extend([t] * len(searchable_cols))
    params.append(limit)
    rows = query_db(sql, params)
    return [dict(r) for r in rows]

# ------------------------- Chatbot behavior -------------------------

def chatbot_response(user_message):
    # 1) Try faqs (quick wins)
    faqs = retrieve_from_faqs(user_message)
    if faqs:
        # Combine top results into a single answer
        parts = [f"[{r['category']}] {r['question']}\nAnswer: {r['answer']}" for r in faqs]
        return "\n\n".join(parts)

    # 2) Try specialized tables (schedule, dining, library, facilities)
    # Heuristics: look for keywords
    low = user_message.lower()
    if any(k in low for k in ['schedule', 'time', 'timetable', 'class']):
        sched = retrieve_by_table(user_message, 'schedules', ['dept', 'course', 'details'])
        if sched:
            return json.dumps(sched, indent=2)
    if any(k in low for k in ['canteen', 'dining', 'menu', 'mess']):
        din = retrieve_by_table(user_message, 'dining', ['name', 'menu', 'notes'])
        if din:
            return json.dumps(din, indent=2)
    if any(k in low for k in ['library', 'books', 'borrow', 'renew']):
        lib = retrieve_by_table(user_message, 'library', ['section', 'services', 'notes'])
        if lib:
            return json.dumps(lib, indent=2)
    if any(k in low for k in ['lab', 'facility', 'gym', 'parking', 'hostel']):
        fac = retrieve_by_table(user_message, 'facilities', ['name', 'description', 'location'])
        if fac:
            return json.dumps(fac, indent=2)

    # 3) Optional: if OpenAI is configured, call it for a friendly reply
    if openai and os.environ.get('OPENAI_API_KEY'):
        try:
            openai.api_key = os.environ.get('OPENAI_API_KEY')
            prompt = (
                "You are a helpful campus assistant. The user asks: " + user_message +
                "\n\nAnswer concisely and mention if you couldn't find structured data."
            )
            completion = openai.Completion.create(
                model='gpt-4o',
                prompt=prompt,
                max_tokens=300,
                temperature=0.2,
            )
            text = completion.choices[0].text.strip()
            return text
        except Exception as e:
            # last resort fallback
            return "Sorry, I couldn't find an exact answer in the campus DB and an external fallback failed: " + str(e)

    # 4) Final fallback: generic helpful reply
    return (
        "I couldn't find a direct match in the campus database. "
        "Try asking about specific keywords like 'library hours', 'CS department schedule', 'canteen menu', or 'how to apply for leave'."
    )

# ------------------------- Routes -------------------------

INDEX_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Campus Chatbot</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 800px; margin: 20px auto; }
    #chat { border: 1px solid #ddd; padding: 12px; height: 400px; overflow: auto; }
    .msg { margin: 8px 0; }
    .user { text-align: right; }
    .assistant { text-align: left; }
    #input { width: 100%; padding: 8px; }
    button { padding: 8px 12px; }
    pre { white-space: pre-wrap; word-wrap: break-word; }
  </style>
</head>
<body>
  <h1>Campus Chatbot</h1>
  <p>Ask about schedules, dining, facilities, library, or administrative procedures.</p>
  <div id="chat"></div>
  <div>
    <input id="input" placeholder="Type your question..." />
    <button id="send">Send</button>
  </div>
  <script>
    const chat = document.getElementById('chat')
    const input = document.getElementById('input')
    const send = document.getElementById('send')

    function append(msg, cls){
      const d = document.createElement('div')
      d.className = 'msg ' + cls
      if (cls === 'user') d.textContent = 'You: ' + msg
      else d.innerHTML = '<strong>Bot:</strong> <pre>' + msg + '</pre>'
      chat.appendChild(d)
      chat.scrollTop = chat.scrollHeight
    }

    async function sendMsg(){
      const text = input.value.trim()
      if (!text) return
      append(text, 'user')
      input.value = ''
      append('...', 'assistant')
      const res = await fetch('/api/chat', {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({message: text})
      })
      const data = await res.json()
      // replace last assistant '...' with real content
      const nodes = chat.querySelectorAll('.assistant')
      nodes[nodes.length - 1].innerHTML = '<strong>Bot:</strong> <pre>' + data.reply + '</pre>'
    }

    send.addEventListener('click', sendMsg)
    input.addEventListener('keydown', (e)=>{ if (e.key === 'Enter') sendMsg() })
  </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.get_json() or {}
    message = data.get('message', '')
    reply = chatbot_response(message)
    return jsonify({'reply': reply})

# Admin route to init DB and insert sample data
@app.route('/admin/init_db')
def init_db():
    db = get_db()
    cur = db.cursor()
    # Create tables
    cur.executescript('''
    DROP TABLE IF EXISTS faqs;
    DROP TABLE IF EXISTS schedules;
    DROP TABLE IF EXISTS dining;
    DROP TABLE IF EXISTS facilities;
    DROP TABLE IF EXISTS library;

    CREATE TABLE faqs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        question TEXT,
        answer TEXT
    );

    CREATE TABLE schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dept TEXT,
        course TEXT,
        details TEXT
    );

    CREATE TABLE dining (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        menu TEXT,
        notes TEXT
    );

    CREATE TABLE facilities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        description TEXT,
        location TEXT
    );

    CREATE TABLE library (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        section TEXT,
        services TEXT,
        notes TEXT
    );
    ''')

    # Insert sample data
    faqs = [
        ('Admissions', 'How do I apply for admission?', 'Visit the admissions portal on the college website, fill the form, and submit required documents.'),
        ('Exams', 'What is the exam application deadline?', 'Exam application deadlines are posted on the academic calendar. Typically 2-3 weeks before exams.'),
        ('Leave', 'How do I apply for leave?', 'Submit a leave application through the student portal or at the registrar office with supporting documents.'),
    ]
    cur.executemany('INSERT INTO faqs (category, question, answer) VALUES (?, ?, ?)', faqs)

    schedules = [
        ('Computer Science', 'B.Tech CS - 3rd Year', 'Mon/Wed/Fri 10:00-11:30, Room CS-201'),
        ('Mechanical', 'B.Tech ME - 2nd Year', 'Tue/Thu 09:00-10:30, Room ME-103'),
    ]
    cur.executemany('INSERT INTO schedules (dept, course, details) VALUES (?, ?, ?)', schedules)

    dining = [
        ('Main Canteen', 'Breakfast: 7-9 AM; Lunch: 12-2 PM; Dinner: 7-9 PM', 'Accepts cash and card. Veg & non-veg options.'),
        ('North Mess', 'Daily thali, specials on weekends', 'Open to hostel residents.'),
    ]
    cur.executemany('INSERT INTO dining (name, menu, notes) VALUES (?, ?, ?)', dining)

    facilities = [
        ('Gym', 'Open 6 AM - 10 PM, equipment for cardio and weights', 'Building A, Ground Floor'),
        ('Parking', 'Student parking available in Lot C', 'Entrance near Gate 2'),
    ]
    cur.executemany('INSERT INTO facilities (name, description, location) VALUES (?, ?, ?)', facilities)

    library = [
        ('Reference', 'In-library reference books, cannot be borrowed', 'Open 8 AM - 8 PM'),
        ('Borrowing', 'Students can borrow up to 5 books for 15 days', 'Renewal possible twice online'),
    ]
    cur.executemany('INSERT INTO library (section, services, notes) VALUES (?, ?, ?)', library)

    db.commit()
    return 'Initialized campus.db with sample data. You can now use the chatbot.'

if __name__ == '__main__':
    # If DB doesn't exist, create it automatically with init data
    if not os.path.exists(DATABASE):
        with app.app_context():
            init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
