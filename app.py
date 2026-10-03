import os
import re
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection, init_db

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'mindmed-hackathon-secure-session-key-2026')

# Initialize database on startup
init_db()

# Non-diagnostic disclaimer text constant
MEDICAL_DISCLAIMER = (
    "MINDMED provides wellbeing screening and early-awareness support. "
    "It does not provide medical diagnosis and does not replace qualified healthcare professionals."
)

@app.context_processor
def inject_global_context():
    """Make user info and disclaimer available across all templates."""
    user = None
    if 'user_id' in session:
        conn = get_db_connection()
        user = conn.execute('SELECT id, name, email, age, gender, location FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        conn.close()
    return {
        'current_user': user,
        'medical_disclaimer': MEDICAL_DISCLAIMER
    }

def login_required(f):
    """Decorator to require login for protected routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# AUTHENTICATION ROUTES
# ==========================================

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please enter both email and password.', 'error')
            return render_template('login.html', email=email)

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            flash(f"Welcome back, {user['name'].split()[0]}!", 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'error')
            return render_template('login.html', email=email)

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        age_str = request.form.get('age', '').strip()
        gender = request.form.get('gender', '').strip()
        location = request.form.get('location', '').strip()

        # Validations
        if not name or not email or not password or not confirm_password:
            flash('Please complete all required fields.', 'error')
            return render_template('signup.html', form_data=request.form)

        # Basic email format validation
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            flash('Please enter a valid email address.', 'error')
            return render_template('signup.html', form_data=request.form)

        # Password length validation
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('signup.html', form_data=request.form)

        # Password match validation
        if password != confirm_password:
            flash('Passwords do not match. Please re-enter.', 'error')
            return render_template('signup.html', form_data=request.form)

        age = None
        if age_str:
            try:
                age = int(age_str)
                if age < 10 or age > 120:
                    flash('Please enter a realistic age.', 'error')
                    return render_template('signup.html', form_data=request.form)
            except ValueError:
                flash('Age must be a valid number.', 'error')
                return render_template('signup.html', form_data=request.form)

        conn = get_db_connection()
        existing_user = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if existing_user:
            conn.close()
            flash('An account with this email already exists. Please log in.', 'error')
            return render_template('signup.html', form_data=request.form)

        # Hash password and insert user
        hashed_password = generate_password_hash(password)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (name, email, password, age, gender, location)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, email, hashed_password, age, gender or 'Prefer not to say', location or 'Not specified'))
        user_id = cursor.lastrowid

        # Create empty baseline record for user
        cursor.execute('''
            INSERT INTO baseline (user_id, stress_baseline, mood_baseline, sleep_baseline, energy_baseline, anxiety_baseline, burnout_baseline)
            VALUES (?, NULL, NULL, NULL, NULL, NULL, NULL)
        ''', (user_id,))

        # Create default consent record
        cursor.execute('''
            INSERT INTO consent (user_id, share_summary, share_assessment)
            VALUES (?, 1, 1)
        ''', (user_id,))

        # Welcome message from AI companion
        welcome_ai = f"Welcome to MINDMED, {name.split()[0]}! I am your AI Wellbeing Companion. Feel free to talk to me about how your day is going, or start by taking your first Wellbeing Check to create your baseline."
        cursor.execute('''
            INSERT INTO chat_messages (user_id, sender, message)
            VALUES (?, 'ai', ?)
        ''', (user_id, welcome_ai))

        conn.commit()
        conn.close()

        # Log user in
        session['user_id'] = user_id
        session['user_name'] = name
        flash(f'Account created successfully! Welcome to MINDMED, {name.split()[0]}.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('signup.html', form_data={})

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out securely.', 'info')
    return redirect(url_for('login'))

# ==========================================
# DASHBOARD & LOGIC
# ==========================================

def get_indication_label(score):
    """Transparent non-diagnostic risk indicator scale."""
    if score is None:
        return {"level": "Not Assessed", "class": "badge-neutral", "text": "No data yet"}
    if score <= 2:
        return {"level": "Low Indication", "class": "badge-low", "text": "Within typical balanced range"}
    elif score == 3:
        return {"level": "Moderate Indication", "class": "badge-moderate", "text": "Mild to moderate pattern worth watching"}
    elif score == 4:
        return {"level": "Elevated Indication", "class": "badge-elevated", "text": "Elevated pattern; proactive rest recommended"}
    else:
        return {"level": "Needs Attention", "class": "badge-high", "text": "Marked indication; consider professional support"}

def analyze_early_awareness(latest_assessment, baseline):
    """
    Early warning pattern detection:
    Detects if 2 or more indicators have shifted unfavorably compared to baseline.
    Never gives medical diagnosis; identifies patterns worth monitoring.
    """
    if not latest_assessment or not baseline or baseline['stress_baseline'] is None:
        return None

    deviations = []

    # Stress (higher is worse)
    stress_delta = latest_assessment['stress'] - baseline['stress_baseline']
    if stress_delta >= 1.0:
        deviations.append({
            'metric': 'Stress Load',
            'change': f"+{stress_delta:.1f}",
            'description': 'Recent responses indicate heightened mental tension compared to your typical baseline.'
        })

    # Sleep (lower is worse)
    sleep_delta = latest_assessment['sleep'] - baseline['sleep_baseline']
    if sleep_delta <= -1.0:
        deviations.append({
            'metric': 'Sleep Quality & Duration',
            'change': f"{sleep_delta:.1f}",
            'description': 'Sleep restoration scores have fallen below your established baseline.'
        })

    # Energy (lower is worse)
    energy_delta = latest_assessment['energy'] - baseline['energy_baseline']
    if energy_delta <= -1.0:
        deviations.append({
            'metric': 'Daily Energy Level',
            'change': f"{energy_delta:.1f}",
            'description': 'Reported energy reserves show a meaningful downward shift from your norm.'
        })

    # Burnout (higher is worse)
    burnout_delta = latest_assessment['burnout'] - baseline['burnout_baseline']
    if burnout_delta >= 1.0:
        deviations.append({
            'metric': 'Burnout & Exhaustion Strain',
            'change': f"+{burnout_delta:.1f}",
            'description': 'Cognitive and physical recovery difficulty is tracking higher than usual.'
        })

    # Anxiety (higher is worse)
    anxiety_delta = latest_assessment['anxiety'] - baseline['anxiety_baseline']
    if anxiety_delta >= 1.0:
        deviations.append({
            'metric': 'Anxiety Tension Screening',
            'change': f"+{anxiety_delta:.1f}",
            'description': 'Worry and nervous activation are elevated compared to your baseline.'
        })

    # If 2 or more significant shifts are observed, generate early awareness notice
    if len(deviations) >= 2:
        return {
            'triggered': True,
            'title': 'MindMED Early Awareness Insight',
            'summary': 'We noticed meaningful shifts across multiple wellbeing responses compared with your personal baseline.',
            'pattern_message': 'Your responses show a pattern that may be worth monitoring for burnout-related strain or chronic overload.',
            'deviations': deviations,
            'recommendations': [
                "Schedule intentional 15-minute decompression blocks throughout your day without screen use.",
                "Protect an unbroken 7 to 8-hour sleep window with regular lights-out timing.",
                "Share your wellbeing summary with a qualified counselor or trusted support system."
            ]
        }
    return None

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    conn = get_db_connection()

    # Fetch latest assessment
    latest_assessment = conn.execute('''
        SELECT * FROM assessments
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 1
    ''', (user_id,)).fetchone()

    # Fetch total assessments count
    total_assessments = conn.execute('''
        SELECT COUNT(*) as count FROM assessments WHERE user_id = ?
    ''', (user_id,)).fetchone()['count']

    # Fetch baseline
    baseline = conn.execute('''
        SELECT * FROM baseline WHERE user_id = ?
    ''', (user_id,)).fetchone()

    # Fetch upcoming appointments
    appointments = conn.execute('''
        SELECT a.*, p.name as prof_name, p.specialization, p.location
        FROM appointments a
        JOIN professionals p ON a.professional_id = p.id
        WHERE a.user_id = ?
        ORDER BY a.appointment_date ASC, a.appointment_time ASC
        LIMIT 2
    ''', (user_id,)).fetchall()

    # Fetch recent mood check-ins
    recent_moods = conn.execute('''
        SELECT * FROM mood_checkins
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 5
    ''', (user_id,)).fetchall()

    # Mood streak / total checkins
    total_moods = conn.execute('''
        SELECT COUNT(*) as count FROM mood_checkins WHERE user_id = ?
    ''', (user_id,)).fetchone()['count']

    # Today's check-in
    today_checkin = conn.execute('''
        SELECT * FROM mood_checkins
        WHERE user_id = ? AND date(created_at) = date('now')
        ORDER BY created_at DESC
        LIMIT 1
    ''', (user_id,)).fetchone()

    # Historical assessments for Chart.js trend
    trend_assessments = conn.execute('''
        SELECT * FROM assessments
        WHERE user_id = ?
        ORDER BY created_at ASC
        LIMIT 10
    ''', (user_id,)).fetchall()

    conn.close()

    # Chart datasets
    chart_dates = [a['created_at'][5:10] for a in trend_assessments]
    chart_stress = [a['stress'] for a in trend_assessments]
    chart_mood = [a['mood'] for a in trend_assessments]
    chart_sleep = [a['sleep'] for a in trend_assessments]
    chart_energy = [a['energy'] for a in trend_assessments]
    chart_anxiety = [a['anxiety'] for a in trend_assessments]

    # Has baseline check
    has_baseline = (baseline is not None and baseline['stress_baseline'] is not None)

    # Radar balance data
    radar_labels = ['Stress', 'Mood', 'Sleep', 'Energy', 'Anxiety', 'Burnout']
    radar_current = []
    radar_baseline = []
    if latest_assessment:
        radar_current = [
            latest_assessment['stress'],
            latest_assessment['mood'],
            latest_assessment['sleep'],
            latest_assessment['energy'],
            latest_assessment['anxiety'],
            latest_assessment['burnout']
        ]
    if has_baseline:
        radar_baseline = [
            baseline['stress_baseline'],
            baseline['mood_baseline'],
            baseline['sleep_baseline'],
            baseline['energy_baseline'],
            baseline['anxiety_baseline'],
            baseline['burnout_baseline']
        ]

    # Comparisons and indications
    comparisons = {}
    risk_indicators = {}
    early_awareness = None

    if latest_assessment and has_baseline:
        # Core wellbeing comparisons
        metrics = [
            ('stress', 'Stress', baseline['stress_baseline'], latest_assessment['stress'], 'higher_is_worse'),
            ('mood', 'Mood & Positivity', baseline['mood_baseline'], latest_assessment['mood'], 'higher_is_better'),
            ('sleep', 'Sleep Quality', baseline['sleep_baseline'], latest_assessment['sleep'], 'higher_is_better'),
            ('energy', 'Energy Reserve', baseline['energy_baseline'], latest_assessment['energy'], 'higher_is_better')
        ]

        for key, name, base_val, curr_val, direction in metrics:
            delta = curr_val - base_val
            if direction == 'higher_is_worse':
                is_unfavorable = delta > 0.5
                is_favorable = delta < -0.5
            else:
                is_unfavorable = delta < -0.5
                is_favorable = delta > 0.5

            if abs(delta) < 0.3:
                note = f"Consistent with your usual baseline ({base_val:.1f}/5)."
            elif delta > 0:
                note = f"Your recent responses are higher than your baseline ({base_val:.1f}/5)."
            else:
                note = f"Your recent responses are lower than your baseline ({base_val:.1f}/5)."

            comparisons[key] = {
                'name': name,
                'current': curr_val,
                'baseline': base_val,
                'delta': round(delta, 1),
                'delta_str': f"+{delta:.1f}" if delta > 0 else f"{delta:.1f}",
                'is_unfavorable': is_unfavorable,
                'is_favorable': is_favorable,
                'note': note
            }

        # Risk indicators
        risk_indicators = {
            'anxiety': get_indication_label(latest_assessment['anxiety']),
            'depression': get_indication_label(latest_assessment['depression']),
            'burnout': get_indication_label(latest_assessment['burnout']),
            'health_risk': get_indication_label(latest_assessment['health_risk'])
        }

        # Early awareness detection
        early_awareness = analyze_early_awareness(latest_assessment, baseline)

    elif latest_assessment and not has_baseline:
        risk_indicators = {
            'anxiety': get_indication_label(latest_assessment['anxiety']),
            'depression': get_indication_label(latest_assessment['depression']),
            'burnout': get_indication_label(latest_assessment['burnout']),
            'health_risk': get_indication_label(latest_assessment['health_risk'])
        }

    return render_template(
        'dashboard.html',
        latest_assessment=latest_assessment,
        baseline=baseline,
        has_baseline=has_baseline,
        comparisons=comparisons,
        risk_indicators=risk_indicators,
        early_awareness=early_awareness,
        appointments=appointments,
        total_assessments=total_assessments,
        recent_moods=recent_moods,
        total_moods=total_moods,
        today_checkin=today_checkin,
        chart_dates=chart_dates,
        chart_stress=chart_stress,
        chart_mood=chart_mood,
        chart_sleep=chart_sleep,
        chart_energy=chart_energy,
        chart_anxiety=chart_anxiety,
        radar_labels=radar_labels,
        radar_current=radar_current,
        radar_baseline=radar_baseline
    )

@app.route('/api/mood-checkin', methods=['POST'])
@login_required
def api_mood_checkin():
    user_id = session['user_id']
    data = request.get_json() or {}
    try:
        mood_score = int(data.get('mood_score', 3))
        energy_score = int(data.get('energy_score', 3))
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid numerical values'}), 400

    mood_label = data.get('mood_label', 'Neutral').strip()
    tags = data.get('tags', '').strip()
    note = data.get('note', '').strip()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO mood_checkins (user_id, mood_score, mood_label, energy_score, tags, note)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, mood_score, mood_label, energy_score, tags, note))
    conn.commit()

    streak = cursor.execute('SELECT COUNT(*) as count FROM mood_checkins WHERE user_id = ?', (user_id,)).fetchone()['count']
    conn.close()

    return jsonify({
        'status': 'success',
        'message': f'Thank you! Your daily check-in as "{mood_label}" has been recorded.',
        'streak': streak,
        'mood_label': mood_label,
        'mood_score': mood_score,
        'created_at': datetime.now().strftime('%b %d, %I:%M %p')
    })

# ==========================================
# ASSESSMENT & RESULTS
# ==========================================

@app.route('/assessment', methods=['GET', 'POST'])
@login_required
def assessment():
    user_id = session['user_id']

    if request.method == 'POST':
        try:
            # Emotional Wellbeing (1-5)
            mood = int(request.form.get('mood', 3))
            stress = int(request.form.get('stress', 3))
            energy = int(request.form.get('energy', 3))
            sleep = int(request.form.get('sleep', 3))

            # Anxiety Screening (1-5 composite)
            anx_q1 = int(request.form.get('anx_nervous', 2))
            anx_q2 = int(request.form.get('anx_worry', 2))
            anxiety = round((anx_q1 + anx_q2) / 2)

            # Depression Risk Screening (1-5 composite)
            dep_q1 = int(request.form.get('dep_pleasure', 2))
            dep_q2 = int(request.form.get('dep_hopeless', 2))
            depression = round((dep_q1 + dep_q2) / 2)

            # Burnout Screening (1-5 composite)
            burn_q1 = int(request.form.get('burn_exhaustion', 2))
            burn_q2 = int(request.form.get('burn_motivation', 2))
            burn_q3 = int(request.form.get('burn_recovery', 2))
            burnout = round((burn_q1 + burn_q2 + burn_q3) / 3)

            # Health Risk Screening (1-5 composite)
            hlth_q1 = int(request.form.get('hlth_fatigue', 2))
            hlth_q2 = int(request.form.get('hlth_activity', 2))
            health_risk = round((hlth_q1 + hlth_q2) / 2)

            # Clamp all scores between 1 and 5
            scores = {k: max(1, min(5, v)) for k, v in {
                'mood': mood, 'stress': stress, 'energy': energy, 'sleep': sleep,
                'anxiety': anxiety, 'depression': depression, 'burnout': burnout,
                'health_risk': health_risk
            }.items()}

        except (ValueError, TypeError):
            flash('Please answer all assessment questions with valid selections.', 'error')
            return render_template('assessment.html')

        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert new assessment record
        cursor.execute('''
            INSERT INTO assessments (user_id, stress, mood, sleep, energy, anxiety, depression, burnout, health_risk)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            scores['stress'], scores['mood'], scores['sleep'], scores['energy'],
            scores['anxiety'], scores['depression'], scores['burnout'], scores['health_risk']
        ))
        assessment_id = cursor.lastrowid

        # Check existing baseline
        baseline = cursor.execute('SELECT * FROM baseline WHERE user_id = ?', (user_id,)).fetchone()

        if not baseline or baseline['stress_baseline'] is None:
            # First assessment becomes the personal baseline!
            cursor.execute('''
                INSERT OR REPLACE INTO baseline (user_id, stress_baseline, mood_baseline, sleep_baseline, energy_baseline, anxiety_baseline, burnout_baseline, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                user_id,
                float(scores['stress']), float(scores['mood']), float(scores['sleep']),
                float(scores['energy']), float(scores['anxiety']), float(scores['burnout'])
            ))
            flash('Your personal wellbeing baseline has been successfully established!', 'success')
        else:
            flash('Assessment completed! Your screening analysis is ready.', 'success')

        conn.commit()
        conn.close()

        return redirect(url_for('results', assessment_id=assessment_id))

    return render_template('assessment.html')

@app.route('/results')
@app.route('/results/<int:assessment_id>')
@login_required
def results(assessment_id=None):
    user_id = session['user_id']
    conn = get_db_connection()

    if assessment_id:
        assessment_record = conn.execute('''
            SELECT * FROM assessments WHERE id = ? AND user_id = ?
        ''', (assessment_id, user_id)).fetchone()
    else:
        assessment_record = conn.execute('''
            SELECT * FROM assessments WHERE user_id = ? ORDER BY created_at DESC LIMIT 1
        ''', (user_id,)).fetchone()

    baseline = conn.execute('SELECT * FROM baseline WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()

    if not assessment_record:
        flash('No assessment results found. Please complete a wellbeing check first.', 'info')
        return redirect(url_for('assessment'))

    # Build detailed personalized cards
    def build_metric_data(score, base_val, label, higher_is_worse=True, suggestions=None):
        ind = get_indication_label(score)
        delta_str = "N/A"
        delta_note = "Baseline comparison not yet available."
        delta = None
        if base_val is not None:
            delta = round(score - base_val, 1)
            delta_str = f"+{delta}" if delta > 0 else f"{delta}"
            if abs(delta) < 0.3:
                delta_note = f"Consistent with your usual baseline ({base_val:.1f}/5)."
            elif delta > 0:
                delta_note = f"Responses are higher (+{delta}) than your personal baseline ({base_val:.1f}/5)."
            else:
                delta_note = f"Responses are lower ({delta}) than your personal baseline ({base_val:.1f}/5)."

        return {
            'score': score,
            'label': label,
            'indication': ind,
            'baseline': base_val,
            'delta': delta,
            'delta_str': delta_str,
            'delta_note': delta_note,
            'suggestion': suggestions.get(ind['level'], suggestions.get('default', 'Continue monitoring your habits.'))
        }

    results_data = {
        'stress': build_metric_data(
            assessment_record['stress'],
            baseline['stress_baseline'] if baseline else None,
            'Stress Indicator',
            higher_is_worse=True,
            suggestions={
                'Low Indication': 'Your stress load is well-managed. Maintain healthy personal time boundaries.',
                'Moderate Indication': 'Mild stress noted. Introduce 5-minute breathing pauses and prioritize daily rest.',
                'Elevated Indication': 'Noticeably elevated stress. Consider delegating non-urgent tasks and talking with a mentor.',
                'Needs Attention': 'High stress indications. Proactively reduce obligations and consider speaking with a mental health specialist.'
            }
        ),
        'mood': build_metric_data(
            assessment_record['mood'],
            baseline['mood_baseline'] if baseline else None,
            'Mood & Emotional State',
            higher_is_worse=False,
            suggestions={
                'Low Indication': 'Your mood responses indicate feelings of low enthusiasm. Gentle social engagement and outdoors time may help.',
                'Moderate Indication': 'Neutral to moderate emotional tone. Engage in creative or calming hobbies you enjoy.',
                'Elevated Indication': 'Positive emotional resilience observed. Keep nurturing positive relationships.',
                'Needs Attention': 'Flourishing emotional vitality. Continue maintaining your balanced lifestyle.'
            }
        ),
        'sleep': build_metric_data(
            assessment_record['sleep'],
            baseline['sleep_baseline'] if baseline else None,
            'Sleep Restoration',
            higher_is_worse=False,
            suggestions={
                'Low Indication': 'Sleep restorative quality appears disrupted. Avoid evening blue light and keep consistent sleep hours.',
                'Moderate Indication': 'Fair sleep quality. Aim for 30 minutes of screen-free winding down before bed.',
                'Elevated Indication': 'Good restorative sleep reported. Maintain your sleep sanctuary and wake schedule.',
                'Needs Attention': 'Excellent sleep pattern. Consistent sleep is a prime pillar of mental well-being.'
            }
        ),
        'energy': build_metric_data(
            assessment_record['energy'],
            baseline['energy_baseline'] if baseline else None,
            'Daily Energy & Vitality',
            higher_is_worse=False,
            suggestions={
                'Low Indication': 'Low energy reserves detected. Stay hydrated, eat balanced meals, and take short walking breaks.',
                'Moderate Indication': 'Moderate energy. Watch out for midday slumps by balancing caffeine intake.',
                'Elevated Indication': 'Strong energy levels throughout the day.',
                'Needs Attention': 'High vitality. Excellent capacity for daily activities.'
            }
        ),
        'anxiety': build_metric_data(
            assessment_record['anxiety'],
            baseline['anxiety_baseline'] if baseline else None,
            'Anxiety-Risk Screening',
            higher_is_worse=True,
            suggestions={
                'Low Indication': 'No significant worry or nervous tension indicated.',
                'Moderate Indication': 'Mild anxious thoughts reported. Practicing box breathing or 5-4-3-2-1 grounding can provide relief.',
                'Elevated Indication': 'Frequent worry or nervousness detected. Journaling your worries or talking to our AI Companion can help de-escalate thoughts.',
                'Needs Attention': 'Marked anxiety pattern. We recommend consulting a licensed psychologist or counselor for structured guidance.'
            }
        ),
        'depression': build_metric_data(
            assessment_record['depression'],
            baseline['anxiety_baseline'] if baseline else None, # using baseline context
            'Depression-Risk Screening',
            higher_is_worse=True,
            suggestions={
                'Low Indication': 'Responses indicate steady interest, motivation, and positive outlook.',
                'Moderate Indication': 'Mild dips in pleasure or hopefulness noted. Reconnect with small uplifting daily rituals.',
                'Elevated Indication': 'Responses suggest reduced motivation or persistent low spirits worth monitoring.',
                'Needs Attention': 'Screening indicates sustained low mood. Consider speaking with a compassionate healthcare provider for professional support.'
            }
        ),
        'burnout': build_metric_data(
            assessment_record['burnout'],
            baseline['burnout_baseline'] if baseline else None,
            'Burnout-Risk Screening',
            higher_is_worse=True,
            suggestions={
                'Low Indication': 'Minimal signs of burnout or exhaustion. Healthy recovery capacity maintained.',
                'Moderate Indication': 'Occasional workplace or study fatigue. Establish firmer cut-off hours in the evenings.',
                'Elevated Indication': 'Responses suggest notable exhaustion and motivational strain. Prioritize restorative breaks immediately.',
                'Needs Attention': 'Significant burnout-related pattern detected. We strongly suggest taking structured time off and consulting a professional.'
            }
        ),
        'health_risk': build_metric_data(
            assessment_record['health_risk'],
            None,
            'Basic Health & Lifestyle Indicator',
            higher_is_worse=True,
            suggestions={
                'Low Indication': 'Lifestyle habits and physical vitality appear well balanced.',
                'Moderate Indication': 'Mild physical fatigue or lifestyle strain reported.',
                'Elevated Indication': 'Physical fatigue is impacting daily routines. Prioritize nutrition and physical activity.',
                'Needs Attention': 'High physical fatigue indicated. A routine physical check-up with a medical doctor is encouraged.'
            }
        )
    }

    # Early awareness calculation
    early_awareness = analyze_early_awareness(assessment_record, baseline)

    return render_template(
        'results.html',
        assessment=assessment_record,
        results_data=results_data,
        early_awareness=early_awareness,
        has_baseline=(baseline is not None and baseline['stress_baseline'] is not None)
    )

@app.route('/update-baseline', methods=['POST'])
@login_required
def update_baseline():
    """Recalibrate baseline using the latest assessment."""
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    latest = cursor.execute('''
        SELECT * FROM assessments WHERE user_id = ? ORDER BY created_at DESC LIMIT 1
    ''', (user_id,)).fetchone()

    if latest:
        cursor.execute('''
            INSERT OR REPLACE INTO baseline (user_id, stress_baseline, mood_baseline, sleep_baseline, energy_baseline, anxiety_baseline, burnout_baseline, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            user_id,
            float(latest['stress']), float(latest['mood']), float(latest['sleep']),
            float(latest['energy']), float(latest['anxiety']), float(latest['burnout'])
        ))
        conn.commit()
        flash('Your personal wellbeing baseline has been updated to your latest assessment!', 'success')
    else:
        flash('Please complete an assessment before calibrating your baseline.', 'warning')

    conn.close()
    return redirect(url_for('dashboard'))

# ==========================================
# AI WELLBEING COMPANION & CRISIS DETECTION
# ==========================================

CRISIS_KEYWORDS = [
    r'\bkill\s+(myself|me)\b',
    r'\bsuicid(e|al)\b',
    r'\bend\s+my\s+life\b',
    r'\bwant\s+to\s+die\b',
    r'\bdon\'?t\s+want\s+to\s+live\b',
    r'\bself[- ]?harm\b',
    r'\bhurt\s+myself\b',
    r'\bcutting\s+myself\b',
    r'\bno\s+reason\s+to\s+live\b',
    r'\bbetter\s+off\s+dead\b'
]

def check_crisis_intent(text):
    text_lower = text.lower()
    for pattern in CRISIS_KEYWORDS:
        if re.search(pattern, text_lower):
            return True
    return False

def generate_companion_reply(user_message, user_name="friend"):
    """Rule-based conversational engine designed for safe, supportive wellbeing dialogue."""
    msg = user_message.lower().strip()

    # Crisis & Safety Check
    if check_crisis_intent(msg):
        return {
            'is_crisis': True,
            'reply': (
                "🚨 **URGENT SAFETY & SUPPORT ALERT**\n\n"
                "I hear how much pain you are in right now, but please know that you do not have to go through this alone. "
                "There is immediate, compassionate help available 24/7:\n\n"
                "• **National Tele-MANAS Mental Health Helpline (India)**: Call **14416** or **1800-891-4416** (Toll-Free, 24/7)\n"
                "• **KIRAN Mental Health Helpline**: **1800-599-0019**\n"
                "• **988 Suicide & Crisis Lifeline (US & International)**: Call or text **988**\n"
                "• **Emergency Services**: Dial **112** (India), **911** (US), or reach out to your nearest hospital emergency room.\n\n"
                "Please reach out to a trusted family member, close friend, or qualified doctor immediately. "
                "MINDMED is an early-awareness screening tool and is not equipped to handle immediate emergencies. Your safety and life matter deeply."
            )
        }

    # Keyword Responses
    if any(w in msg for w in ['stress', 'stressed', 'overwhelm', 'pressure', 'too much']):
        reply = (
            f"I hear you, {user_name}. Feeling stressed is your nervous system's way of signaling that your demands exceed your current capacity for recovery.\n\n"
            "Here is a quick **2-Minute Reset** you can do right now:\n"
            "1. **Box Breathing**: Inhale deeply for 4 seconds, hold for 4 seconds, exhale gently for 4 seconds, hold for 4 seconds. Repeat 3 times.\n"
            "2. **The 3-Item Rule**: Write down only 3 essential tasks for today and grant yourself permission to defer the rest.\n"
            "3. **Physical Unclench**: Drop your shoulders down from your ears and relax your jaw.\n\n"
            "Would you like to check your stress score against your baseline or explore relaxation techniques?"
        )
    elif any(w in msg for w in ['sleep', 'insomnia', 'awake', 'can\'t sleep', 'nightmare', 'restless']):
        reply = (
            f"Sleep disruptions can make everything else feel much heavier, {user_name}. A few evidence-based non-medical sleep practices:\n\n"
            "• **The 20-Minute Rule**: If you cannot fall asleep after 20 minutes, get out of bed, sit in dim warm light, and read a quiet book until drowsiness returns.\n"
            "• **Thermal Drop**: Keep your bedroom cool (around 18–20°C / 65–68°F); the body needs to cool down to initiate deep sleep.\n"
            "• **Screen Sunset**: Try to keep screens away at least 45 minutes before sleep to allow your natural melatonin to rise.\n\n"
            "Your MindMED baseline tracks sleep patterns over time so you can observe if this is an isolated night or a trend worth monitoring."
        )
    elif any(w in msg for w in ['anxious', 'anxiety', 'panic', 'nervous', 'scared', 'worry', 'worried']):
        reply = (
            "When anxiety surges, cognitive logic often feels hijacked by physical alertness. Let's ground your senses together with the **5-4-3-2-1 Technique**:\n\n"
            "👁️ **5 things** you can see around your room\n"
            "✋ **4 things** you can physically touch right now\n"
            "👂 **3 distinct sounds** you can hear\n"
            "👃 **2 things** you can smell\n"
            "👅 **1 thing** you can taste or notice in your mouth\n\n"
            "Take a slow, deep breath. Remind yourself: *'This uncomfortable sensation is temporary, and I am safe in this room right now.'*"
        )
    elif any(w in msg for w in ['sad', 'down', 'depress', 'crying', 'unhappy', 'empty', 'hopeless', 'gloomy']):
        reply = (
            f"Thank you for trusting me with how you are feeling, {user_name}. It is completely valid to have days where your emotional energy is low.\n\n"
            "You do not have to force yourself to feel cheerful today. Instead, try offering yourself gentle compassion:\n"
            "• Drink a cup of warm water or tea.\n"
            "• Step outside for 5 minutes to feel natural sunlight on your face.\n"
            "• If you have the energy, send a simple emoji or greeting to a friend you trust.\n\n"
            "If these feelings linger for several weeks, having an open conversation with one of our verified mental health professionals on the Professionals page can provide structured, compassionate guidance."
        )
    elif any(w in msg for w in ['tired', 'fatigue', 'exhausted', 'drained', 'no energy', 'sleepy']):
        reply = (
            "Exhaustion can be physical, mental, or emotional. When we push past our limits without replenishment, our battery naturally dips.\n\n"
            "Ask yourself: **What kind of rest do I need right now?**\n"
            "• *Sensory Rest*: Turning off bright lights, screens, and headphones for 15 minutes.\n"
            "• *Mental Rest*: Setting aside work or study to do a repetitive, mindful task (like drawing, gentle stretching, or watering plants).\n"
            "• *Physical Rest*: A 20-minute power nap or lying down with elevated feet.\n\n"
            "Be kind to your body today—it is working hard to support you."
        )
    elif any(w in msg for w in ['exam', 'test', 'study', 'grades', 'college', 'school', 'assignment']):
        reply = (
            "Academic pressure can feel immense, but remember: **your worth as a human being is never defined by a test score or grade**.\n\n"
            "To conquer exam overwhelm:\n"
            "1. **Pomodoro Sprints**: Study with total focus for 25 minutes, then enforce a 5-minute break away from screens.\n"
            "2. **Active Recall over Rereading**: Quiz yourself on 3 key points instead of passively reading pages for hours.\n"
            "3. **Sleep Before Cramming**: Scientific research shows that memories consolidate during deep sleep. Sacrificing sleep often reduces exam performance.\n\n"
            "You have handled tough challenges before, and you can take this step by step."
        )
    elif any(w in msg for w in ['burnout', 'overworked', 'job', 'boss', 'deadlines', 'career']):
        reply = (
            "Burnout is not a personal failure; it is a predictable physical and cognitive reaction to chronic, unrelenting stress with inadequate boundaries.\n\n"
            "To begin reclaiming your bandwidth:\n"
            "• **Establish a hard shutdown ritual**: When your workday finishes, physically close your laptop and transition to an evening activity.\n"
            "• **Audit your commitments**: What is one meeting or task you can decline, delegate, or defer this week?\n"
            "• **Notice your baseline**: Check your MindMED dashboard to see if your burnout and sleep metrics have shifted together.\n\n"
            "Consider booking a consultation with one of our counselors for guidance on workload boundaries."
        )
    elif any(w in msg for w in ['lonely', 'alone', 'isolated', 'nobody', 'no friends']):
        reply = (
            "Feeling lonely can feel very isolating, but loneliness is a universal human signal telling us we crave connection—just like hunger signals the need for food.\n\n"
            "Small ways to cultivate connection today:\n"
            "• Send a quick text: *'Hey, was just thinking of you! Hope your week is going smoothly.'*\n"
            "• Work or read in a shared space like a local library or coffee shop for passive social warmth.\n"
            "• Remember that reaching out is a strength, and speaking with a counselor can offer a warm, confidential, non-judgmental space."
        )
    elif any(w in msg for w in ['baseline', 'how it works', 'what is mindmed', 'features', 'algorithm']):
        reply = (
            "**How MINDMED Works**:\n\n"
            "1. **Talk**: You can share your thoughts with me anytime in this safe, private companion chat.\n"
            "2. **Understand**: Take regular Wellbeing Checks across 8 dimensions (Stress, Mood, Sleep, Energy, Anxiety, Depression, Burnout, Health).\n"
            "3. **Detect**: MindMED creates a personal baseline unique to you. When new responses deviate significantly, our Early Awareness engine alerts you before burnout deepens.\n"
            "4. **Connect**: Seamlessly connect with vetted healthcare professionals and book appointments with full privacy consent control!"
        )
    elif any(w in msg for w in ['hello', 'hi', 'hey', 'good morning', 'good evening', 'greetings']):
        reply = (
            f"Hello {user_name}! 👋 It's wonderful to connect with you. I am here whenever you need a listening ear, a grounding exercise, or reflections on your wellbeing.\n\n"
            "How are you feeling mentally and physically today?"
        )
    elif any(w in msg for w in ['thank', 'thanks', 'helpful', 'appreciate']):
        reply = (
            f"You are so welcome, {user_name}! 🌿 Taking time to look after your mental wellbeing is something to be genuinely proud of. "
            "I'm here anytime you need to talk or reset."
        )
    else:
        reply = (
            f"Thank you for sharing that with me, {user_name}. "
            "I am here to support you without judgment. Whether you are navigating everyday stress, curious about sleep routines, feeling tired, or wanting to understand your wellbeing patterns, we can take it one step at a time.\n\n"
            "Feel free to tell me more about what has been on your mind, or explore your latest Wellbeing Check on the dashboard."
        )

    return {'is_crisis': False, 'reply': reply}

@app.route('/ai-companion')
@login_required
def ai_companion():
    user_id = session['user_id']
    conn = get_db_connection()
    messages = conn.execute('''
        SELECT * FROM chat_messages WHERE user_id = ? ORDER BY created_at ASC
    ''', (user_id,)).fetchall()
    conn.close()

    return render_template('ai_companion.html', messages=messages)

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    user_id = session['user_id']
    user_name = session.get('user_name', 'friend').split()[0]
    data = request.get_json() or {}
    message_text = data.get('message', '').strip()

    if not message_text:
        return jsonify({'error': 'Message cannot be empty.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # Save user message
    cursor.execute('''
        INSERT INTO chat_messages (user_id, sender, message)
        VALUES (?, 'user', ?)
    ''', (user_id, message_text))

    # Generate companion reply
    result = generate_companion_reply(message_text, user_name)
    bot_reply = result['reply']
    is_crisis = 1 if result['is_crisis'] else 0

    # Save bot message
    cursor.execute('''
        INSERT INTO chat_messages (user_id, sender, message, is_crisis)
        VALUES (?, 'ai', ?, ?)
    ''', (user_id, bot_reply, is_crisis))

    conn.commit()
    conn.close()

    return jsonify({
        'status': 'success',
        'reply': bot_reply,
        'is_crisis': bool(is_crisis),
        'timestamp': datetime.now().strftime('%I:%M %p')
    })

@app.route('/api/clear-chat', methods=['POST'])
@login_required
def clear_chat():
    user_id = session['user_id']
    user_name = session.get('user_name', 'friend').split()[0]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM chat_messages WHERE user_id = ?', (user_id,))
    # Insert greeting
    welcome_ai = f"Hello {user_name}! Chat history has been reset. How are you feeling today?"
    cursor.execute('''
        INSERT INTO chat_messages (user_id, sender, message)
        VALUES (?, 'ai', ?)
    ''', (user_id, welcome_ai))
    conn.commit()
    conn.close()
    flash('Conversation history has been cleared.', 'info')
    return redirect(url_for('ai_companion'))

# ==========================================
# INSIGHTS & WELLBEING TIMELINE
# ==========================================

@app.route('/insights')
@login_required
def insights():
    user_id = session['user_id']
    conn = get_db_connection()

    # Assessments history
    assessments_history = conn.execute('''
        SELECT * FROM assessments
        WHERE user_id = ?
        ORDER BY created_at ASC
    ''', (user_id,)).fetchall()

    latest_assessment = conn.execute('''
        SELECT * FROM assessments
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 1
    ''', (user_id,)).fetchone()

    baseline = conn.execute('SELECT * FROM baseline WHERE user_id = ?', (user_id,)).fetchone()
    has_baseline = (baseline is not None and baseline['stress_baseline'] is not None)

    # Mood check-ins history
    mood_history = conn.execute('''
        SELECT * FROM mood_checkins
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 25
    ''', (user_id,)).fetchall()

    total_checkins = conn.execute('''
        SELECT COUNT(*) as count FROM mood_checkins WHERE user_id = ?
    ''', (user_id,)).fetchone()['count']

    conn.close()

    # Early awareness analysis
    early_awareness = analyze_early_awareness(latest_assessment, baseline)

    # Build chronological timeline
    timeline = []
    for a in assessments_history:
        timeline.append({
            'type': 'assessment',
            'date': a['created_at'],
            'title': 'Wellbeing Screening Completed',
            'summary': f"Stress: {a['stress']}/5 • Mood: {a['mood']}/5 • Sleep: {a['sleep']}/5 • Energy: {a['energy']}/5 • Anxiety: {a['anxiety']}/5",
            'badge': 'Screening Check',
            'badge_class': 'badge-neutral',
            'icon': '📝'
        })
    for m in mood_history:
        mood_badge_class = 'badge-low' if m['mood_score'] >= 4 else ('badge-moderate' if m['mood_score'] == 3 else 'badge-elevated')
        tags_str = f" • Tags: {m['tags']}" if m['tags'] else ""
        note_str = f" • Note: \"{m['note']}\"" if m['note'] else ""
        timeline.append({
            'type': 'mood',
            'date': m['created_at'],
            'title': f"Daily Check-In: {m['mood_label']} ({m['mood_score']}/5)",
            'summary': f"Energy: {m['energy_score']}/5{tags_str}{note_str}",
            'badge': 'Mood Log',
            'badge_class': mood_badge_class,
            'icon': '🌱'
        })
    timeline.sort(key=lambda x: x['date'], reverse=True)

    # Personalized Risk Prediction Model
    if latest_assessment:
        stress_pts = (latest_assessment['stress'] - 1) / 4 * 25
        anx_pts = (latest_assessment['anxiety'] - 1) / 4 * 25
        burn_pts = (latest_assessment['burnout'] - 1) / 4 * 25
        sleep_pts = (5 - latest_assessment['sleep']) / 4 * 15
        energy_pts = (5 - latest_assessment['energy']) / 4 * 10
        total_risk = round(stress_pts + anx_pts + burn_pts + sleep_pts + energy_pts)

        if total_risk <= 30:
            level = "Low Indication"
            badge = "badge-low"
            outlook = "Stable & Balanced"
            guidance = "Your wellbeing markers indicate healthy balance and restorative capacity. Continue your everyday habits."
        elif total_risk <= 55:
            level = "Moderate Indication"
            badge = "badge-moderate"
            outlook = "Watch Mild Strain"
            guidance = "Subtle tension noted. Prioritize 10-minute micro-breaks, hydration, and regular sleep routines."
        elif total_risk <= 75:
            level = "Elevated Indication"
            badge = "badge-elevated"
            outlook = "Proactive Rest Advised"
            guidance = "Multiple indicators suggest strain. Consider reviewing your workload and discussing your patterns with a counselor."
        else:
            level = "Needs Attention"
            badge = "badge-high"
            outlook = "Structured Support Recommended"
            guidance = "Sustained overload detected. We strongly suggest reaching out to a verified mental health specialist."

        sum_pts = max(1, stress_pts + anx_pts + burn_pts + sleep_pts + energy_pts)
        factors = [
            {'name': 'Stress Load Impact', 'pct': max(5, round((stress_pts / sum_pts) * 100)), 'status': 'Elevated' if stress_pts > 14 else 'Balanced'},
            {'name': 'Anxiety Tension Level', 'pct': max(5, round((anx_pts / sum_pts) * 100)), 'status': 'Elevated' if anx_pts > 14 else 'Balanced'},
            {'name': 'Burnout & Exhaustion', 'pct': max(5, round((burn_pts / sum_pts) * 100)), 'status': 'Elevated' if burn_pts > 14 else 'Balanced'},
            {'name': 'Sleep Deficit Impact', 'pct': max(5, round((sleep_pts / sum_pts) * 100)), 'status': 'Elevated' if sleep_pts > 8 else 'Restorative'},
            {'name': 'Vitality & Energy Reserve', 'pct': max(5, round((energy_pts / sum_pts) * 100)), 'status': 'Watch' if energy_pts > 6 else 'Adequate'}
        ]
        factors.sort(key=lambda f: f['pct'], reverse=True)

        risk_prediction = {
            'composite_score': total_risk,
            'level': level,
            'level_badge': badge,
            'outlook': outlook,
            'confidence': min(96, 68 + (len(assessments_history) * 6)),
            'primary_driver': factors[0]['name'],
            'factors': factors,
            'guidance': guidance
        }
    else:
        risk_prediction = {
            'composite_score': 20,
            'level': 'Not Assessed',
            'level_badge': 'badge-neutral',
            'outlook': 'Awaiting Assessment',
            'confidence': 50,
            'primary_driver': 'Pending baseline check',
            'factors': [
                {'name': 'Stress Load Impact', 'pct': 25, 'status': 'Pending'},
                {'name': 'Anxiety Tension Level', 'pct': 25, 'status': 'Pending'},
                {'name': 'Burnout & Exhaustion', 'pct': 25, 'status': 'Pending'},
                {'name': 'Sleep Deficit Impact', 'pct': 25, 'status': 'Pending'}
            ],
            'guidance': 'Complete your initial Wellbeing Check to generate personalized risk predictions.'
        }

    # Chart datasets
    chart_dates = [a['created_at'][5:10] for a in assessments_history]
    chart_stress = [a['stress'] for a in assessments_history]
    chart_mood = [a['mood'] for a in assessments_history]
    chart_sleep = [a['sleep'] for a in assessments_history]
    chart_anxiety = [a['anxiety'] for a in assessments_history]
    chart_burnout = [a['burnout'] for a in assessments_history]

    return render_template(
        'insights.html',
        timeline=timeline,
        risk_prediction=risk_prediction,
        latest_assessment=latest_assessment,
        baseline=baseline,
        has_baseline=has_baseline,
        early_awareness=early_awareness,
        total_checkins=total_checkins,
        total_assessments=len(assessments_history),
        chart_dates=chart_dates,
        chart_stress=chart_stress,
        chart_mood=chart_mood,
        chart_sleep=chart_sleep,
        chart_anxiety=chart_anxiety,
        chart_burnout=chart_burnout
    )

# ==========================================
# PROFESSIONALS & APPOINTMENTS (DOCTORS / SUPPORT)
# ==========================================

@app.route('/doctors')
@app.route('/professionals')
@login_required
def professionals():
    specialty_filter = request.args.get('specialty', '').strip()
    search_query = request.args.get('search', '').strip()

    conn = get_db_connection()
    query = 'SELECT * FROM professionals WHERE 1=1'
    params = []

    if specialty_filter:
        query += ' AND specialization LIKE ?'
        params.append(f'%{specialty_filter}%')

    if search_query:
        query += ' AND (name LIKE ? OR location LIKE ? OR specialization LIKE ?)'
        params.extend([f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'])

    query += ' ORDER BY rating DESC'
    profs = conn.execute(query, params).fetchall()
    conn.close()

    return render_template('professionals.html', professionals=profs, specialty_filter=specialty_filter, search_query=search_query)

@app.route('/appointments', methods=['GET', 'POST'])
@login_required
def appointments():
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        professional_id = request.form.get('professional_id')
        appointment_date = request.form.get('appointment_date')
        appointment_time = request.form.get('appointment_time')
        notes = request.form.get('notes', '').strip()

        if not professional_id or not appointment_date or not appointment_time:
            flash('Please select a healthcare professional, appointment date, and time slot.', 'error')
            return redirect(url_for('appointments'))

        cursor.execute('''
            INSERT INTO appointments (user_id, professional_id, appointment_date, appointment_time, status, notes)
            VALUES (?, ?, ?, ?, 'Confirmed', ?)
        ''', (user_id, professional_id, appointment_date, appointment_time, notes))
        conn.commit()
        flash('Appointment booked successfully! Your healthcare provider has been notified.', 'success')
        conn.close()
        return redirect(url_for('appointments'))

    # GET: fetch all user appointments and list of professionals for the booking form
    user_appointments = conn.execute('''
        SELECT a.*, p.name as prof_name, p.specialization, p.location, p.experience
        FROM appointments a
        JOIN professionals p ON a.professional_id = p.id
        WHERE a.user_id = ?
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
    ''', (user_id,)).fetchall()

    all_professionals = conn.execute('SELECT id, name, specialization, location FROM professionals ORDER BY name ASC').fetchall()
    selected_prof_id = request.args.get('prof_id')

    conn.close()
    return render_template(
        'appointments.html',
        appointments=user_appointments,
        professionals=all_professionals,
        selected_prof_id=selected_prof_id
    )

@app.route('/appointments/cancel/<int:appointment_id>', methods=['POST'])
@login_required
def cancel_appointment(appointment_id):
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE appointments
        SET status = 'Cancelled'
        WHERE id = ? AND user_id = ?
    ''', (appointment_id, user_id))
    conn.commit()
    conn.close()
    flash('Appointment has been cancelled.', 'info')
    return redirect(url_for('appointments'))

# ==========================================
# PROFILE & CONSENT MANAGEMENT
# ==========================================

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_profile':
            name = request.form.get('name', '').strip()
            age_str = request.form.get('age', '').strip()
            gender = request.form.get('gender', '').strip()
            location = request.form.get('location', '').strip()

            if not name:
                flash('Name cannot be empty.', 'error')
            else:
                age = int(age_str) if age_str and age_str.isdigit() else None
                cursor.execute('''
                    UPDATE users
                    SET name = ?, age = ?, gender = ?, location = ?
                    WHERE id = ?
                ''', (name, age, gender, location, user_id))
                session['user_name'] = name
                conn.commit()
                flash('Profile updated successfully!', 'success')

        elif action == 'update_consent':
            share_summary = 1 if request.form.get('share_summary') else 0
            share_assessment = 1 if request.form.get('share_assessment') else 0

            cursor.execute('''
                INSERT OR REPLACE INTO consent (user_id, share_summary, share_assessment, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, share_summary, share_assessment))
            conn.commit()
            flash('Privacy and sharing consent preferences saved successfully.', 'success')

    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    consent = conn.execute('SELECT * FROM consent WHERE user_id = ?', (user_id,)).fetchone()
    total_assessments = conn.execute('SELECT COUNT(*) as count FROM assessments WHERE user_id = ?', (user_id,)).fetchone()['count']
    baseline = conn.execute('SELECT * FROM baseline WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()

    return render_template(
        'profile.html',
        user=user,
        consent=consent,
        total_assessments=total_assessments,
        baseline=baseline
    )

# ==========================================
# PROFESSIONAL WELLBEING SUMMARY
# ==========================================

@app.route('/summary')
@login_required
def summary():
    user_id = session['user_id']
    conn = get_db_connection()

    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    consent = conn.execute('SELECT * FROM consent WHERE user_id = ?', (user_id,)).fetchone()
    baseline = conn.execute('SELECT * FROM baseline WHERE user_id = ?', (user_id,)).fetchone()
    latest_assessment = conn.execute('''
        SELECT * FROM assessments WHERE user_id = ? ORDER BY created_at DESC LIMIT 1
    ''', (user_id,)).fetchone()
    conn.close()

    early_awareness = analyze_early_awareness(latest_assessment, baseline)

    return render_template(
        'summary.html',
        user=user,
        consent=consent,
        baseline=baseline,
        assessment=latest_assessment,
        early_awareness=early_awareness,
        generated_at=datetime.now().strftime('%B %d, %Y at %I:%M %p')
    )

# Error Handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('login.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return "An internal error occurred. Please refresh or return to the dashboard.", 500

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
