"""Exam service for UTS/UAS management."""

import logging
from datetime import datetime, timedelta

from ..config import get_settings
from ..database import (
    Course,
    Exam,
    ExamQuestion,
    ExamSubmission,
    ExamAnswer,
    get_db,
)

logger = logging.getLogger(__name__)


class ExamService:
    """Service for handling exams."""
    
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
    
    async def create_exam(
        self,
        course_id: str,
        created_by: str,
        exam_type: str,
        title: str,
        scheduled_at: datetime,
        duration: int
    ) -> dict:
        """Create new exam."""
        async for db in get_db():
            # Validate duration
            if not 15 <= duration <= 300:
                return {
                    "success": False,
                    "error": "Durasi harus antara 15-300 menit"
                }
            
            # Create exam
            exam = Exam(
                course_id=course_id,
                created_by=created_by,
                type=exam_type,
                title=title,
                scheduled_at=scheduled_at,
                duration=duration,
                status="draft",
            )
            db.add(exam)
            await db.commit()
            
            logger.info(f"Exam created: {exam.id} - {title}")
            
            return {
                "success": True,
                "exam": {
                    "id": str(exam.id),
                    "title": exam.title,
                    "type": exam.type,
                    "scheduled_at": exam.scheduled_at.isoformat(),
                    "duration": exam.duration,
                }
            }
    
    async def add_question(
        self,
        exam_id: str,
        question_type: str,
        question_text: str,
        options: dict = None,
        correct_option: str = None,
        cpmk: str = "",
        points: int = 1
    ) -> dict:
        """Add question to exam."""
        async for db in get_db():
            # Get exam
            exam = await db.query(Exam).filter(Exam.id == exam_id).first()
            
            if not exam:
                return {
                    "success": False,
                    "error": "Ujian tidak ditemukan"
                }
            
            # Create question
            question = ExamQuestion(
                exam_id=exam_id,
                type=question_type,
                question_text=question_text,
                options=options,
                correct_option=correct_option,
                cpmk=cpmk if cpmk else None,
                points=points,
                sort_order=exam.total_questions,
            )
            db.add(question)
            
            # Update exam count
            exam.total_questions += 1
            exam.total_points += points
            
            await db.commit()
            
            logger.info(f"Question added to exam {exam_id}")
            
            return {
                "success": True,
                "question": {
                    "id": str(question.id),
                    "type": question.type,
                    "points": question.points,
                },
                "total_questions": exam.total_questions,
            }
    
    async def start_exam(
        self,
        exam_id: str,
        student_id: str
    ) -> dict:
        """Start exam for student."""
        async for db in get_db():
            # Get exam
            exam = await db.query(Exam).filter(Exam.id == exam_id).first()
            
            if not exam:
                return {
                    "success": False,
                    "error": "Ujian tidak ditemukan"
                }
            
            # Check if exam is scheduled
            now = datetime.utcnow()
            if now < exam.scheduled_at - timedelta(minutes=30):
                return {
                    "success": False,
                    "error": "Ujian belum dimulai. Bisa dimulai 30 menit sebelum jadwal."
                }
            
            # Check if already started
            existing = await db.query(ExamSubmission).filter(
                ExamSubmission.exam_id == exam_id,
                ExamSubmission.student_id == student_id
            ).first()
            
            if existing:
                if existing.status == "in_progress":
                    return {
                        "success": False,
                        "error": "Anda sudah memulai ujian ini"
                    }
                elif existing.status == "submitted":
                    return {
                        "success": False,
                        "error": "Anda sudah menyelesaikan ujian ini"
                    }
            
            # Create exam submission
            submission = ExamSubmission(
                exam_id=exam_id,
                student_id=student_id,
                status="in_progress",
                started_at=now,
            )
            db.add(submission)
            await db.commit()
            
            logger.info(f"Exam started: {exam_id} by {student_id}")
            
            return {
                "success": True,
                "submission": {
                    "id": str(submission.id),
                    "exam_id": exam_id,
                    "started_at": submission.started_at.isoformat(),
                    "duration": exam.duration,
                    "end_time": (now + timedelta(minutes=exam.duration)).isoformat(),
                }
            }
    
    async def submit_exam(
        self,
        exam_id: str,
        student_id: str
    ) -> dict:
        """Submit exam."""
        async for db in get_db():
            # Get submission
            submission = await db.query(ExamSubmission).filter(
                ExamSubmission.exam_id == exam_id,
                ExamSubmission.student_id == student_id,
                ExamSubmission.status == "in_progress"
            ).first()
            
            if not submission:
                return {
                    "success": False,
                    "error": "Tidak ada ujian aktif untuk disubmit"
                }
            
            # Get exam
            exam = await db.query(Exam).filter(Exam.id == exam_id).first()
            
            # Calculate score
            answers = await db.query(ExamAnswer).filter(
                ExamAnswer.exam_submission_id == submission.id
            ).all()
            
            total_score = 0
            max_score = exam.total_points
            
            for answer in answers:
                if answer.score:
                    total_score += answer.score
            
            # Calculate final score
            final_score = int((total_score / max_score) * 100) if max_score > 0 else 0
            
            # Determine grade
            grade = self.score_to_grade(final_score)
            
            # Update submission
            submission.status = "submitted"
            submission.submitted_at = datetime.utcnow()
            submission.total_score = total_score
            submission.max_score = max_score
            submission.final_score = final_score
            submission.grade = grade
            
            await db.commit()
            
            logger.info(f"Exam submitted: {exam_id} by {student_id}")
            
            return {
                "success": True,
                "result": {
                    "submission_id": str(submission.id),
                    "total_score": total_score,
                    "max_score": max_score,
                    "final_score": final_score,
                    "grade": grade,
                }
            }
    
    async def get_exam(self, exam_id: str) -> dict:
        """Get exam details."""
        async for db in get_db():
            exam = await db.query(Exam).filter(Exam.id == exam_id).first()
            
            if not exam:
                return None
            
            return {
                "id": str(exam.id),
                "course_id": str(exam.course_id),
                "title": exam.title,
                "type": exam.type,
                "scheduled_at": exam.scheduled_at.isoformat(),
                "duration": exam.duration,
                "total_questions": exam.total_questions,
                "total_points": exam.total_points,
                "status": exam.status,
            }
    
    async def get_exams_by_course(self, course_id: str) -> list[dict]:
        """Get all exams for a course."""
        async for db in get_db():
            exams = await db.query(Exam).filter(
                Exam.course_id == course_id
            ).order_by(Exam.scheduled_at.desc()).all()
            
            return [
                {
                    "id": str(e.id),
                    "title": e.title,
                    "type": e.type,
                    "scheduled_at": e.scheduled_at.isoformat(),
                    "duration": e.duration,
                    "status": e.status,
                }
                for e in exams
            ]
