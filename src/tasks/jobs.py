"""Scheduled jobs for automated tasks."""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class Jobs:
    """Scheduled jobs for automated tasks."""
    
    def __init__(self, db_session):
        self.db = db_session
    
    async def check_verification_timeout(self):
        """Check for unverified members and send reminders/kick."""
        from ..database import User
        
        # Find users joined more than 24 hours ago and not verified
        threshold = datetime.utcnow() - timedelta(hours=24)
        
        unverified = await self.db.query(User).filter(
            User.is_verified == False,
            User.created_at < threshold
        ).all()
        
        for user in unverified:
            logger.info(f"Unverified user: {user.discord_id} (joined {user.created_at})")
            # TODO: Send reminder DM and potentially kick
    
    async def check_pending_registrations(self):
        """Expire old pending registrations."""
        from ..database import User
        
        threshold = datetime.utcnow() - timedelta(hours=48)
        
        expired = await self.db.query(User).filter(
            User.is_verified == False,
            User.created_at < threshold
        ).all()
        
        for user in expired:
            logger.info(f"Expiring registration: {user.discord_id}")
            # TODO: Delete user and notify
    
    async def check_deadline_reminders(self):
        """Send deadline reminders (T-7, T-3, T-1, T-2h)."""
        from ..database import Assignment
        
        now = datetime.utcnow()
        
        # T-7 days
        t7 = now + timedelta(days=7)
        assignments_t7 = await self.db.query(Assignment).filter(
            Assignment.deadline.between(now, t7),
            Assignment.status == "active"
        ).all()
        
        for assignment in assignments_t7:
            logger.info(f"Deadline reminder T-7: {assignment.title}")
            # TODO: Send reminder
        
        # T-3 days
        t3 = now + timedelta(days=3)
        assignments_t3 = await self.db.query(Assignment).filter(
            Assignment.deadline.between(now, t3),
            Assignment.status == "active"
        ).all()
        
        for assignment in assignments_t3:
            logger.info(f"Deadline reminder T-3: {assignment.title}")
            # TODO: Send reminder
        
        # T-1 day
        t1 = now + timedelta(days=1)
        assignments_t1 = await self.db.query(Assignment).filter(
            Assignment.deadline.between(now, t1),
            Assignment.status == "active"
        ).all()
        
        for assignment in assignments_t1:
            logger.info(f"Deadline reminder T-1: {assignment.title}")
            # TODO: Send reminder
    
    async def update_leaderboard(self):
        """Update leaderboard rankings."""
        from ..database import User, Leaderboard
        
        # Get all users with EXP
        users = await self.db.query(User).filter(
            User.exp > 0
        ).all()
        
        for user in users:
            entry = await self.db.query(Leaderboard).filter(
                Leaderboard.user_id == user.discord_id,
                Leaderboard.period == "alltime"
            ).first()
            
            if entry:
                entry.exp_earned = user.exp
                entry.updated_at = datetime.utcnow()
            else:
                entry = Leaderboard(
                    user_id=user.discord_id,
                    period="alltime",
                    exp_earned=user.exp,
                )
                self.db.add(entry)
        
        await self.db.commit()
        logger.info("Leaderboard updated")
    
    async def cleanup_expired_sessions(self):
        """Cleanup expired attendance sessions."""
        from ..database import AttendanceSession
        
        threshold = datetime.utcnow() - timedelta(hours=2)
        
        expired = await self.db.query(AttendanceSession).filter(
            AttendanceSession.status == "active",
            AttendanceSession.opens_at < threshold
        ).all()
        
        for session in expired:
            session.status = "expired"
            logger.info(f"Session expired: {session.id}")
        
        await self.db.commit()
