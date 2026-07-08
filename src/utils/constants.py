"""Constants for the application."""


class Constants:
    """Application constants."""
    
    # NIM
    NIM_PATTERN = r"^\d{10}$"
    NIM_LENGTH = 10
    
    # Prodi Codes
    PRODI_CODES = {
        "711": "Teknologi Informasi",
        "712": "Sistem Informasi",
        "713": "Teknologi Informasi (Baru)",
    }
    
    # Assignment Types
    ASSIGNMENT_TYPES = [
        "materi_report",
        "tugas_report",
        "jurnal_report",
        "mini_research",
    ]
    
    # Exam Types
    EXAM_TYPES = ["UTS", "UAS"]
    
    # Question Types
    QUESTION_TYPES = ["MCQ", "ESSAY", "CODE"]
    
    # Attendance Status
    ATTENDANCE_STATUS = ["hadir", "izin", "sakit", "alpa"]
    
    # Grade Scale
    GRADE_SCALE = [
        (85, "A"),
        (80, "A-"),
        (75, "B+"),
        (70, "B"),
        (65, "B-"),
        (60, "C+"),
        (55, "C"),
        (50, "C-"),
        (40, "D"),
        (0, "E"),
    ]
    
    # UMSU Grading Weights
    TATAP_MUKA_WEIGHTS = {
        "kehadiran": 0.20,
        "uts": 0.40,
        "uas": 0.40,
    }
    
    TUGAS_TERSTRUKTUR_WEIGHTS = {
        "materi_report": 0.20,
        "tugas_report": 0.20,
        "jurnal_report": 0.30,
        "mini_research": 0.30,
    }
    
    TUGAS_MANDIRI_WEIGHTS = {
        "materi_report": 0.60,
        "tugas_report": 0.40,
    }
    
    COMPONENT_WEIGHTS = {
        "tatap_muka": 0.30,
        "tugas_terstruktur": 0.30,
        "tugas_mandiri": 0.30,
        "attitude": 0.10,
    }
    
    # Gamification
    EXP_BASE = 100
    EXP_LEVEL_MULTIPLIER = 1.5
    MAX_LEVEL = 50
    
    # Attendance
    ATTENDANCE_CODE_LENGTH = 6
    ATTENDANCE_CODE_EXPIRY_MINUTES = 15
    MIN_ATTENDANCE_SESSIONS = 10
    
    # Late Penalty
    LATE_PENALTY_PER_HOUR = 5
    LATE_PENALTY_MAX_PERCENT = 50
    LATE_SUBMISSION_MAX_HOURS = 24
    
    # File Upload
    MAX_FILE_SIZE_MB = 25
    ALLOWED_FILE_TYPES = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "image/jpeg",
        "image/png",
    ]
    
    # Badges
    BADGES = {
        "first_submission": {
            "name": "First Steps",
            "description": "Submit first assignment",
            "icon": "🎯",
            "exp_reward": 50,
        },
        "submissions_10": {
            "name": "Dedicated",
            "description": "Submit 10 assignments",
            "icon": "📚",
            "exp_reward": 100,
        },
        "attendance_10": {
            "name": "Regular",
            "description": "Attend 10 sessions",
            "icon": "✅",
            "exp_reward": 100,
        },
        "attendance_20": {
            "name": "Committed",
            "description": "Attend 20 sessions",
            "icon": "🌟",
            "exp_reward": 200,
        },
        "level_5": {
            "name": "Rising Star",
            "description": "Reach level 5",
            "icon": "⭐",
            "exp_reward": 150,
        },
        "level_10": {
            "name": "Expert",
            "description": "Reach level 10",
            "icon": "🏆",
            "exp_reward": 300,
        },
    }
