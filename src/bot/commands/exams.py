"""Exam commands for UTS/UAS management."""

import logging
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands

from ...config import get_settings
from ...database import (
    User,
    Course,
    Exam,
    ExamQuestion,
    ExamSubmission,
    ExamAnswer,
    get_db,
)

logger = logging.getLogger(__name__)


class ExamCommands(commands.Cog):
    """Exam commands for UTS/UAS management."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings = get_settings()
    
    @app_commands.command(name="exam-create", description="Buat ujian baru")
    @app_commands.describe(
        matkul="Mata kuliah",
        type="Jenis ujian (UTS/UAS)",
        jadwal="Jadwal ujian (YYYY-MM-DD HH:MM)",
        durasi="Durasi dalam menit"
    )
    @app_commands.checks.has_role("Dosen")
    async def exam_create(
        self,
        interaction: discord.Interaction,
        matkul: str,
        type: str,
        jadwal: str,
        durasi: int
    ):
        """Create new exam."""
        await interaction.response.defer(ephemeral=True)
        
        # Validate type
        if type.upper() not in ["UTS", "UAS"]:
            await interaction.followup.send(
                "❌ Jenis ujian tidak valid. Pilihan: UTS, UAS",
                ephemeral=True
            )
            return
        
        # Validate duration
        if not 15 <= durasi <= 300:
            await interaction.followup.send(
                "❌ Durasi harus antara 15-300 menit.",
                ephemeral=True
            )
            return
        
        # Parse schedule
        try:
            scheduled_at = datetime.strptime(jadwal, "%Y-%m-%d %H:%M")
        except ValueError:
            await interaction.followup.send(
                "❌ Format jadwal salah. Gunakan: YYYY-MM-DD HH:MM",
                ephemeral=True
            )
            return
        
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
            
            # Create exam
            exam = Exam(
                course_id=course.id,
                created_by=str(interaction.user.id),
                type=type.upper(),
                title=f"{type.upper()} {matkul}",
                scheduled_at=scheduled_at,
                duration=durasi,
                status="draft",
            )
            db.add(exam)
            await db.commit()
        
        embed = discord.Embed(
            title=f"📝 {type.upper()} Dibuat",
            description=f"Ujian untuk **{matkul}** telah dibuat.",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Jadwal", value=jadwal, inline=True)
        embed.add_field(name="Durasi", value=f"{durasi} menit", inline=True)
        embed.set_footer(text=f"Dibuat oleh {interaction.user.display_name}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        logger.info(f"Exam created: {type.upper()} for {matkul} by {interaction.user.id}")
    
    @app_commands.command(name="exam-addquestion", description="Tambah soal ujian")
    @app_commands.describe(
        exam_id="ID Ujian",
        type="Jenis soal (MCQ/ESSAY/CODE)",
        soal="Teks soal",
        opssi="Opsi jawaban (MCQ, pisahkan dengan koma)",
        jawaban_benar="Jawaban benar (MCQ)",
        cpmk="CPMK yang diukur"
    )
    @app_commands.checks.has_role("Dosen")
    async def exam_addquestion(
        self,
        interaction: discord.Interaction,
        exam_id: str,
        type: str,
        soal: str,
        opssi: str = "",
        jawaban_benar: str = "",
        cpmk: str = ""
    ):
        """Add exam question."""
        await interaction.response.defer(ephemeral=True)
        
        # Validate type
        if type.upper() not in ["MCQ", "ESSAY", "CODE"]:
            await interaction.followup.send(
                "❌ Jenis soal tidak valid. Pilihan: MCQ, ESSAY, CODE",
                ephemeral=True
            )
            return
        
        # Validate MCQ requires options
        if type.upper() == "MCQ" and not opssi:
            await interaction.followup.send(
                "❌ MCQ harus memiliki opsi jawaban.",
                ephemeral=True
            )
            return
        
        async for db in get_db():
            # Get exam
            exam = await db.query(Exam).filter(Exam.id == exam_id).first()
            
            if not exam:
                await interaction.followup.send(
                    "❌ Ujian tidak ditemukan.",
                    ephemeral=True
                )
                return
            
            # Parse options for MCQ
            options = None
            if type.upper() == "MCQ":
                options_list = [o.strip() for o in opssi.split(",")]
                options = {chr(65 + i): o for i, o in enumerate(options_list)}
            
            # Create question
            question = ExamQuestion(
                exam_id=exam_id,
                type=type.upper(),
                question_text=soal,
                options=options,
                correct_option=jawaban_benar.upper() if jawaban_benar else None,
                cpmk=cpmk if cpmk else None,
                points=1,
                sort_order=exam.total_questions,
            )
            db.add(question)
            
            # Update exam count
            exam.total_questions += 1
            exam.total_points += 1
            
            await db.commit()
        
        embed = discord.Embed(
            title="✅ Soal Ditambahkan",
            description=f"Soal {type.upper()} telah ditambahkan.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Total Soal", value=str(exam.total_questions), inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        logger.info(f"Question added to exam {exam_id} by {interaction.user.id}")
    
    @app_commands.command(name="exam-start", description="Mulai ujian")
    @app_commands.describe(exam_id="ID Ujian")
    async def exam_start(self, interaction: discord.Interaction, exam_id: str):
        """Start exam."""
        await interaction.response.defer(ephemeral=True)
        
        async for db in get_db():
            # Get exam
            exam = await db.query(Exam).filter(Exam.id == exam_id).first()
            
            if not exam:
                await interaction.followup.send(
                    "❌ Ujian tidak ditemukan.",
                    ephemeral=True
                )
                return
            
            # Check if exam is scheduled
            now = datetime.utcnow()
            if now < exam.scheduled_at - timedelta(minutes=30):
                await interaction.followup.send(
                    "❌ Ujian belum dimulai. Bisa dimulai 30 menit sebelum jadwal.",
                    ephemeral=True
                )
                return
            
            # Check if already started
            existing = await db.query(ExamSubmission).filter(
                ExamSubmission.exam_id == exam_id,
                ExamSubmission.student_id == str(interaction.user.id)
            ).first()
            
            if existing:
                if existing.status == "in_progress":
                    await interaction.followup.send(
                        "❌ Anda sudah memulai ujian ini.",
                        ephemeral=True
                    )
                    return
                elif existing.status == "submitted":
                    await interaction.followup.send(
                        "❌ Anda sudah menyelesaikan ujian ini.",
                        ephemeral=True
                    )
                    return
            
            # Create exam submission
            submission = ExamSubmission(
                exam_id=exam_id,
                student_id=str(interaction.user.id),
                status="in_progress",
                started_at=now,
            )
            db.add(submission)
            await db.commit()
        
        embed = discord.Embed(
            title="📝 Ujian Dimulai",
            description=f"Ujian **{exam.title}** telah dimulai.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(
            name="Durasi",
            value=f"{exam.duration} menit",
            inline=True
        )
        embed.add_field(
            name="Berkas Selesai",
            value=f"<t:{int((now + timedelta(minutes=exam.duration)).timestamp())}:R>",
            inline=True
        )
        embed.add_field(
            name="Cara Menjawab",
            value="Gunakan `/exam-answer [exam_id] [question_number] [jawaban]`",
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        logger.info(f"Exam {exam_id} started by {interaction.user.id}")
    
    @app_commands.command(name="exam-submit", description="Selesaikan ujian")
    @app_commands.describe(exam_id="ID Ujian")
    async def exam_submit(self, interaction: discord.Interaction, exam_id: str):
        """Submit exam."""
        await interaction.response.defer(ephemeral=True)
        
        async for db in get_db():
            # Get submission
            submission = await db.query(ExamSubmission).filter(
                ExamSubmission.exam_id == exam_id,
                ExamSubmission.student_id == str(interaction.user.id),
                ExamSubmission.status == "in_progress"
            ).first()
            
            if not submission:
                await interaction.followup.send(
                    "❌ Tidak ada ujian aktif untuk disubmit.",
                    ephemeral=True
                )
                return
            
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
        
        embed = discord.Embed(
            title="✅ Ujian Selesai",
            description=f"Ujian **{exam.title}** telah diselesaikan.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Skor", value=f"{final_score}", inline=True)
        embed.add_field(name="Grade", value=grade, inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        logger.info(f"Exam {exam_id} submitted by {interaction.user.id}")
    
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
    await bot.add_cog(ExamCommands(bot))
