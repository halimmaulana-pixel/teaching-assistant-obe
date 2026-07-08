"""Assignment service for managing tasks and homework."""

import logging
from datetime import datetime, timedelta

from ..config import get_settings
from ..database import (
    User,
    Course,
    Assignment,
    Submission,
    get_db,
)

logger = logging.getLogger(__name__)


class AssignmentService:
    """Service for handling assignments."""
    
    def __init__(self):
        self.settings = get_settings()
    
    async def create_assignment(
        self,
        course_id: str,
        created_by: str,
        title: str,
        tipe: str,
        deadline: datetime,
        bobot: int,
        cpmk_mapping: list[str],
        kelompok_mode: bool = False
    ) -> dict:
        """Create new assignment."""
        async for db in get_db():
            # Check duplicate title
            existing = await db.query(Assignment).filter(
                Assignment.course_id == course_id,
                Assignment.title.ilike(f"%{title}%")
            ).first()
            
            if existing:
                return {
                    "success": False,
                    "error": "Judul tugas sudah ada di mata kuliah ini"
                }
            
            # Validate deadline
            if deadline < datetime.utcnow() + timedelta(hours=24):
                return {
                    "success": False,
                    "error": "Deadline minimal 24 jam dari sekarang"
                }
            
            # Create assignment
            assignment = Assignment(
                course_id=course_id,
                created_by=created_by,
                title=title,
                tipe=tipe,
                deadline=deadline,
                bobot=bobot,
                cpmk_mapping=cpmk_mapping,
                kelompok_mode=kelompok_mode,
                status="active",
            )
            db.add(assignment)
            await db.commit()
            
            logger.info(f"Assignment created: {assignment.id} - {title}")
            
            return {
                "success": True,
                "assignment": {
                    "id": str(assignment.id),
                    "title": assignment.title,
                    "tipe": assignment.tipe,
                    "deadline": assignment.deadline.isoformat(),
                    "bobot": assignment.bobot,
                    "cpmk_mapping": assignment.cpmk_mapping,
                }
            }
    
    async def submit_assignment(
        self,
        assignment_id: str,
        student_id: str,
        notes: str = "",
        google_drive_link: str = ""
    ) -> dict:
        """Submit assignment."""
        async for db in get_db():
            # Get assignment
            assignment = await db.query(Assignment).filter(
                Assignment.id == assignment_id
            ).first()
            
            if not assignment:
                return {
                    "success": False,
                    "error": "Tugas tidak ditemukan"
                }
            
            if assignment.status != "active":
                return {
                    "success": False,
                    "error": "Tugas sudah ditutup"
                }
            
            # Check deadline
            now = datetime.utcnow()
            if now > assignment.deadline + timedelta(hours=24):
                return {
                    "success": False,
                    "error": "Deadline sudah lewat lebih dari 24 jam"
                }
            
            # Check if already submitted and graded
            existing = await db.query(Submission).filter(
                Submission.assignment_id == assignment_id,
                Submission.student_id == student_id
            ).first()
            
            if existing and existing.status == "graded":
                return {
                    "success": False,
                    "error": "Tugas sudah dinilai, tidak bisa resubmit"
                }
            
            # Calculate late penalty
            is_late = now > assignment.deadline
            late_hours = 0
            penalty_percent = 0
            
            if is_late:
                late_hours = int((now - assignment.deadline).total_seconds() // 3600)
                penalty_percent = min(
                    late_hours * self.settings.late_penalty_per_hour,
                    self.settings.late_penalty_max_percent
                )
            
            # Create or update submission
            if existing:
                existing.notes = notes
                existing.google_drive_link = google_drive_link
                existing.is_late = is_late
                existing.late_hours = late_hours
                existing.penalty_percent = penalty_percent
                existing.submitted_at = now
                existing.resubmit_count += 1
                existing.is_resubmit = True
                submission = existing
            else:
                submission = Submission(
                    assignment_id=assignment_id,
                    student_id=student_id,
                    notes=notes,
                    google_drive_link=google_drive_link,
                    is_late=is_late,
                    late_hours=late_hours,
                    penalty_percent=penalty_percent,
                    submitted_at=now,
                    status="submitted",
                )
                db.add(submission)
            
            # Update assignment count
            assignment.submission_count += 1
            await db.commit()
            
            logger.info(f"Submission created: {submission.id} for assignment {assignment_id}")
            
            return {
                "success": True,
                "submission": {
                    "id": str(submission.id),
                    "assignment_id": assignment_id,
                    "is_late": is_late,
                    "late_hours": late_hours,
                    "penalty_percent": penalty_percent,
                    "status": submission.status,
                }
            }
    
    async def get_assignment(self, assignment_id: str) -> dict:
        """Get assignment details."""
        async for db in get_db():
            assignment = await db.query(Assignment).filter(
                Assignment.id == assignment_id
            ).first()
            
            if not assignment:
                return None
            
            return {
                "id": str(assignment.id),
                "course_id": str(assignment.course_id),
                "created_by": assignment.created_by,
                "title": assignment.title,
                "description": assignment.description,
                "tipe": assignment.tipe,
                "deadline": assignment.deadline.isoformat(),
                "bobot": assignment.bobot,
                "cpmk_mapping": assignment.cpmk_mapping,
                "kelompok_mode": assignment.kelompok_mode,
                "status": assignment.status,
                "submission_count": assignment.submission_count,
                "graded_count": assignment.graded_count,
            }
    
    async def get_assignments_by_course(self, course_id: str) -> list[dict]:
        """Get all assignments for a course."""
        async for db in get_db():
            assignments = await db.query(Assignment).filter(
                Assignment.course_id == course_id
            ).order_by(Assignment.deadline.desc()).all()
            
            return [
                {
                    "id": str(a.id),
                    "title": a.title,
                    "tipe": a.tipe,
                    "deadline": a.deadline.isoformat(),
                    "bobot": a.bobot,
                    "status": a.status,
                }
                for a in assignments
            ]
    
    async def close_assignment(self, assignment_id: str) -> dict:
        """Close assignment."""
        async for db in get_db():
            assignment = await db.query(Assignment).filter(
                Assignment.id == assignment_id
            ).first()
            
            if not assignment:
                return {
                    "success": False,
                    "error": "Tugas tidak ditemukan"
                }
            
            assignment.status = "closed"
            await db.commit()
            
            logger.info(f"Assignment closed: {assignment_id}")
            
            return {
                "success": True,
                "message": "Tugas ditutup"
            }
