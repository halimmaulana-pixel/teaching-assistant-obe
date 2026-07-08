# Discord Teaching Assistant Bot — OBE System Specification
## FIKTI UMSU · Production-Grade Specification

**Version**: 1.0  
**Date**: 2026-07-08  
**Status**: Consolidated from 16+ sub-agent analysis

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Core Features](#2-core-features)
3. [Feature Details](#3-feature-details)
4. [Database Schema](#4-database-schema)
5. [Command Reference](#5-command-reference)
6. [Implementation Plan](#6-implementation-plan)
7. [Tech Stack](#7-tech-stack)

---

## 1. System Overview

### 1.1 Purpose
Discord-based Teaching Assistant Bot for Outcome-Based Education (OBE) at FIKTI UMSU, supporting:
- Student registration & verification
- Attendance tracking
- Assignment management & grading
- Exam administration (UTS/UAS)
- Gamification (EXP, badges, leaderboard)
- OBE analytics (CPMK tracking)

### 1.2 Key Constraints
- **NIM Format**: 10 digits `[YY][PPP][NNNNN]` (e.g., `2471110042`)
- **Prodi Codes**: 711=TI, 712=SI, 713=TI baru
- **Minimum Attendance**: 10 sessions required
- **UMSU Grading**: Tatap Muka (30%), Tugas Terstruktur (30%), Tugas Mandiri (30%), Attitude (10%)

---

## 2. Core Features

### 2.1 Student Registration & Verification
- NIM-based verification (10-digit format)
- Auto-kick after 72 hours if not verified
- Role management (Mahasiswa, Dosen, Admin)
- Welcome DM with verification instructions

### 2.2 Attendance System
- Session-based attendance with codes
- Minimum 10 sessions requirement
- Attendance tracking and alerts
- Manual override for admin

### 2.3 Assignment Management
- 4 types: materi_report, tugas_report, jurnal_report, mini_research
- Group vs individual tasks
- Rubric-based grading
- Late submission penalties

### 2.4 Grade Calculation Engine
- UMSU-specific grading structure
- Tatap Muka (30%): Kehadiran 20%, UTS 40%, UAS 40%
- Tugas Terstruktur (30%): Materi Report 20%, Tugas Report 20%, Jurnal Report 30%, Mini Research 30%
- Tugas Mandiri (30%): Materi Report 60%, Tugas Report 40%
- Attitude (10%)

### 2.5 Exam System (UTS/UAS)
- MCQ, Essay, Code questions
- Timer with auto-submit
- Auto-grading for MCQ

### 2.6 Gamification
- EXP system (100 × level^1.5 formula)
- 30+ badges
- Leaderboard
- Quests and boss battles

### 2.7 OBE Analytics
- CPMK achievement tracking
- Continuous improvement
- Student progress reports

---

## 3. Feature Details

### 3.1 Registration Workflow

```
Mahasiswa join server
    ↓
Bot sends DM with verification instructions
    ↓
Mahasiswa goes to #verifikasi channel
    ↓
Mahasiswa types /verify [NIM]
    ↓
Bot validates NIM format
    ↓
Bot checks if NIM exists in database
    ↓
If valid: Bot assigns role @Mahasiswa
    ↓
If invalid: Bot rejects with error message
    ↓
If not verified within 72 hours: Auto-kick
```

### 3.2 Attendance Workflow

```
Dosen starts session: /mulai-kuliah [kelas] [mata_kuliah]
    ↓
Bot generates attendance code
    ↓
Bot posts embed in #absensi channel
    ↓
Mahasiswa types /absen [kode]
    ↓
Bot validates code and records attendance
    ↓
Bot awards EXP for attendance
    ↓
Dosen closes session: /tutup-kuliah
    ↓
Bot generates attendance summary
```

### 3.3 Assignment Workflow

```
Dosen creates assignment: /dcreate
    ↓
Bot validates input and creates record
    ↓
Bot posts embed in #tugas channel
    ↓
Mahasiswa submits: /submit [assignment_id]
    ↓
Bot validates submission and records
    ↓
Dosen grades: /grade [submission_id]
    ↓
Bot calculates score and grade
    ↓
Dosen publishes: /publish [assignment_id]
    ↓
Bot sends DM to students with grades
```

### 3.4 Grade Calculation

```python
def calculate_final_grade(student_id, course_id):
    # Check minimum attendance
    attendance = get_attendance_summary(student_id, course_id)
    if attendance.total_sessions < 10:
        return {'score': 0, 'grade': 'E', 'reason': 'Kehadiran < 10x'}
    
    # Calculate each component
    tatap_muka = calculate_tatap_muka(student_id, course_id)
    tugas_terstruktur = calculate_tugas_terstruktur(student_id, course_id)
    tugas_mandiri = calculate_tugas_mandiri(student_id, course_id)
    attitude = calculate_attitude(student_id, course_id)
    
    # Weighted average
    final = (
        tatap_muka['score'] * 0.30 +
        tugas_terstruktur['score'] * 0.30 +
        tugas_mandiri['score'] * 0.30 +
        attitude * 0.10
    )
    
    return {
        'score': round(final, 2),
        'grade': score_to_grade(final),
        'components': {
            'tatap_muka': tatap_muka,
            'tugas_terstruktur': tugas_terstruktur,
            'tugas_mandiri': tugas_mandiri,
            'attitude': attitude
        }
    }
```

### 3.5 Gamification System

```python
# EXP Formula
exp_for_level(level):
    return 100 * (level ** 1.5)

# Badge Examples
BADGES = {
    'first_submission': {'name': 'First Steps', 'description': 'Submit first assignment'},
    'perfect_score': {'name': 'Perfect', 'description': 'Get 100% on assignment'},
    'attendance_10': {'name': 'Dedicated', 'description': 'Attend 10 sessions'},
    'streak_7': {'name': 'On Fire', 'description': '7-day activity streak'},
    'group_leader': {'name': 'Leader', 'description': 'Lead a group assignment'},
}
```

---

## 4. Database Schema

### 4.1 Core Tables

```sql
-- Users (Discord members)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    discord_id VARCHAR(20) UNIQUE NOT NULL,
    nim VARCHAR(10) UNIQUE,
    nama_lengkap VARCHAR(100),
    angkatan INTEGER,
    prodi VARCHAR(10),
    kelas VARCHAR(20),
    role VARCHAR(20) DEFAULT 'mahasiswa',
    is_verified BOOLEAN DEFAULT FALSE,
    exp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Courses
CREATE TABLE courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    credits INTEGER,
    prodi VARCHAR(10),
    semester INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Enrollments
CREATE TABLE enrollments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES users(id),
    course_id UUID REFERENCES courses(id),
    class_id UUID,
    semester INTEGER,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(student_id, course_id, semester)
);

-- Assignments
CREATE TABLE assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID REFERENCES courses(id),
    created_by UUID REFERENCES users(id),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    tipe VARCHAR(20) NOT NULL,
    deadline TIMESTAMP NOT NULL,
    bobot INTEGER NOT NULL,
    cpmk_mapping TEXT[],
    rubric_template_id UUID,
    kelompok_mode BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Submissions
CREATE TABLE submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID REFERENCES assignments(id),
    student_id UUID REFERENCES users(id),
    group_id UUID,
    status VARCHAR(20) DEFAULT 'draft',
    is_late BOOLEAN DEFAULT FALSE,
    late_hours DECIMAL(5,2) DEFAULT 0,
    penalty_percent DECIMAL(5,2) DEFAULT 0,
    notes TEXT,
    google_drive_link TEXT,
    submitted_at TIMESTAMP,
    graded_at TIMESTAMP,
    graded_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Grades
CREATE TABLE grades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID REFERENCES submissions(id),
    raw_score DECIMAL(5,2) NOT NULL,
    late_penalty DECIMAL(5,2) DEFAULT 0,
    final_score DECIMAL(5,2) NOT NULL,
    grade CHAR(2) NOT NULL,
    overall_feedback TEXT,
    graded_by UUID REFERENCES users(id),
    graded_at TIMESTAMP DEFAULT NOW(),
    published BOOLEAN DEFAULT FALSE,
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Attendance Sessions
CREATE TABLE attendance_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id UUID,
    course_id UUID REFERENCES courses(id),
    session_date DATE NOT NULL,
    opens_at TIMESTAMP NOT NULL,
    closes_at TIMESTAMP,
    attendance_code VARCHAR(10),
    status VARCHAR(20) DEFAULT 'active',
    started_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Attendance Records
CREATE TABLE attendance_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES attendance_sessions(id),
    student_id UUID REFERENCES users(id),
    status VARCHAR(20) NOT NULL,
    check_in_time TIMESTAMP,
    check_method VARCHAR(20),
    exp_earned INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(session_id, student_id)
);

-- Exams
CREATE TABLE exams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID REFERENCES courses(id),
    created_by UUID REFERENCES users(id),
    type VARCHAR(10) NOT NULL,
    title VARCHAR(200) NOT NULL,
    scheduled_at TIMESTAMP NOT NULL,
    duration INTEGER NOT NULL,
    total_questions INTEGER DEFAULT 0,
    total_points INTEGER DEFAULT 0,
    randomize_questions BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Exam Questions
CREATE TABLE exam_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_id UUID REFERENCES exams(id),
    type VARCHAR(10) NOT NULL,
    question_text TEXT NOT NULL,
    options JSONB,
    correct_option VARCHAR(10),
    code_template TEXT,
    test_cases JSONB,
    cpmk VARCHAR(20),
    points INTEGER DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Exam Submissions
CREATE TABLE exam_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_id UUID REFERENCES exams(id),
    student_id UUID REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'in_progress',
    started_at TIMESTAMP DEFAULT NOW(),
    submitted_at TIMESTAMP,
    total_score DECIMAL(5,2),
    max_score DECIMAL(5,2),
    final_score DECIMAL(5,2),
    grade CHAR(2),
    cpmk_scores JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Badges
CREATE TABLE badges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    icon VARCHAR(10),
    exp_reward INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- User Badges
CREATE TABLE user_badges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    badge_id UUID REFERENCES badges(id),
    earned_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, badge_id)
);

-- Leaderboard
CREATE TABLE leaderboard (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    course_id UUID REFERENCES courses(id),
    period VARCHAR(20) NOT NULL,
    exp_earned INTEGER DEFAULT 0,
    rank INTEGER,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, course_id, period)
);
```

---

## 5. Command Reference

### 5.1 Registration Commands

| Command | Permission | Description |
|---------|------------|-------------|
| `/verify [NIM]` | @everyone | Verify NIM and get role |
| `/approve-registration [id]` | Admin | Approve pending registration |
| `/reject-registration [id] [reason]` | Admin | Reject registration |

### 5.2 Attendance Commands

| Command | Permission | Description |
|---------|------------|-------------|
| `/mulai-kuliah [kelas] [matkul]` | Dosen | Start attendance session |
| `/tutup-kuliah` | Dosen | Close attendance session |
| `/absen [kode]` | Mahasiswa | Submit attendance |
| `/manual-absen [mahasiswa] [status]` | Dosen | Manual attendance |
| `/override-attendance [session] [mahasiswa] [status]` | Admin | Override attendance |

### 5.3 Assignment Commands

| Command | Permission | Description |
|---------|------------|-------------|
| `/dcreate [matkul] [judul] [tipe] [deadline] [bobot] [cpmk]` | Dosen | Create assignment |
| `/submit [assignment_id]` | Mahasiswa | Submit assignment |
| `/grade [submission_id] [scores] [feedback]` | Dosen | Grade submission |
| `/publish [assignment_id] [mode]` | Dosen | Publish grades |
| `/appeal [assignment_id] [reason]` | Mahasiswa | Appeal grade |

### 5.4 Group Commands

| Command | Permission | Description |
|---------|------------|-------------|
| `/group create [assignment_id] [members]` | Mahasiswa | Create group |
| `/group join [group_id]` | Mahasiswa | Join group |
| `/group leave [group_id]` | Mahasiswa | Leave group |
| `/peer start [assignment_id]` | Dosen | Start peer assessment |
| `/peer submit [scores] [feedback]` | Mahasiswa | Submit peer assessment |

### 5.5 Exam Commands

| Command | Permission | Description |
|---------|------------|-------------|
| `/exam-create [matkul] [type] [jadwal] [durasi]` | Dosen | Create exam |
| `/exam-addquestion [exam_id] [type] [soal]` | Dosen | Add question |
| `/exam-start [exam_id]` | Mahasiswa | Start exam |
| `/exam-submit [exam_id]` | Mahasiswa | Submit exam |

### 5.6 Report Commands

| Command | Permission | Description |
|---------|------------|-------------|
| `/grade-report [student_id] [course_id]` | Dosen/TA | Grade report |
| `/leaderboard [course_id] [period]` | All | Leaderboard |
| `/badges` | Mahasiswa | View badges |
| `/status-bot` | Admin | Bot status |

---

## 6. Implementation Plan

### Phase 1: Core Foundation (Week 1-2)
- [ ] Project setup (pyproject.toml, .env.example)
- [ ] Database schema (SQLAlchemy models)
- [ ] Bot skeleton with basic commands
- [ ] Student registration & verification
- [ ] Basic attendance system

### Phase 2: Assignment & Grading (Week 3-4)
- [ ] Assignment CRUD
- [ ] Submission system
- [ ] Rubric system
- [ ] Grade calculation engine
- [ ] CPMK tracking

### Phase 3: Advanced Features (Week 5-6)
- [ ] Group system
- [ ] Peer assessment
- [ ] UTS/UAS workflow
- [ ] Exam timer & auto-submit

### Phase 4: Gamification & Polish (Week 7-8)
- [ ] EXP system
- [ ] Badges
- [ ] Leaderboard
- [ ] Deadline management
- [ ] Reminder system

### Phase 5: Testing & Deploy (Week 9-10)
- [ ] Unit tests
- [ ] Integration tests
- [ ] UAT with dosen
- [ ] Production deploy

---

## 7. Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| Bot Framework | discord.py 2.x |
| Database | PostgreSQL 15+ |
| ORM | SQLAlchemy 2.0 |
| Cache | Redis |
| File Storage | Cloudflare R2 / AWS S3 |
| Job Queue | Celery / ARQ |
| Auth | Discord OAuth2 |
| Hosting | Railway / Render |
| Monitoring | Sentry |
| CI/CD | GitHub Actions |

---

## Appendix A: Edge Cases

### Submission Edge Cases (22 Cases)
- S-01: Deadline <24h (late penalty)
- S-02: Deadline >24h (auto-reject)
- S-03: Double submit (before grading)
- S-04: Double submit (after grading)
- S-05: Invalid file type
- S-06: File size >25MB
- S-07: Invalid Google Drive link
- S-08: Empty file
- S-09: Assignment not found
- S-10: Not enrolled
- S-11: Group submission
- S-12: Not group member
- S-13: Draft save
- S-14: Network error
- S-15: Discord file limit
- S-16: Course ended
- S-17: Non-student submit
- S-18: Concurrent submit
- S-19: Plagiarism flag
- S-20: Resubmit after appeal
- S-21: Submit during exam
- S-22: Malware detected

### Grading Edge Cases (15 Cases)
- G-01: Partial grading
- G-02: Publish incomplete
- G-03: Bulk grading conflict
- G-04: Grade appeal
- G-05: Rubric change
- G-06: Penalty overflow
- G-07: Negative EXP
- G-08: CPMK not mapped
- G-09: Duplicate grade
- G-10: Score outside range
- G-11: Batch missing student
- G-12: Export partial
- G-13: CPMK threshold
- G-14: Recalculate request
- G-15: TA permission

### Exam Edge Cases (15 Cases)
- E-01: Time up during exam
- E-02: Network disconnect
- E-03: Browser crash
- E-04: Invalid answer format
- E-05: Code execution timeout
- E-06: Double submission exam
- E-07: Essay too long
- E-08: Code syntax error
- E-09: Exam not started
- E-10: Different exam time
- E-11: All answers identical
- E-12: IP address change
- E-13: Partial submit
- E-14: No questions
- E-15: Exam duration 0

### Grade Calculation Edge Cases (10 Cases)
- C-01: Attendance <10
- C-02: No assignment submissions
- C-03: No UTS/UAS
- C-04: Weight budget overflow
- C-05: Negative component
- C-06: Division by zero
- C-07: Grade boundary exact
- C-08: GPA calculation
- C-09: Leaderboard update
- C-10: Grade release timing

---

## Appendix B: Database Views

```sql
-- Grade Summary View
CREATE VIEW v_grade_summary AS
SELECT 
    s.student_id,
    s.assignment_id,
    a.course_id,
    a.tipe,
    a.bobot,
    g.final_score,
    g.grade,
    g.published,
    s.is_late,
    s.late_hours,
    s.penalty_percent
FROM submissions s
JOIN assignments a ON s.assignment_id = a.id
LEFT JOIN grades g ON s.id = g.submission_id
WHERE s.status = 'submitted' AND g.published = true;

-- CPMK Achievement View
CREATE VIEW v_cpmk_achievement AS
SELECT 
    gs.student_id,
    a.course_id,
    rc.cpmk,
    AVG(gcs.score) as avg_score,
    COUNT(CASE WHEN gcs.score >= 70 THEN 1 END) as achieved_count,
    COUNT(*) as total_count,
    ROUND(COUNT(CASE WHEN gcs.score >= 70 THEN 1 END)::DECIMAL / COUNT(*) * 100, 2) as achievement_percent
FROM grade_criteria_scores gcs
JOIN grades g ON gcs.grade_id = g.id
JOIN submissions s ON g.submission_id = s.id
JOIN assignments a ON s.assignment_id = a.id
JOIN rubric_criteria rc ON gcs.rubric_criteria_id = rc.id
WHERE rc.cpmk IS NOT NULL
GROUP BY gs.student_id, a.course_id, rc.cpmk;

-- Student Progress View
CREATE VIEW v_student_progress AS
SELECT 
    e.student_id,
    e.course_id,
    e.total_attendance,
    e.total_sessions,
    ROUND(e.total_attendance::DECIMAL / NULLIF(e.total_sessions, 0) * 100, 2) as attendance_percent,
    g.final_score as uts_score,
    g2.final_score as uas_score
FROM enrollments e
LEFT JOIN exam_submissions es ON e.student_id = es.student_id AND es.type = 'UTS'
LEFT JOIN grades g ON es.id = g.submission_id
LEFT JOIN exam_submissions es2 ON e.student_id = es2.student_id AND es2.type = 'UAS'
LEFT JOIN grades g2 ON es2.id = g2.submission_id;
```

---

## Appendix C: Scheduled Tasks

```python
SCHEDULED_TASKS = {
    "check_verification_timeout": {
        "schedule": "every 1 hour",
        "description": "Check for unverified members and send reminders/kick"
    },
    "check_pending_registrations": {
        "schedule": "every 30 minutes",
        "description": "Expire old pending registrations"
    },
    "cleanup_expired_tokens": {
        "schedule": "every 1 hour",
        "description": "Delete expired verification tokens"
    },
    "check_deadline_reminders": {
        "schedule": "every 15 minutes",
        "description": "Send deadline reminders (T-7, T-3, T-1, T-2h)"
    },
    "update_leaderboard": {
        "schedule": "every 1 hour",
        "description": "Update leaderboard rankings"
    },
    "generate_daily_report": {
        "schedule": "every day at 23:00",
        "description": "Generate daily activity report"
    }
}
```

---

**Document End**
