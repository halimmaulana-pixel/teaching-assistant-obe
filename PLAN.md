# Discord Teaching Assistant Bot — Implementation Plan
## FIKTI UMSU · OBE System

**Version**: 1.0  
**Date**: 2026-07-08  
**Duration**: 10 weeks

---

## Table of Contents

1. [Overview](#1-overview)
2. [Phase 1: Core Foundation (Week 1-2)](#2-phase-1-core-foundation-week-1-2)
3. [Phase 2: Assignment & Grading (Week 3-4)](#3-phase-2-assignment--grading-week-3-4)
4. [Phase 3: Advanced Features (Week 5-6)](#4-phase-3-advanced-features-week-5-6)
5. [Phase 4: Gamification & Polish (Week 7-8)](#5-phase-4-gamification--polish-week-7-8)
6. [Phase 5: Testing & Deploy (Week 9-10)](#6-phase-5-testing--deploy-week-9-10)
7. [Dependencies](#7-dependencies)
8. [Risk Mitigation](#8-risk-mitigation)

---

## 1. Overview

### 1.1 Project Structure

```
teaching-assistant-obe/
├── src/
│   ├── __init__.py
│   ├── main.py                    # Bot entry point
│   ├── config.py                  # Configuration
│   ├── database/
│   │   ├── __init__.py
│   │   ├── engine.py              # SQLAlchemy engine
│   │   ├── models.py             # All models
│   │   └── migrations/           # Alembic migrations
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── client.py             # Discord client
│   │   ├── commands/             # Slash commands
│   │   │   ├── __init__.py
│   │   │   ├── registration.py   # /verify, /approve, /reject
│   │   │   ├── attendance.py     # /absen, /mulai-kuliah, /tutup-kuliah
│   │   │   ├── assignments.py    # /dcreate, /submit, /grade
│   │   │   ├── exams.py          # /exam-create, /exam-start
│   │   │   ├── groups.py         # /group, /peer
│   │   │   └── reports.py        # /grade-report, /leaderboard
│   │   ├── events/               # Event handlers
│   │   │   ├── __init__.py
│   │   │   ├── on_member_join.py
│   │   │   └── on_message.py
│   │   └── views/                # UI Components
│   │       ├── __init__.py
│   │       ├── modals.py         # Modal forms
│   │       └── buttons.py        # Button interactions
│   ├── services/
│   │   ├── __init__.py
│   │   ├── registration.py       # Registration logic
│   │   ├── attendance.py         # Attendance logic
│   │   ├── assignments.py        # Assignment logic
│   │   ├── grading.py            # Grading logic
│   │   ├── exams.py              # Exam logic
│   │   ├── gamification.py       # EXP, badges, leaderboard
│   │   └── obe.py               # OBE analytics
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── validators.py         # Input validation
│   │   ├── helpers.py            # Utility functions
│   │   └── constants.py          # Constants
│   └── tasks/
│       ├── __init__.py
│       ├── scheduler.py          # Task scheduler
│       └── jobs.py               # Scheduled jobs
├── tests/
│   ├── __init__.py
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── data/
│   ├── local.db                  # SQLite for dev
│   └── exports/                  # CSV exports
├── docs/
│   ├── SPEC.md                   # Feature specification
│   ├── PLAN.md                   # This file
│   └── API.md                    # API documentation
├── .env.example                  # Environment variables
├── pyproject.toml                # Project metadata
├── alembic.ini                   # Migration config
└── README.md                     # Project README
```

---

## 2. Phase 1: Core Foundation (Week 1-2)

### 2.1 Week 1: Project Setup & Database

#### Day 1-2: Project Initialization
- [ ] Create `pyproject.toml` with dependencies
- [ ] Create `.env.example` with required variables
- [ ] Set up project structure
- [ ] Configure logging

#### Day 3-4: Database Models
- [ ] Create SQLAlchemy engine and session
- [ ] Implement `User` model
- [ ] Implement `Course` model
- [ ] Implement `Enrollment` model
- [ ] Implement `AttendanceSession` model
- [ ] Implement `AttendanceRecord` model

#### Day 5: Database Setup
- [ ] Create Alembic configuration
- [ ] Generate initial migration
- [ ] Test database connection
- [ ] Create seed data script

### 2.2 Week 2: Bot Skeleton & Registration

#### Day 1-2: Bot Setup
- [ ] Create Discord bot client
- [ ] Set up slash command groups
- [ ] Configure bot permissions
- [ ] Test bot connection

#### Day 3-4: Registration System
- [ ] Implement `/verify` command
- [ ] Implement NIM validation
- [ ] Implement role assignment
- [ ] Implement welcome DM

#### Day 5: Registration Admin
- [ ] Implement `/approve-registration` command
- [ ] Implement `/reject-registration` command
- [ ] Implement registration timeout
- [ ] Test registration flow

### 2.3 Deliverables
- [ ] Working bot with basic commands
- [ ] Database with core models
- [ ] Registration system
- [ ] Basic attendance system

---

## 3. Phase 2: Assignment & Grading (Week 3-4)

### 3.1 Week 3: Assignment System

#### Day 1-2: Assignment Models
- [ ] Implement `Assignment` model
- [ ] Implement `Submission` model
- [ ] Implement `SubmissionFile` model
- [ ] Create database migrations

#### Day 3-4: Assignment Commands
- [ ] Implement `/dcreate` command
- [ ] Implement assignment validation
- [ ] Implement assignment embed
- [ ] Implement deadline tracking

#### Day 5: Submission System
- [ ] Implement `/submit` command
- [ ] Implement file upload
- [ ] Implement Google Drive link
- [ ] Implement submission validation

### 3.2 Week 4: Grading System

#### Day 1-2: Rubric System
- [ ] Implement `RubricTemplate` model
- [ ] Implement `RubricCriteria` model
- [ ] Implement `RubricLevel` model
- [ ] Implement `/rubric` command

#### Day 3-4: Grading Engine
- [ ] Implement `Grade` model
- [ ] Implement `GradeCriteriaScore` model
- [ ] Implement `/grade` command
- [ ] Implement grade calculation

#### Day 5: Grade Publishing
- [ ] Implement `/publish` command
- [ ] Implement grade DM notification
- [ ] Implement grade report
- [ ] Test grading flow

### 3.3 Deliverables
- [ ] Assignment CRUD system
- [ ] Submission system
- [ ] Rubric system
- [ ] Grade calculation engine

---

## 4. Phase 3: Advanced Features (Week 5-6)

### 4.1 Week 5: Group System

#### Day 1-2: Group Models
- [ ] Implement `Group` model
- [ ] Implement `PeerAssessment` model
- [ ] Create database migrations
- [ ] Implement group validation

#### Day 3-4: Group Commands
- [ ] Implement `/group create` command
- [ ] Implement `/group join` command
- [ ] Implement `/group leave` command
- [ ] Implement group submission

#### Day 5: Peer Assessment
- [ ] Implement `/peer start` command
- [ ] Implement `/peer submit` command
- [ ] Implement peer score calculation
- [ ] Implement anti-manipulation

### 4.2 Week 6: Exam System

#### Day 1-2: Exam Models
- [ ] Implement `Exam` model
- [ ] Implement `ExamQuestion` model
- [ ] Implement `ExamSubmission` model
- [ ] Implement `ExamAnswer` model

#### Day 3-4: Exam Commands
- [ ] Implement `/exam-create` command
- [ ] Implement `/exam-addquestion` command
- [ ] Implement `/exam-start` command
- [ ] Implement exam timer

#### Day 5: Exam Grading
- [ ] Implement auto-grading for MCQ
- [ ] Implement essay grading
- [ ] Implement code execution
- [ ] Implement exam report

### 4.3 Deliverables
- [ ] Group management system
- [ ] Peer assessment system
- [ ] Exam system with timer
- [ ] Auto-grading for MCQ

---

## 5. Phase 4: Gamification & Polish (Week 7-8)

### 5.1 Week 7: Gamification

#### Day 1-2: EXP System
- [ ] Implement EXP calculation
- [ ] Implement level system
- [ ] Implement EXP rewards
- [ ] Implement level-up notifications

#### Day 3-4: Badge System
- [ ] Implement `Badge` model
- [ ] Implement `UserBadge` model
- [ ] Implement badge achievements
- [ ] Implement badge display

#### Day 5: Leaderboard
- [ ] Implement `Leaderboard` model
- [ ] Implement leaderboard calculation
- [ ] Implement leaderboard display
- [ ] Implement ranking updates

### 5.2 Week 8: Polish

#### Day 1-2: Deadline Management
- [ ] Implement deadline reminders
- [ ] Implement late penalty
- [ ] Implement auto-close
- [ ] Implement reminder schedule

#### Day 3-4: Report System
- [ ] Implement `/grade-report` command
- [ ] Implement `/leaderboard` command
- [ ] Implement `/badges` command
- [ ] Implement CSV export

#### Day 5: Error Handling
- [ ] Implement error messages
- [ ] Implement rate limiting
- [ ] Implement cooldowns
- [ ] Implement logging

### 5.3 Deliverables
- [ ] EXP and level system
- [ ] Badge system
- [ ] Leaderboard
- [ ] Deadline management
- [ ] Report system

---

## 6. Phase 5: Testing & Deploy (Week 9-10)

### 6.1 Week 9: Testing

#### Day 1-2: Unit Tests
- [ ] Test registration flow
- [ ] Test attendance flow
- [ ] Test assignment flow
- [ ] Test grading flow

#### Day 3-4: Integration Tests
- [ ] Test exam flow
- [ ] Test group flow
- [ ] Test gamification flow
- [ ] Test report generation

#### Day 5: Edge Cases
- [ ] Test edge cases from SPEC.md
- [ ] Test error handling
- [ ] Test rate limiting
- [ ] Test concurrent operations

### 6.2 Week 10: Deploy

#### Day 1-2: Production Setup
- [ ] Set up production database
- [ ] Configure environment variables
- [ ] Set up monitoring (Sentry)
- [ ] Configure CI/CD

#### Day 3-4: UAT
- [ ] Test with dosen
- [ ] Test with mahasiswa
- [ ] Collect feedback
- [ ] Fix issues

#### Day 5: Launch
- [ ] Deploy to production
- [ ] Monitor for issues
- [ ] Document deployment
- [ ] Create user guide

### 6.3 Deliverables
- [ ] Complete test suite
- [ ] Production deployment
- [ ] User documentation
- [ ] Monitoring setup

---

## 7. Dependencies

### 7.1 External Dependencies
- **Discord API**: Rate limits, permissions
- **PostgreSQL**: Database hosting
- **Redis**: Caching and job queue
- **File Storage**: R2/S3 for submissions
- **Sentry**: Error monitoring

### 7.2 Internal Dependencies
- **Phase 1** → **Phase 2**: Database models
- **Phase 2** → **Phase 3**: Grading system
- **Phase 3** → **Phase 4**: Advanced features
- **Phase 4** → **Phase 5**: Complete system

---

## 8. Risk Mitigation

### 8.1 Technical Risks
- **Discord Rate Limits**: Implement rate limiting and retry logic
- **Database Performance**: Use connection pooling and caching
- **File Storage Costs**: Implement file size limits and cleanup
- **Concurrent Operations**: Use database transactions and locks

### 8.2 Timeline Risks
- **Scope Creep**: Stick to MVP features
- **Dependency Delays**: Have fallback options
- **Testing Time**: Start testing early
- **Deployment Issues**: Use staging environment

### 8.3 Mitigation Strategies
- **Daily Standups**: Track progress
- **Weekly Reviews**: Adjust timeline
- **Buffer Time**: 20% buffer for unexpected issues
- **Parallel Work**: Run independent tasks in parallel

---

**Plan End**
