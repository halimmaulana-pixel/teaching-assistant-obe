"""Attendance service for tracking student attendance."""

import random
import string
import logging
from datetime import datetime, timedelta

from ..config import get_settings
from ..database import (
    User,
    Course,
    AttendanceSession,
    AttendanceRecord,
    get_db,
)

logger = logging.getLogger(__name__)


class AttendanceService:
    """Service for handling attendance."""
    
    def __init__(self):
        self.settings = get_settings()
    
    def generate_attendance_code(self) -> str:
        """Generate random attendance code."""
        return ''.join(random.choices(
            string.ascii_uppercase + string.digits,
            k=self.settings.attendance_code_length
        ))
    
    async def start_session(
        self,
        course_id: str,
        class_id: str,
        started_by: str
    ) -> dict:
        """Start attendance session."""
        code = self.generate_attendance_code()
        
        async for db in get_db():
            # Check for active session
            active = await db.query(AttendanceSession).filter(
                AttendanceSession.course_id == course_id,
                AttendanceSession.class_id == class_id,
                AttendanceSession.status == "active"
            ).first()
            
            if active:
                return {
                    "success": False,
                    "error": "Sudah ada sesi aktif untuk kelas ini"
                }
            
            # Create session
            session = AttendanceSession(
                class_id=class_id,
                course_id=course_id,
                session_date=datetime.utcnow(),
                opens_at=datetime.utcnow(),
                attendance_code=code,
                status="active",
                started_by=started_by,
            )
            db.add(session)
            await db.commit()
            
            logger.info(f"Attendance session started: {session.id}")
            
            return {
                "success": True,
                "session": {
                    "id": str(session.id),
                    "code": code,
                    "class_id": class_id,
                    "course_id": course_id,
                    "opens_at": session.opens_at.isoformat(),
                }
            }
    
    async def close_session(self, session_id: str) -> dict:
        """Close attendance session."""
        async for db in get_db():
            session = await db.query(AttendanceSession).filter(
                AttendanceSession.id == session_id
            ).first()
            
            if not session:
                return {
                    "success": False,
                    "error": "Sesi tidak ditemukan"
                }
            
            if session.status != "active":
                return {
                    "success": False,
                    "error": "Sesi sudah ditutup"
                }
            
            session.closes_at = datetime.utcnow()
            session.status = "closed"
            
            # Count attendance
            count = await db.query(AttendanceRecord).filter(
                AttendanceRecord.session_id == session_id
            ).count()
            
            await db.commit()
            
            logger.info(f"Attendance session closed: {session_id}, {count} attendees")
            
            return {
                "success": True,
                "session": {
                    "id": str(session.id),
                    "attendance_count": count,
                    "closes_at": session.closes_at.isoformat(),
                }
            }
    
    async def submit_attendance(
        self,
        code: str,
        student_id: str
    ) -> dict:
        """Submit attendance with code."""
        async for db in get_db():
            # Find session with code
            session = await db.query(AttendanceSession).filter(
                AttendanceSession.attendance_code == code.upper(),
                AttendanceSession.status == "active"
            ).first()
            
            if not session:
                return {
                    "success": False,
                    "error": "Kode absensi tidak valid atau sudah tidak aktif"
                }
            
            # Check if expired
            if datetime.utcnow() > session.opens_at + timedelta(
                minutes=self.settings.attendance_code_expiry_minutes
            ):
                session.status = "expired"
                await db.commit()
                return {
                    "success": False,
                    "error": "Kode absensi sudah kedaluwarsa"
                }
            
            # Check if already attended
            existing = await db.query(AttendanceRecord).filter(
                AttendanceRecord.session_id == session.id,
                AttendanceRecord.student_id == student_id
            ).first()
            
            if existing:
                return {
                    "success": False,
                    "error": "Anda sudah melakukan absensi"
                }
            
            # Record attendance
            record = AttendanceRecord(
                session_id=session.id,
                student_id=student_id,
                status="hadir",
                check_in_time=datetime.utcnow(),
                check_method="code",
                exp_earned=10,
            )
            db.add(record)
            
            # Update user EXP
            user = await db.query(User).filter(
                User.discord_id == student_id
            ).first()
            
            if user:
                user.exp += 10
                # Check level up
                new_level = self.calculate_level(user.exp)
                level_up = new_level > user.level
                if level_up:
                    user.level = new_level
            
            await db.commit()
            
            logger.info(f"Attendance submitted: {student_id} for session {session.id}")
            
            return {
                "success": True,
                "record": {
                    "id": str(record.id),
                    "session_id": str(session.id),
                    "status": record.status,
                    "exp_earned": record.exp_earned,
                    "level_up": level_up if user else False,
                    "new_level": user.level if user and level_up else None,
                }
            }
    
    async def manual_attendance(
        self,
        session_id: str,
        student_id: str,
        status: str,
        recorded_by: str
    ) -> dict:
        """Manual attendance by lecturer."""
        async for db in get_db():
            # Check session
            session = await db.query(AttendanceSession).filter(
                AttendanceSession.id == session_id
            ).first()
            
            if not session:
                return {
                    "success": False,
                    "error": "Sesi tidak ditemukan"
                }
            
            # Check existing record
            existing = await db.query(AttendanceRecord).filter(
                AttendanceRecord.session_id == session_id,
                AttendanceRecord.student_id == student_id
            ).first()
            
            if existing:
                existing.status = status
                existing.check_method = "manual"
            else:
                record = AttendanceRecord(
                    session_id=session_id,
                    student_id=student_id,
                    status=status,
                    check_in_time=datetime.utcnow(),
                    check_method="manual",
                )
                db.add(record)
            
            await db.commit()
            
            logger.info(f"Manual attendance: {student_id} -> {status} by {recorded_by}")
            
            return {
                "success": True,
                "message": f"Absensi {student_id} diubah menjadi {status}"
            }
    
    async def get_attendance_summary(
        self,
        student_id: str,
        course_id: str
    ) -> dict:
        """Get attendance summary for student."""
        async for db in get_db():
            # Get total sessions
            total_sessions = await db.query(AttendanceSession).filter(
                AttendanceSession.course_id == course_id,
                AttendanceSession.status.in_(["active", "closed"])
            ).count()
            
            # Get attended sessions
            attended = await db.query(AttendanceRecord).join(
                AttendanceSession
            ).filter(
                AttendanceSession.course_id == course_id,
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.status == "hadir"
            ).count()
            
            # Calculate percentage
            percentage = (attended / total_sessions * 100) if total_sessions > 0 else 0
            
            return {
                "total_sessions": total_sessions,
                "attended": attended,
                "percentage": round(percentage, 2),
                "is_below_minimum": attended < self.settings.umsu_min_attendance,
            }
    
    def calculate_level(self, exp: int) -> int:
        """Calculate level from EXP."""
        level = 1
        while exp >= self.settings.exp_base * (level ** self.settings.exp_level_multiplier):
            level += 1
            if level >= self.settings.max_level:
                break
        return level - 1
