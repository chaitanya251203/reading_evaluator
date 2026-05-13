import sqlite3
try:
    conn = sqlite3.connect('reading_assessment.db')
    conn.execute("ALTER TABLE reading_sessions ADD COLUMN teacher_notes TEXT DEFAULT '';")
    conn.commit()
    conn.close()
    print("Column added")
except Exception as e:
    print(e)
