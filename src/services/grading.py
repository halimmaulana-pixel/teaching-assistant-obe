"""Grading service for handling grades and rubrics."""

import logging
from datetime import datetime

from ..config import get_settings
from ..database import (
    User,
    Assignment,
    Submission,
    Grade,
    GradeCriteriaScore,
    get_db,
)

logger = logging.getLogger(__name__)


class GradingService:
    """Service for handling grading."""
    
    def __init__(self):
        self.settings = get_settings()
    
    def score_to_grade(self, score: int) -> str:
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
    
    async def grade_submission(
        self,
        submission_id: str,
        score: int,
        graded_by: str,
        feedback: str = "",
        criteria_scores: list[dict] = None
    ) -> dict:
        """Grade a submission."""
        async for db in get_db():
            # Get submission
            submission = await db.query(Submission).filter(
                Submission.id == submission_id
            ).first()
            
            if not submission:
                return {
                    "success": False,
                    "error": "Submission tidak ditemukan"
                }
            
            if submission.status == "graded":
                return {
                    "success": False,
                    "error": "Sudah dinilai, gunakan /regrade"
                }
            
            # Calculate final score with penalty
            final_score = score
            if submission.penalty_percent > 0:
                final_score = int(score * (1 - submission.penalty_percent / 100))
            
            # Determine grade
            grade = self.score_to_grade(final_score)
            
            # Create grade record
            grade_record = Grade(
                submission_id=submission_id,
                raw_score=score,
                late_penalty=submission.penalty_percent,
                final_score=final_score,
                grade=grade,
                overall_feedback=feedback,
                graded_by=graded_by,
            )
            db.add(grade_record)
            
            # Update submission
            submission.status = "graded"
            submission.graded_at = datetime.utcnow()
            submission.graded_by = graded_by
            
            # Update assignment count
            assignment = await db.query(Assignment).filter(
                Assignment.id == submission.assignment_id
            ).first()
            if assignment:
                assignment.graded_count += 1
            
            await db.commit()
            
            logger.info(f"Submission graded: {submission_id} -> {grade} ({final_score})")
            
            return {
                "success": True,
                "grade": {
                    "id": str(grade_record.id),
                    "submission_id": submission_id,
                    "raw_score": score,
                    "late_penalty": submission.penalty_percent,
                    "final_score": final_score,
                    "grade": grade,
                    "feedback": feedback,
                }
            }
    
    async def publish_grades(
        self,
        assignment_id: str,
        published_by: str,
        mode: str = "all"
    ) -> dict:
        """Publish grades for an assignment."""
        async for db in get_db():
            # Get unpublished grades
            grades = await db.query(Grade).join(Submission).filter(
                Submission.assignment_id == assignment_id,
                Grade.published == False
            ).all()
            
            if not grades:
                return {
                    "success": False,
                    "error": "Tidak ada nilai untuk dipublish"
                }
            
            # Publish grades
            published_count = 0
            for grade in grades:
                grade.published = True
                grade.published_at = datetime.utcnow()
                published_count += 1
            
            await db.commit()
            
            logger.info(f"Published {published_count} grades for assignment {assignment_id}")
            
            return {
                "success": True,
                "published_count": published_count
            }
    
    async def get_grade(self, submission_id: str) -> dict:
        """Get grade for a submission."""
        async for db in get_db():
            grade = await db.query(Grade).filter(
                Grade.submission_id == submission_id
            ).first()
            
            if not grade:
                return None
            
            return {
                "id": str(grade.id),
                "submission_id": str(grade.submission_id),
                "raw_score": grade.raw_score,
                "late_penalty": grade.late_penalty,
                "final_score": grade.final_score,
                "grade": grade.grade,
                "feedback": grade.overall_feedback,
                "published": grade.published,
                "graded_at": grade.graded_at.isoformat() if grade.graded_at else None,
            }
    
    async def get_grades_by_assignment(self, assignment_id: str) -> list[dict]:
        """Get all grades for an assignment."""
        async for db in get_db():
            grades = await db.query(Grade).join(Submission).filter(
                Submission.assignment_id == assignment_id
            ).all()
            
            return [
                {
                    "id": str(g.id),
                    "submission_id": str(g.submission_id),
                    "raw_score": g.raw_score,
                    "final_score": g.final_score,
                    "grade": g.grade,
                    "published": g.published,
                }
                for g in grades
            ]
    
    async def calculate_final_grade(
        self,
        student_id: str,
        course_id: str
    ) -> dict:
        """Calculate final grade for a student in a course."""
        async for db in get_db():
            # Get attendance
            from .attendance import AttendanceService
            attendance_service = AttendanceService()
            attendance = await attendance_service.get_attendance_summary(
                student_id, course_id
            )
            
            # Check minimum attendance
            if attendance["attended"] < self.settings.umsu_min_attendance:
                return {
                    "success": True,
                    "score": 0,
                    "grade": "E",
                    "reason": "Kehadiran < 10x",
                    "components": {}
                }
            
            # Get submissions and grades
            submissions = await db.query(Submission).filter(
                Submission.student_id == student_id
            ).all()
            
            # Calculate component scores
            tatap_muka_score = 0
            tugas_terstruktur_score = 0
            tugas_mandiri_score = 0
            attitude_score = 100  # Default
            
            for sub in submissions:
                grade = await db.query(Grade).filter(
                    Grade.submission_id == sub.id,
                    Grade.published == True
                ).first()
                
                if grade:
                    assignment = await db.query(Assignment).filter(
                        Assignment.id == sub.assignment_id
                    ).first()
                    
                    if assignment:
                        # Group by tipe
                        if assignment.tipe in ["materi_report", "tugas_report"]:
                            tugas_mandiri_score += grade.final_score
                        elif assignment.tipe in ["jurnal_report", "mini_research"]:
                            tugas_terstruktur_score += grade.final_score
            
            # Calculate weighted average
            # Simplified calculation
            final_score = (
                tatap_muka_score * 0.30 +
                tugas_terstruktur_score * 0.30 +
                tugas_mandiri_score * 0.30 +
                attitude_score * 0.10
            )
            
            grade = self.score_to_grade(int(final_score))
            
            return {
                "success": True,
                "score": round(final_score, 2),
                "grade": grade,
                "components": {
                    "tatap_muka": tatap_muka_score,
                    "tugas_terstruktur": tugas_terstruktur_score,
                    "tugas_mandiri": tugas_mandiri_score,
                    "attitude": attitude_score,
                }
            }
