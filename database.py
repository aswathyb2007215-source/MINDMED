import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), 'mindmed.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            location TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Baseline table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS baseline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            stress_baseline REAL,
            mood_baseline REAL,
            sleep_baseline REAL,
            energy_baseline REAL,
            anxiety_baseline REAL,
            burnout_baseline REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Assessments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            stress INTEGER NOT NULL,
            mood INTEGER NOT NULL,
            sleep INTEGER NOT NULL,
            energy INTEGER NOT NULL,
            anxiety INTEGER NOT NULL,
            depression INTEGER NOT NULL,
            burnout INTEGER NOT NULL,
            health_risk INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Mood check-ins table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mood_checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            mood_score INTEGER NOT NULL,
            mood_label TEXT NOT NULL,
            energy_score INTEGER DEFAULT 3,
            tags TEXT,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Professionals table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS professionals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialization TEXT NOT NULL,
            experience TEXT NOT NULL,
            location TEXT NOT NULL,
            availability TEXT NOT NULL,
            bio TEXT,
            rating REAL DEFAULT 4.9,
            avatar_color TEXT DEFAULT '#0F766E'
        )
    ''')

    # Appointments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            professional_id INTEGER NOT NULL,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            status TEXT DEFAULT 'Confirmed',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (professional_id) REFERENCES professionals(id)
        )
    ''')

    # Consent table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS consent (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            share_summary INTEGER DEFAULT 1,
            share_assessment INTEGER DEFAULT 1,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Chat messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            is_crisis INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Seed demo healthcare professionals if none exist
    cursor.execute('SELECT COUNT(*) FROM professionals')
    if cursor.fetchone()[0] == 0:
        demo_professionals = [
            (
                'Dr. Ananya Menon',
                'Mental Health Specialist & CBT Therapist',
                '8 years experience',
                'Kollam, Kerala',
                'Mon - Fri, 10:00 AM - 4:00 PM',
                'Specializes in stress management, cognitive behavioral therapy, anxiety screening, and life transitions.',
                4.9,
                '#0D9488'
            ),
            (
                'Dr. Rahul Nair',
                'Clinical Psychologist',
                '6 years experience',
                'Kochi, Kerala',
                'Tue - Sat, 11:00 AM - 6:00 PM',
                'Focuses on burnout prevention, workplace emotional regulation, mindfulness, and mood pattern observation.',
                4.8,
                '#0284C7'
            ),
            (
                'Dr. Priya Sharma',
                'Consultant Neuropsychologist',
                '10 years experience',
                'Bengaluru, Karnataka',
                'Mon - Thu, 9:00 AM - 3:00 PM',
                'Expertise in sleep architecture, cognitive load, restorative neuro-hygiene, and depressive symptom support.',
                4.9,
                '#7C3AED'
            ),
            (
                'Dr. Arjun Varma',
                'Consultant Psychiatrist',
                '12 years experience',
                'Thiruvananthapuram, Kerala',
                'Mon - Sat, 2:00 PM - 8:00 PM',
                'Specializes in comprehensive psychiatric evaluations, anxiety management, and holistic lifestyle coordination.',
                5.0,
                '#EA580C'
            ),
            (
                'Dr. Meera Krishnan',
                'Wellbeing & Resilience Counselor',
                '5 years experience',
                'Kozhikode, Kerala',
                'Daily, 10:00 AM - 5:00 PM',
                'Guides students and young professionals dealing with academic strain, social anxiety, and career fatigue.',
                4.7,
                '#059669'
            )
        ]
        cursor.executemany('''
            INSERT INTO professionals (name, specialization, experience, location, availability, bio, rating, avatar_color)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', demo_professionals)

    # Seed a demo user for quick evaluation if desired by judges
    cursor.execute('SELECT COUNT(*) FROM users WHERE email = ?', ('demo@mindmed.health',))
    if cursor.fetchone()[0] == 0:
        demo_pass = generate_password_hash('mindmed123')
        cursor.execute('''
            INSERT INTO users (name, email, password, age, gender, location)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('Aswathy Kumar', 'demo@mindmed.health', demo_pass, 24, 'Female', 'Kochi, Kerala'))
        user_id = cursor.lastrowid

        # Seed demo baseline
        cursor.execute('''
            INSERT INTO baseline (user_id, stress_baseline, mood_baseline, sleep_baseline, energy_baseline, anxiety_baseline, burnout_baseline)
            VALUES (?, 2.0, 4.0, 4.0, 4.0, 2.0, 2.0)
        ''', (user_id,))

        # Seed initial baseline assessment
        cursor.execute('''
            INSERT INTO assessments (user_id, stress, mood, sleep, energy, anxiety, depression, burnout, health_risk, created_at)
            VALUES (?, 2, 4, 4, 4, 2, 1, 2, 1, datetime('now', '-3 days'))
        ''', (user_id,))

        # Seed recent assessment showing elevated stress for demonstration
        cursor.execute('''
            INSERT INTO assessments (user_id, stress, mood, sleep, energy, anxiety, depression, burnout, health_risk, created_at)
            VALUES (?, 4, 3, 2, 2, 4, 2, 4, 3, datetime('now', '-1 hours'))
        ''', (user_id,))

        # Seed consent
        cursor.execute('''
            INSERT INTO consent (user_id, share_summary, share_assessment)
            VALUES (?, 1, 1)
        ''', (user_id,))

        # Seed one sample appointment
        cursor.execute('''
            INSERT INTO appointments (user_id, professional_id, appointment_date, appointment_time, status, notes)
            VALUES (?, 1, '2026-09-25', '11:00 AM', 'Confirmed', 'Routine check-in regarding recent sleep and study workload.')
        ''', (user_id,))

        # Seed initial friendly chat
        cursor.execute('''
            INSERT INTO chat_messages (user_id, sender, message)
            VALUES (?, 'ai', 'Hello Aswathy! I am your MindMED Wellbeing Companion. I am here to listen, offer supportive strategies, and help you understand your wellbeing patterns. How are you feeling today?')
        ''', (user_id,))

        # Seed mood check-ins over recent days
        demo_moods = [
            (user_id, 4, 'Good', 4, 'Productive, Focused', 'Feeling balanced and got good sleep.', "datetime('now', '-4 days')"),
            (user_id, 4, 'Good', 3, 'Calm, Hopeful', 'Walked in the park during lunchtime.', "datetime('now', '-3 days')"),
            (user_id, 3, 'Okay', 3, 'Busy, Tired', 'Long meetings all afternoon.', "datetime('now', '-2 days')"),
            (user_id, 2, 'Low', 2, 'Stressed, Drained', 'Exam deadlines approaching, struggled to sleep.', "datetime('now', '-1 days')"),
            (user_id, 2, 'Anxious', 2, 'Overwhelmed, Restless', 'Mind racing about final presentations.', "datetime('now', '-2 hours')")
        ]
        for m in demo_moods:
            cursor.execute(f'''
                INSERT INTO mood_checkins (user_id, mood_score, mood_label, energy_score, tags, note, created_at)
                VALUES (?, ?, ?, ?, ?, ?, {m[6]})
            ''', (m[0], m[1], m[2], m[3], m[4], m[5]))

    conn.commit()
    conn.close()

def reset_demo_user_seed():
    """Helper to reset demo user state for testing or demonstration."""
    conn = get_db_connection()
    cursor = conn.cursor()
    user = cursor.execute('SELECT id FROM users WHERE email = ?', ('demo@mindmed.health',)).fetchone()
    if user:
        uid = user['id']
        cursor.execute('DELETE FROM assessments WHERE user_id = ?', (uid,))
        cursor.execute('DELETE FROM mood_checkins WHERE user_id = ?', (uid,))
        cursor.execute('DELETE FROM baseline WHERE user_id = ?', (uid,))

        cursor.execute('''
            INSERT INTO baseline (user_id, stress_baseline, mood_baseline, sleep_baseline, energy_baseline, anxiety_baseline, burnout_baseline)
            VALUES (?, 2.0, 4.0, 4.0, 4.0, 2.0, 2.0)
        ''', (uid,))

        cursor.execute('''
            INSERT INTO assessments (user_id, stress, mood, sleep, energy, anxiety, depression, burnout, health_risk, created_at)
            VALUES (?, 2, 4, 4, 4, 2, 1, 2, 1, datetime('now', '-7 days'))
        ''', (uid,))
        cursor.execute('''
            INSERT INTO assessments (user_id, stress, mood, sleep, energy, anxiety, depression, burnout, health_risk, created_at)
            VALUES (?, 4, 3, 2, 2, 4, 2, 4, 3, datetime('now', '-1 hours'))
        ''', (uid,))

        demo_moods = [
            (uid, 4, 'Good', 4, 'Productive', 'Balanced day', "datetime('now', '-3 days')"),
            (uid, 3, 'Okay', 3, 'Busy', 'Long workload', "datetime('now', '-2 days')"),
            (uid, 2, 'Anxious', 2, 'Overwhelmed', 'Exam deadlines approaching', "datetime('now', '-2 hours')")
        ]
        for m in demo_moods:
            cursor.execute(f'''
                INSERT INTO mood_checkins (user_id, mood_score, mood_label, energy_score, tags, note, created_at)
                VALUES (?, ?, ?, ?, ?, ?, {m[6]})
            ''', (m[0], m[1], m[2], m[3], m[4], m[5]))

        conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("MindMED database initialized successfully.")
