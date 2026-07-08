"""Helper utilities."""

from datetime import datetime
from typing import Optional


class Helpers:
    """Helper utilities."""
    
    @staticmethod
    def format_datetime(dt: datetime, format: str = "%Y-%m-%d %H:%M") -> str:
        """Format datetime to string."""
        return dt.strftime(format)
    
    @staticmethod
    def parse_datetime(dt_str: str, format: str = "%Y-%m-%d %H:%M") -> Optional[datetime]:
        """Parse datetime from string."""
        try:
            return datetime.strptime(dt_str, format)
        except ValueError:
            return None
    
    @staticmethod
    def score_to_grade(score: int) -> str:
        """Convert score to grade."""
        if score >= 85:
            return "A"
        elif score >= 80:
            return "A-"
        elif score >= 75:
            return "B+"
        elif score >= 70:
            return "B"
        elif score >= 65:
            return "B-"
        elif score >= 60:
            return "C+"
        elif score >= 55:
            return "C"
        elif score >= 50:
            return "C-"
        elif score >= 40:
            return "D"
        else:
            return "E"
    
    @staticmethod
    def calculate_late_penalty(late_hours: int, penalty_per_hour: int = 5, max_penalty: int = 50) -> int:
        """Calculate late submission penalty."""
        return min(late_hours * penalty_per_hour, max_penalty)
    
    @staticmethod
    def format_duration(minutes: int) -> str:
        """Format duration in minutes to human readable string."""
        if minutes < 60:
            return f"{minutes} menit"
        hours = minutes // 60
        remaining = minutes % 60
        if remaining == 0:
            return f"{hours} jam"
        return f"{hours} jam {remaining} menit"
    
    @staticmethod
    def truncate(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """Truncate text to max length."""
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix
