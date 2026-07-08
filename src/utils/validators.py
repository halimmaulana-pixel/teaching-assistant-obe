"""Validation utilities."""

import re
from datetime import datetime


class Validators:
    """Validation utilities."""
    
    @staticmethod
    def validate_nim(nim: str) -> bool:
        """Validate NIM format (10 digits)."""
        return bool(re.match(r"^\d{10}$", nim))
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email))
    
    @staticmethod
    def validate_deadline(deadline: datetime, min_hours: int = 24) -> bool:
        """Validate deadline is at least min_hours from now."""
        return deadline > datetime.utcnow() + __import__("datetime").timedelta(hours=min_hours)
    
    @staticmethod
    def validate_score(score: int) -> bool:
        """Validate score is between 0-100."""
        return 0 <= score <= 100
    
    @staticmethod
    def validate_bobot(bobot: int) -> bool:
        """Validate bobot is between 1-100."""
        return 1 <= bobot <= 100
    
    @staticmethod
    def validate_duration(duration: int) -> bool:
        """Validate exam duration (15-300 minutes)."""
        return 15 <= duration <= 300
    
    @staticmethod
    def validate_attendance_code(code: str) -> bool:
        """Validate attendance code format."""
        return bool(re.match(r"^[A-Z0-9]{6}$", code))
    
    @staticmethod
    def validate_group_size(size: int) -> bool:
        """Validate group size (2-5 members)."""
        return 2 <= size <= 5
