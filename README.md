# MINDMED

> **Talk. Understand. Detect. Connect.**

MINDMED is an AI-powered personalized wellbeing and early-awareness platform designed to establish a unique personal baseline, detect meaningful shifts across stress, mood, sleep, and energy, deliver early pattern awareness before burnout deepens, and connect users safely with verified healthcare specialists.

---

## ⚕️ Important Medical Disclaimer

> **MINDMED provides wellbeing screening and early-awareness support. It does not provide medical diagnosis and does not replace qualified healthcare professionals.**
> 
> The platform strictly uses non-diagnostic language:
> * *"Your responses indicate..."*
> * *"This screening suggests..."*
> * *"A pattern worth monitoring..."*
> * *"Consider speaking with a qualified professional..."*

---

## 🌟 Core Pillars

1. **Talk (AI Wellbeing Companion):** Private, supportive conversational companion equipped with evidence-based grounding techniques, sleep hygiene tips, and immediate crisis safety detection with national helplines.
2. **Understand (Wellbeing Assessment):** Multi-dimensional screening covering emotional state (mood, stress, sleep, energy), anxiety (GAD-2 screening style), depression-risk (PHQ-2 screening style), burnout indicators, and somatic vitality.
3. **Detect (Personal Baseline & Early Awareness):** Dynamically computes user baseline vs current responses, detects deltas, and triggers proactive Early Awareness alerts when multiple indicators shift unfavorably.
4. **Connect (Healthcare Professionals & Appointments):** Directory of verified psychologists, psychiatrists, and counselors with instant appointment booking and patient-controlled consent sharing.

---

## 🚀 Quick Start Guide

### Prerequisites
* Python 3.9+ (Python 3.13 tested)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Application
```bash
python app.py
```

### 3. Open in Browser
Visit **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

The SQLite database (`mindmed.db`) initializes automatically with pre-seeded demo healthcare specialists and a ready-to-test user account.

---

## 🧪 Demo Credentials for Judges

| Role | Email | Password | Baseline State |
| :--- | :--- | :--- | :--- |
| **Demo User** | `demo@mindmed.health` | `mindmed123` | Baseline Calibrated + Elevated Stress Assessment for Early Awareness showcase |
| **New User** | Any new registration | Any 6+ char password | Fresh empty baseline flow |

> **Tip:** The login page includes a one-click **"Click to Auto-Fill Demo User"** button for quick evaluation!

---

## 🔄 End-to-End User Flow

1. **Sign In / Sign Up:**
   * Open `http://127.0.0.1:5000/login`
   * Register a new user with name, email, password, age, gender, and location.
   * Or click the demo filler button to log in as Aswathy.
2. **Dashboard Overview:**
   * Review the welcome banner and core wellbeing cards (Stress, Mood, Sleep, Energy).
   * Notice the **Personal Baseline** progress and **Current vs Baseline comparison matrix**.
   * Observe the **MindMED Early Awareness** banner alerting to unfavorable shifts.
3. **Take a Wellbeing Check:**
   * Navigate to `Wellbeing Check`.
   * Complete the 5 screening dimensions.
   * Submit to generate personalized non-diagnostic scores, suggestions, and updated baseline deltas.
4. **AI Wellbeing Companion:**
   * Navigate to `AI Companion`.
   * Click prompt chips like *"I'm feeling stressed"*, *"I can't sleep"*, or type custom reflections.
   * Test crisis safety handling by asking emergency-related questions to see immediate crisis helpline cards.
5. **Verified Specialists & Appointments:**
   * Navigate to `Professionals` to view verified doctors, ratings, specializations, and locations.
   * Click `Book Consultation` to schedule an appointment.
   * View and manage scheduled appointments on the `Appointments` page.
6. **Privacy Consent Management:**
   * Navigate to `Profile & Consent` to toggle whether your wellbeing summary or assessment details may be shared with healthcare providers.
7. **Clinical Wellbeing Summary:**
   * Open `Clinical Summary` to view a clean, printable medical report with patient demographics, baseline deltas, risk screening indications, and user consent authorization.
8. **Secure Logout:**
   * Click `Logout` to terminate the session. Accessing `/dashboard` directly redirects back to login.

---

## 🏗️ Project Architecture

```
mindmed/
│
├── app.py                     # Flask application routes, session management, rule engine
├── database.py                # SQLite schema, connection helpers, and seed data
├── requirements.txt           # Minimal dependencies (Flask, Werkzeug)
├── README.md                  # Documentation and quickstart
├── mindmed.db                 # SQLite database (auto-generated)
│
├── templates/
│   ├── base.html              # Layout, navbar, disclaimer banner, flash notifications
│   ├── login.html             # Login view with brand hero and demo credential filler
│   ├── signup.html            # Registration with full validation
│   ├── dashboard.html         # Baseline tracking, delta comparison, early awareness
│   ├── assessment.html        # 5-section interactive screening questionnaire
│   ├── results.html           # Screening results report with actionable next steps
│   ├── ai_companion.html      # AI chat UI with crisis alert handling
│   ├── professionals.html     # Directory of mental healthcare specialists
│   ├── appointments.html      # Appointment booking and management
│   ├── profile.html           # User profile and consent controls
│   └── summary.html           # Printable provider-ready clinical summary
│
└── static/
    ├── css/
    │   ├── style.css          # Color palette, base components, badges, responsive grid
    │   ├── auth.css           # Auth split-screen styling
    │   └── dashboard.css      # Dashboard, cards, chat, and printable summary styles
    │
    └── js/
        ├── main.js            # Mobile navigation, flash alerts, demo account helper
        ├── assessment.js       # Live progress tracking and validation
        └── chat.js            # Async chat, prompt chips, typing feedback, crisis alerts
```

---

## 🔒 Security & Privacy Features

* **Password Hashing:** Passwords hashed with `Werkzeug` PBKDF2/SHA256.
* **Session Protection:** Secure Flask cookie sessions; all sensitive routes protected via `@login_required`.
* **SQL Injection Prevention:** 100% parameterized SQLite queries.
* **Data Isolation:** Every query strictly scopes data by `session['user_id']`.
* **Consent Control:** Explicit user-managed flags for summary and assessment sharing.
