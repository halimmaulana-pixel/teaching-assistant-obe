"""Assignment commands for managing tasks and homework."""

import logging
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands

from ...config import get_settings
from ...database import (
    User,
    Course,
    Assignment,
    Submission,
    Grade,
    get_db,
)

logger = logging.getLogger(__name__)


class AssignmentCommands(commands.Cog):
    """Assignment commands for managing tasks and homework."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings = get_settings()
    
    @app_commands.command(name="dcreate", description="Buat tugas baru")
    @app_commands.describe(
        matkul="Mata kuliah",
        judul="Judul tugas",
        tipe="Jenis tugas",
        deadline="Deadline (YYYY-MM-DD HH:MM)",
        bobot="Bobot persentase (1-100)",
        cpmk_mapping="CPMK yang diukur (pisahkan dengan koma)"
    )
    @app_commands.checks.has_role("Dosen")
    async def dcreate(
        self,
        interaction: discord.Interaction,
        matkul: str,
        judul: str,
        tipe: str,
        deadline: str,
        bobot: int,
        cpmk_mapping: str
    ):
        """Create new assignment."""
        await interaction.response.defer(ephemeral=True)
        
        # Validate tipe
        valid_tipies = ["materi_report", "tugas_report", "jurnal_report", "mini_research"]
        if tipe.lower() not in valid_tipies:
            await interaction.followup.send(
                f"❌ Tipe tidak valid. Pilihan: {', '.join(valid_tipies)}",
                ephemeral=True
            )
            return
        
        # Validate bobot
        if not 1 <= bobot <= 100:
            await interaction.followup.send(
                "❌ Bobot harus antara 1-100.",
                ephemeral=True
            )
            return
        
        # Parse deadline
        try:
            deadline_dt = datetime.strptime(deadline, "%Y-%m-%d %H:%M")
        except ValueError:
            await interaction.followup.send(
                "❌ Format deadline salah. Gunakan: YYYY-MM-DD HH:MM",
                ephemeral=True
            )
            return
        
        # Check deadline > 24h from now
        if deadline_dt < datetime.utcnow() + timedelta(hours=24):
            await interaction.followup.send(
                "❌ Deadline minimal 24 jam dari sekarang.",
                ephemeral=True
            )
            return
        
        # Parse CPMK
        cpmk_list = [c.strip() for c in cpmk_mapping.split(",")]
        
        async for db in get_db():
            # Get course
            course = await db.query(Course).filter(
                Course.name.ilike(f"%{matkul}%")
            ).first()
            
            if not course:
                await interaction.followup.send(
                    "❌ Mata kuliah tidak ditemukan.",
                    ephemeral=True
                )
                return
            
            # Check duplicate title
            existing = await db.query(Assignment).filter(
                Assignment.course_id == course.id,
                Assignment.title.ilike(f"%{judul}%")
            ).first()
            
            if existing:
                await interaction.followup.send(
                    "❌ Judul tugas sudah ada di mata kuliah ini.",
                    ephemeral=True
                )
                return
            
            # Create assignment
            assignment = Assignment(
                course_id=course.id,
                created_by=str(interaction.user.id),
                title=judul,
                tipe=tipe.lower(),
                deadline=deadline_dt,
                bobot=bobot,
                cpmk_mapping=cpmk_list,
                status="active",
            )
            db.add(assignment)
            await db.commit()
        
        # Create embed
        embed = discord.Embed(
            title=f"[{tipe.replace('_', ' ').title()}] {judul}",
            description=f"Tugas baru telah dibuat untuk **{matkul}**",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Deadline", value=deadline, inline=True)
        embed.add_field(name="Bobot", value=f"{bobot}% dari {tipe.replace('_', ' ').title()}", inline=True)
        embed.add_field(name="CPMK", value=", ".join(cpmk_list), inline=False)
        embed.set_footer(text=f"Dibuat oleh {interaction.user.display_name}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        logger.info(
            f"Assignment created: {judul} for {matkul} by {interaction.user.id}"
        )
    
    @app_commands.command(name="submit", description="Submit tugas")
    @app_commands.describe(
        assignment_id="ID Tugas",
        google_drive_link="Link Google Drive (opsional)",
        notes="Catatan (opsional)"
    )
    async def submit(
        self,
        interaction: discord.Interaction,
        assignment_id: str,
        google_drive_link: str = "",
        notes: str = ""
    ):
        """Submit assignment."""
        await interaction.response.defer(ephemeral=True)
        
        async for db in get_db():
            # Get assignment
            assignment = await db.query(Assignment).filter(
                Assignment.id == assignment_id
            ).first()
            
            if not assignment:
                await interaction.followup.send(
                    "❌ Tugas tidak ditemukan.",
                    ephemeral=True
                )
                return
            
            # Check if assignment is active
            if assignment.status != "active":
                await interaction.followup.send(
                    "❌ Tugas sudah ditutup.",
                    ephemeral=True
                )
                return
            
            # Check deadline
            now = datetime.utcnow()
            if now > assignment.deadline + timedelta(hours=24):
                await interaction.followup.send(
                    "❌ Deadline sudah lewat lebih dari 24 jam.",
                    ephemeral=True
                )
                return
            
            # Check if already submitted and graded
            existing = await db.query(Submission).filter(
                Submission.assignment_id == assignment_id,
                Submission.student_id == str(interaction.user.id)
            ).first()
            
            if existing and existing.status == "graded":
                await interaction.followup.send(
                    "❌ Tugas sudah dinilai, tidak bisa resubmit.",
                    ephemeral=True
                )
                return
            
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
            else:
                submission = Submission(
                    assignment_id=assignment_id,
                    student_id=str(interaction.user.id),
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
        
        # Create response
        embed = discord.Embed(
            title="✅ Tugas Terkirim",
            description=f"Tugas **{assignment.title}** berhasil dikirim.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        if is_late:
            embed.add_field(
                name="⚠️ Terlambat",
                value=f"{late_hours} jam. Penalty: -{penalty_percent}%",
                inline=True
            )
        
        if google_drive_link:
            embed.add_field(name="📎 Link", value=google_drive_link, inline=False)
        
        if notes:
            embed.add_field(name="📝 Catatan", value=notes, inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        logger.info(
            f"Submission for {assignment.title} by {interaction.user.id}"
        )
    
    @app_commands.command(name="grade", description="Nilai tugas")
    @app_commands.describe(
        submission_id="ID Submission",
        score="Skor (0-100)",
        feedback="Feedback untuk mahasiswa"
    )
    @app_commands.checks.has_role("Dosen")
    async def grade(
        self,
        interaction: discord.Interaction,
        submission_id: str,
        score: int,
        feedback: str = ""
    ):
        """Grade submission."""
        await interaction.response.defer(ephemeral=True)
        
        if not 0 <= score <= 100:
            await interaction.followup.send(
                "❌ Skor harus antara 0-100.",
                ephemeral=True
            )
            return
        
        async for db in get_db():
            # Get submission
            submission = await db.query(Submission).filter(
                Submission.id == submission_id
            ).first()
            
            if not submission:
                await interaction.followup.send(
                    "❌ Submission tidak ditemukan.",
                    ephemeral=True
                )
                return
            
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
                graded_by=str(interaction.user.id),
            )
            db.add(grade_record)
            
            # Update submission
            submission.status = "graded"
            submission.graded_at = datetime.utcnow()
            submission.graded_by = str(interaction.user.id)
            
            # Update assignment count
            assignment = await db.query(Assignment).filter(
                Assignment.id == submission.assignment_id
            ).first()
            if assignment:
                assignment.graded_count += 1
            
            await db.commit()
        
        # Create response
        embed = discord.Embed(
            title="✅ Tugas Dinilai",
            description=f"Submission telah dinilai.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Skor", value=f"{score}", inline=True)
        embed.add_field(name="Final", value=f"{final_score}", inline=True)
        embed.add_field(name="Grade", value=grade, inline=True)
        
        if submission.penalty_percent > 0:
            embed.add_field(
                name=" Penalty",
                value=f"-{submission.penalty_percent}%",
                inline=True
            )
        
        if feedback:
            embed.add_field(name="Feedback", value=feedback, inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        logger.info(
            f"Submission {submission_id} graded: {grade} by {interaction.user.id}"
        )
    
    @app_commands.command(name="publish", description="Publish nilai")
    @app_commands.describe(
        assignment_id="ID Tugas",
        mode="Mode publish (all/class/select)"
    )
    @app_commands.checks.has_role("Dosen")
    async def publish(
        self,
        interaction: discord.Interaction,
        assignment_id: str,
        mode: str = "all"
    ):
        """Publish grades."""
        await interaction.response.defer(ephemeral=True)
        
        if mode.lower() not in ["all", "class", "select"]:
            await interaction.followup.send(
                "❌ Mode tidak valid. Pilihan: all, class, select",
                ephemeral=True
            )
            return
        
        async for db in get_db():
            # Get unpublished grades
            grades = await db.query(Grade).join(Submission).filter(
                Submission.assignment_id == assignment_id,
                Grade.published == False
            ).all()
            
            if not grades:
                await interaction.followup.send(
                    "❌ Tidak ada nilai untuk dipublish.",
                    ephemeral=True
                )
                return
            
            # Publish grades
            published_count = 0
            for grade in grades:
                grade.published = True
                grade.published_at = datetime.utcnow()
                published_count += 1
                
                # Send DM to student
                submission = await db.query(Submission).filter(
                    Submission.id == grade.submission_id
                ).first()
                
                if submission:
                    student = await db.query(User).filter(
                        User.discord_id == submission.student_id
                    ).first()
                    
                    if student:
                        try:
                            user = await self.bot.fetch_user(int(student.discord_id))
                            dm_embed = discord.Embed(
                                title="📊 Nilai Telah Dipublish",
                                description="Tugas Anda telah dinilai.",
                                color=discord.Color.blue()
                            )
                            dm_embed.add_field(
                                name="Skor",
                                value=f"{grade.final_score}",
                                inline=True
                            )
                            dm_embed.add_field(
                                name="Grade",
                                value=grade.grade,
                                inline=True
                            )
                            if grade.overall_feedback:
                                dm_embed.add_field(
                                    name="Feedback",
                                    value=grade.overall_feedback,
                                    inline=False
                                )
                            await user.send(embed=dm_embed)
                        except discord.Forbidden:
                            logger.warning(f"Could not DM student {student.discord_id}")
            
            await db.commit()
        
        embed = discord.Embed(
            title="✅ Nilai Dipublish",
            description=f"{published_count} nilai telah dipublish.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        logger.info(
            f"Published {published_count} grades for assignment {assignment_id}"
        )
    
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


async def setup(bot: commands.Bot):
    """Add cog to bot."""
    await bot.add_cog(AssignmentCommands(bot))
