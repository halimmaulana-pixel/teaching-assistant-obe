"""Gamification service for EXP, badges, and leaderboard."""

import logging
from datetime import datetime, timedelta

from ..config import get_settings
from ..database import (
    User,
    Badge,
    UserBadge,
    Leaderboard,
    get_db,
)

logger = logging.getLogger(__name__)


class GamificationService:
    """Service for gamification features."""
    
    def __init__(self):
        self.settings = get_settings()
    
    def calculate_level(self, exp: int) -> int:
        """Calculate level from EXP."""
        level = 1
        while exp >= self.settings.exp_base * (level ** self.settings.exp_level_multiplier):
            level += 1
            if level >= self.settings.max_level:
                break
        return level - 1
    
    def exp_for_next_level(self, current_level: int) -> int:
        """Calculate EXP needed for next level."""
        return int(self.settings.exp_base * ((current_level + 1) ** self.settings.exp_level_multiplier))
    
    async def add_exp(self, user_id: str, amount: int, reason: str = "") -> dict:
        """Add EXP to user."""
        async for db in get_db():
            user = await db.query(User).filter(User.discord_id == user_id).first()
            
            if not user:
                return {
                    "success": False,
                    "error": "Pengguna tidak ditemukan"
                }
            
            old_level = user.level
            user.exp += amount
            new_level = self.calculate_level(user.exp)
            level_up = new_level > old_level
            
            if level_up:
                user.level = new_level
            
            await db.commit()
            
            logger.info(f"Added {amount} EXP to {user_id} for {reason}")
            
            return {
                "success": True,
                "exp_added": amount,
                "total_exp": user.exp,
                "level": user.level,
                "level_up": level_up,
                "exp_to_next": self.exp_for_next_level(user.level) - user.exp,
            }
    
    async def award_badge(self, user_id: str, badge_name: str) -> dict:
        """Award badge to user."""
        async for db in get_db():
            # Get user
            user = await db.query(User).filter(User.discord_id == user_id).first()
            if not user:
                return {
                    "success": False,
                    "error": "Pengguna tidak ditemukan"
                }
            
            # Get badge
            badge = await db.query(Badge).filter(Badge.name == badge_name).first()
            if not badge:
                return {
                    "success": False,
                    "error": "Badge tidak ditemukan"
                }
            
            # Check if already has badge
            existing = await db.query(UserBadge).filter(
                UserBadge.user_id == user_id,
                UserBadge.badge_id == badge.id
            ).first()
            
            if existing:
                return {
                    "success": False,
                    "error": "Sudah memiliki badge ini"
                }
            
            # Award badge
            user_badge = UserBadge(
                user_id=user_id,
                badge_id=badge.id,
            )
            db.add(user_badge)
            
            # Add EXP reward
            user.exp += badge.exp_reward
            new_level = self.calculate_level(user.exp)
            level_up = new_level > user.level
            
            if level_up:
                user.level = new_level
            
            await db.commit()
            
            logger.info(f"Badge awarded: {badge_name} to {user_id}")
            
            return {
                "success": True,
                "badge": {
                    "name": badge.name,
                    "description": badge.description,
                    "icon": badge.icon,
                    "exp_reward": badge.exp_reward,
                },
                "level_up": level_up,
                "new_level": user.level if level_up else None,
            }
    
    async def get_user_badges(self, user_id: str) -> list[dict]:
        """Get all badges for a user."""
        async for db in get_db():
            user_badges = await db.query(UserBadge).filter(
                UserBadge.user_id == user_id
            ).all()
            
            badges = []
            for ub in user_badges:
                badge = await db.query(Badge).filter(Badge.id == ub.badge_id).first()
                if badge:
                    badges.append({
                        "name": badge.name,
                        "description": badge.description,
                        "icon": badge.icon,
                        "earned_at": ub.earned_at.isoformat(),
                    })
            
            return badges
    
    async def update_leaderboard(
        self,
        user_id: str,
        course_id: str = None,
        period: str = "alltime"
    ) -> dict:
        """Update leaderboard."""
        async for db in get_db():
            # Get user
            user = await db.query(User).filter(User.discord_id == user_id).first()
            if not user:
                return {
                    "success": False,
                    "error": "Pengguna tidak ditemukan"
                }
            
            # Get or create leaderboard entry
            entry = await db.query(Leaderboard).filter(
                Leaderboard.user_id == user_id,
                Leaderboard.course_id == course_id,
                Leaderboard.period == period
            ).first()
            
            if entry:
                entry.exp_earned = user.exp
                entry.updated_at = datetime.utcnow()
            else:
                entry = Leaderboard(
                    user_id=user_id,
                    course_id=course_id,
                    period=period,
                    exp_earned=user.exp,
                )
                db.add(entry)
            
            await db.commit()
            
            return {
                "success": True,
                "entry": {
                    "user_id": user_id,
                    "exp_earned": user.exp,
                    "period": period,
                }
            }
    
    async def get_leaderboard(
        self,
        course_id: str = None,
        period: str = "alltime",
        limit: int = 10
    ) -> list[dict]:
        """Get leaderboard."""
        async for db in get_db():
            query = db.query(Leaderboard).filter(
                Leaderboard.period == period
            )
            
            if course_id:
                query = query.filter(Leaderboard.course_id == course_id)
            
            entries = await query.order_by(
                Leaderboard.exp_earned.desc()
            ).limit(limit).all()
            
            leaderboard = []
            for i, entry in enumerate(entries, 1):
                user = await db.query(User).filter(
                    User.discord_id == entry.user_id
                ).first()
                
                if user:
                    leaderboard.append({
                        "rank": i,
                        "user_id": entry.user_id,
                        "nama_lengkap": user.nama_lengkap,
                        "exp": entry.exp_earned,
                        "level": user.level,
                    })
            
            return leaderboard
    
    async def check_and_award_badges(self, user_id: str) -> list[dict]:
        """Check and award eligible badges."""
        awarded = []
        
        async for db in get_db():
            user = await db.query(User).filter(User.discord_id == user_id).first()
            if not user:
                return awarded
            
            # Check various badge conditions
            from ..database import Submission, AttendanceRecord
            
            # Total submissions
            submission_count = await db.query(Submission).filter(
                Submission.student_id == user_id
            ).count()
            
            if submission_count >= 1:
                result = await self.award_badge(user_id, "first_submission")
                if result.get("success"):
                    awarded.append(result["badge"])
            
            if submission_count >= 10:
                result = await self.award_badge(user_id, "submissions_10")
                if result.get("success"):
                    awarded.append(result["badge"])
            
            # Attendance
            attendance_count = await db.query(AttendanceRecord).filter(
                AttendanceRecord.student_id == user_id,
                AttendanceRecord.status == "hadir"
            ).count()
            
            if attendance_count >= 10:
                result = await self.award_badge(user_id, "attendance_10")
                if result.get("success"):
                    awarded.append(result["badge"])
            
            if attendance_count >= 20:
                result = await self.award_badge(user_id, "attendance_20")
                if result.get("success"):
                    awarded.append(result["badge"])
            
            # Level badges
            if user.level >= 5:
                result = await self.award_badge(user_id, "level_5")
                if result.get("success"):
                    awarded.append(result["badge"])
            
            if user.level >= 10:
                result = await self.award_badge(user_id, "level_10")
                if result.get("success"):
                    awarded.append(result["badge"])
            
            return awarded
