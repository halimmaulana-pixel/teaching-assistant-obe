"""Report commands for grade reports and leaderboards."""

import logging
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from ...config import get_settings
from ...database import (
    User,
    Course,
    Enrollment,
    Submission,
    Grade,
    AttendanceRecord,
    get_db,
)

logger = logging.getLogger(__name__)


class ReportCommands(commands.Cog):
    """Report commands for grade reports and leaderboards."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings = get_settings()
    
    @app_commands.command(name="grade-report", description="Laporan nilai mahasiswa")
    @app_commands.describe(
        student_id="ID Mahasiswa (opsional, default: diri sendiri)",
        course_id="ID Mata Kuliah"
    )
    async def grade_report(
        self,
        interaction: discord.Interaction,
        course_id: str,
        student_id: str = ""
    ):
        """View grade report."""
        await interaction.response.defer(ephemeral=True)
        
        # Use own ID if not specified
        if not student_id:
            student_id = str(interaction.user.id)
        
        async for db in get_db():
            # Get student
            student = await db.query(User).filter(
                User.discord_id == student_id
            ).first()
            
            if not student:
                await interaction.followup.send(
                    "❌ Mahasiswa tidak ditemukan.",
                    ephemeral=True
                )
                return
            
            # Get enrollments
            enrollments = await db.query(Enrollment).filter(
                Enrollment.student_id == student_id,
                Enrollment.course_id == course_id
            ).all()
            
            if not enrollments:
                await interaction.followup.send(
                    "❌ Mahasiswa tidak terdaftar di mata kuliah ini.",
                    ephemeral=True
                )
                return
            
            # Get submissions
            submissions = await db.query(Submission).filter(
                Submission.student_id == student_id
            ).all()
            
            # Get grades
            grades = []
            for sub in submissions:
                grade = await db.query(Grade).filter(
                    Grade.submission_id == sub.id,
                    Grade.published == True
                ).first()
                if grade:
                    grades.append(grade)
            
            # Calculate average
            if grades:
                avg_score = sum(g.final_score for g in grades) / len(grades)
            else:
                avg_score = 0
        
        # Create embed
        embed = discord.Embed(
            title="📊 Laporan Nilai",
            description=f"Nilai untuk **{student.nama_lengkap or student.discord_id}**",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        if grades:
            # Add grade details
            grade_list = []
            for grade in grades[:10]:  # Limit to 10
                submission = await db.query(Submission).filter(
                    Submission.id == grade.submission_id
                ).first()
                if submission:
                    assignment = await db.query(Assignment).filter(
                        Assignment.id == submission.assignment_id
                    ).first()
                    if assignment:
                        grade_list.append(
                            f"• {assignment.title}: {grade.final_score} ({grade.grade})"
                        )
            
            embed.add_field(
                name="Nilai Tugas",
                value="\n".join(grade_list) if grade_list else "Belum ada nilai",
                inline=False
            )
            
            embed.add_field(
                name="Rata-rata",
                value=f"{avg_score:.2f}",
                inline=True
            )
            
            # Determine final grade
            final_grade = self.score_to_grade(int(avg_score))
            embed.add_field(
                name="Grade Akhir",
                value=final_grade,
                inline=True
            )
        else:
            embed.add_field(
                name="Status",
                value="Belum ada nilai yang dipublish",
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="leaderboard", description="Lihat peringkat")
    @app_commands.describe(
        course_id="ID Mata Kuliah (opsional)",
        period="Periode (weekly/monthly/alltime)"
    )
    async def leaderboard(
        self,
        interaction: discord.Interaction,
        period: str = "alltime",
        course_id: str = ""
    ):
        """View leaderboard."""
        await interaction.response.defer(ephemeral=True)
        
        if period not in ["weekly", "monthly", "alltime"]:
            await interaction.followup.send(
                "❌ Periode tidak valid. Pilihan: weekly, monthly, alltime",
                ephemeral=True
            )
            return
        
        async for db in get_db():
            # Get all users with EXP
            users = await db.query(User).filter(
                User.exp > 0
            ).order_by(User.exp.desc()).limit(10).all()
        
        if not users:
            await interaction.followup.send(
                "❌ Belum ada data peringkat.",
                ephemeral=True
            )
            return
        
        # Create embed
        embed = discord.Embed(
            title="🏆 Leaderboard",
            description=f"Peringkat {period}",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )
        
        leaderboard_list = []
        for i, user in enumerate(users, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
            leaderboard_list.append(
                f"{medal} **{user.nama_lengkap or user.discord_id}** - "
                f"{user.exp:,} EXP (Level {user.level})"
            )
        
        embed.add_field(
            name="Peringkat",
            value="\n".join(leaderboard_list),
            inline=False
        )
        
        # Add user's rank
        user_rank = None
        for i, user in enumerate(users, 1):
            if user.discord_id == str(interaction.user.id):
                user_rank = i
                break
        
        if user_rank:
            embed.set_footer(text=f"Peringkat Anda: #{user_rank}")
        else:
            embed.set_footer(text="Anda belum masuk peringkat")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="badges", description="Lihat koleksi badge")
    async def badges(self, interaction: discord.Interaction):
        """View earned badges."""
        await interaction.response.defer(ephemeral=True)
        
        async for db in get_db():
            # Get user's badges
            from ...database import UserBadge, Badge
            user_badges = await db.query(UserBadge).filter(
                UserBadge.user_id == str(interaction.user.id)
            ).all()
            
            badges = []
            for ub in user_badges:
                badge = await db.query(Badge).filter(
                    Badge.id == ub.badge_id
                ).first()
                if badge:
                    badges.append(badge)
        
        # Create embed
        embed = discord.Embed(
            title="🏅 Koleksi Badge",
            description="Badge yang telah Anda kumpulkan",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        if badges:
            badge_list = []
            for badge in badges:
                badge_list.append(
                    f"{badge.icon} **{badge.name}** - {badge.description}"
                )
            
            embed.add_field(
                name="Badge",
                value="\n".join(badge_list),
                inline=False
            )
        else:
            embed.add_field(
                name="Status",
                value="Anda belum memiliki badge. Selesaikan tugas dan hadir kuliah untuk mendapatkan badge!",
                inline=False
            )
        
        # Add available badges
        all_badges = await db.query(Badge).all()
        if all_badges:
            available = []
            for badge in all_badges:
                if badge not in badges:
                    available.append(f"{badge.icon} {badge.name}")
            
            if available:
                embed.add_field(
                    name="Badge Tersedia",
                    value=", ".join(available[:5]) + ("..." if len(available) > 5 else ""),
                    inline=False
                )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="status-bot", description="Status bot")
    @app_commands.checks.has_role("Admin")
    async def status_bot(self, interaction: discord.Interaction):
        """View bot status."""
        await interaction.response.defer(ephemeral=True)
        
        import psutil
        import os
        
        # Get system info
        process = psutil.Process(os.getpid())
        memory = process.memory_info()
        
        embed = discord.Embed(
            title="🤖 Bot Status",
            description="Status sistem Teaching Assistant Bot",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Uptime",
            value=f"{datetime.utcnow() - self.bot.launch_time}",
            inline=True
        )
        embed.add_field(
            name="Memory",
            value=f"{memory.rss / 1024 / 1024:.1f} MB",
            inline=True
        )
        embed.add_field(
            name="Latency",
            value=f"{self.bot.latency * 1000:.0f}ms",
            inline=True
        )
        
        # Database status
        async for db in get_db():
            try:
                await db.execute("SELECT 1")
                db_status = "✅ Connected"
            except Exception:
                db_status = "❌ Disconnected"
        
        embed.add_field(
            name="Database",
            value=db_status,
            inline=True
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="help-attendance", description="Panduan absensi")
    async def help_attendance(self, interaction: discord.Interaction):
        """View attendance guide."""
        await interaction.response.defer(ephemeral=True)
        
        embed = discord.Embed(
            title="📖 Panduan Absensi — FIKTI UMSU",
            description="Cara menggunakan fitur absensi",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Student commands
        student_commands = (
            "• `/verify <NIM>` — Verifikasi akun\n"
            "• `/absen <kode>` — Absen dengan kode\n"
            "• `/grade-report` — Lihat nilai\n"
            "• `/leaderboard` — Lihat peringkat\n"
            "• `/badges` — Lihat koleksi badge"
        )
        embed.add_field(
            name="Untuk Mahasiswa",
            value=student_commands,
            inline=False
        )
        
        # Lecturer commands
        lecturer_commands = (
            "• `/mulai-kuliah <kelas> <mata_kuliah>` — Mulai sesi absensi\n"
            "• `/tutup-kuliah` — Tutup sesi absensi\n"
            "• `/manual-absen` — Absensi manual\n"
            "• `/dcreate` — Buat tugas baru"
        )
        embed.add_field(
            name="Untuk Dosen",
            value=lecturer_commands,
            inline=False
        )
        
        # Admin commands
        admin_commands = (
            "• `/approve-registration` — Setujui registrasi\n"
            "• `/reject-registration` — Tolak registrasi\n"
            "• `/override-attendance` — Override absensi\n"
            "• `/status-bot` — Status bot"
        )
        embed.add_field(
            name="Untuk Admin",
            value=admin_commands,
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
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
    await bot.add_cog(ReportCommands(bot))
