"""OBE Analytics service for tracking CPMK and continuous improvement."""

import logging
from datetime import datetime

from ..config import get_settings
from ..database import (
    User,
    Course,
    Assignment,
    Submission,
    Grade,
    GradeCriteriaScore,
    get_db,
)

logger = logging.getLogger(__name__)


class OBEAnalyticsService:
    """Service for OBE analytics."""
    
    def __init__(self):
        self.settings = get_settings()
    
    async def get_cpmk_achievement(
        self,
        student_id: str,
        course_id: str
    ) -> dict:
        """Get CPMK achievement for a student."""
        async for db in get_db():
            # Get all grades for student in course
            submissions = await db.query(Submission).filter(
                Submission.student_id == student_id
            ).all()
            
            cpmk_data = {}
            
            for sub in submissions:
                grade = await db.query(Grade).filter(
                    Grade.submission_id == sub.id,
                    Grade.published == True
                ).first()
                
                if grade:
                    assignment = await db.query(Assignment).filter(
                        Assignment.id == sub.assignment_id
                    ).first()
                    
                    if assignment and assignment.course_id == course_id:
                        for cpmk in assignment.cpmk_mapping:
                            if cpmk not in cpmk_data:
                                cpmk_data[cpmk] = {
                                    "scores": [],
                                    "count": 0,
                                    "achieved": 0,
                                }
                            
                            cpmk_data[cpmk]["scores"].append(grade.final_score)
                            cpmk_data[cpmk]["count"] += 1
                            
                            if grade.final_score >= 70:  # CPMK threshold
                                cpmk_data[cpmk]["achieved"] += 1
            
            # Calculate achievements
            achievements = {}
            for cpmk, data in cpmk_data.items():
                avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
                achievement_pct = (data["achieved"] / data["count"] * 100) if data["count"] > 0 else 0
                
                achievements[cpmk] = {
                    "average_score": round(avg_score, 2),
                    "total_assessments": data["count"],
                    "achieved_count": data["achieved"],
                    "achievement_percentage": round(achievement_pct, 2),
                }
            
            return {
                "student_id": student_id,
                "course_id": course_id,
                "achievements": achievements,
            }
    
    async def get_course_cpmk_summary(self, course_id: str) -> dict:
        """Get CPMK summary for entire course."""
        async for db in get_db():
            # Get all assignments for course
            assignments = await db.query(Assignment).filter(
                Assignment.course_id == course_id
            ).all()
            
            cpmk_summary = {}
            
            for assignment in assignments:
                for cpmk in assignment.cpmk_mapping:
                    if cpmk not in cpmk_summary:
                        cpmk_summary[cpmk] = {
                            "total_students": 0,
                            "achieved_students": 0,
                            "average_score": 0,
                            "scores": [],
                        }
                    
                    # Get all submissions for this assignment
                    submissions = await db.query(Submission).filter(
                        Submission.assignment_id == assignment.id
                    ).all()
                    
                    for sub in submissions:
                        grade = await db.query(Grade).filter(
                            Grade.submission_id == sub.id,
                            Grade.published == True
                        ).first()
                        
                        if grade:
                            cpmk_summary[cpmk]["scores"].append(grade.final_score)
                            cpmk_summary[cpmk]["total_students"] += 1
                            
                            if grade.final_score >= 70:
                                cpmk_summary[cpmk]["achieved_students"] += 1
            
            # Calculate averages
            for cpmk, data in cpmk_summary.items():
                if data["scores"]:
                    data["average_score"] = round(
                        sum(data["scores"]) / len(data["scores"]), 2
                    )
                data["achievement_percentage"] = round(
                    (data["achieved_students"] / data["total_students"] * 100)
                    if data["total_students"] > 0 else 0, 2
                )
                del data["scores"]  # Remove raw scores
            
            return {
                "course_id": course_id,
                "cpmk_summary": cpmk_summary,
            }
    
    async def get_student_progress(
        self,
        student_id: str,
        course_id: str
    ) -> dict:
        """Get student progress in course."""
        async for db in get_db():
            # Get attendance
            from .attendance import AttendanceService
            attendance_service = AttendanceService()
            attendance = await attendance_service.get_attendance_summary(
                student_id, course_id
            )
            
            # Get submissions
            submissions = await db.query(Submission).filter(
                Submission.student_id == student_id
            ).all()
            
            total_submissions = len(submissions)
            graded_submissions = 0
            average_score = 0
            
            scores = []
            for sub in submissions:
                grade = await db.query(Grade).filter(
                    Grade.submission_id == sub.id,
                    Grade.published == True
                ).first()
                
                if grade:
                    graded_submissions += 1
                    scores.append(grade.final_score)
            
            if scores:
                average_score = sum(scores) / len(scores)
            
            return {
                "student_id": student_id,
                "course_id": course_id,
                "attendance": attendance,
                "submissions": {
                    "total": total_submissions,
                    "graded": graded_submissions,
                    "average_score": round(average_score, 2),
                },
            }
    
    async def get_course_analytics(self, course_id: str) -> dict:
        """Get course analytics for continuous improvement."""
        async for db in get_db():
            # Get course
            course = await db.query(Course).filter(Course.id == course_id).first()
            if not course:
                return None
            
            # Get enrollments
            from ..database import Enrollment
            enrollment_count = await db.query(Enrollment).filter(
                Enrollment.course_id == course_id,
                Enrollment.status == "active"
            ).count()
            
            # Get assignments
            assignment_count = await db.query(Assignment).filter(
                Assignment.course_id == course_id
            ).count()
            
            # Get submissions
            submission_count = await db.query(Submission).join(Assignment).filter(
                Assignment.course_id == course_id
            ).count()
            
            # Get grades
            from ..database import Grade
            grade_count = await db.query(Grade).join(Submission).join(Assignment).filter(
                Assignment.course_id == course_id,
                Grade.published == True
            ).count()
            
            # Calculate submission rate
            submission_rate = (submission_count / (enrollment_count * assignment_count) * 100) if (enrollment_count * assignment_count) > 0 else 0
            
            return {
                "course_id": course_id,
                "course_name": course.name,
                "enrollment_count": enrollment_count,
                "assignment_count": assignment_count,
                "submission_count": submission_count,
                "grade_count": grade_count,
                "submission_rate": round(submission_rate, 2),
            }
    
    async def get_attendance_analytics(
        self,
        course_id: str
    ) -> dict:
        """Get attendance analytics for course."""
        async for db in get_db():
            from ..database import AttendanceSession, AttendanceRecord
            
            # Get total sessions
            total_sessions = await db.query(AttendanceSession).filter(
                AttendanceSession.course_id == course_id
            ).count()
            
            # Get average attendance rate
            sessions = await db.query(AttendanceSession).filter(
                AttendanceSession.course_id == course_id
            ).all()
            
            attendance_rates = []
            for session in sessions:
                attendance_count = await db.query(AttendanceRecord).filter(
                    AttendanceRecord.session_id == session.id,
                    AttendanceRecord.status == "hadir"
                ).count()
                
                # Get enrolled students
                from ..database import Enrollment
                enrolled = await db.query(Enrollment).filter(
                    Enrollment.course_id == course_id,
                    Enrollment.status == "active"
                ).count()
                
                if enrolled > 0:
                    rate = (attendance_count / enrolled * 100)
                    attendance_rates.append(rate)
            
            avg_attendance_rate = sum(attendance_rates) / len(attendance_rates) if attendance_rates else 0
            
            return {
                "course_id": course_id,
                "total_sessions": total_sessions,
                "average_attendance_rate": round(avg_attendance_rate, 2),
            }
