"""Attendance commands for tracking student attendance."""

import random
import string
import logging
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands

from ...config import get_settings
from ...database import (
    User,
    AttendanceSession,
    AttendanceRecord,
    get_db,
)

logger = logging.getLogger(__name__)


class AttendanceCommands(commands.Cog):
    """Attendance commands for tracking student attendance."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings = get_settings()
    
    @app_commands.command(name="mulai-kuliah", description="Mulai sesi absensi")
    @app_commands.describe(
        kelas="Kelas (contoh: TI-B1-2024)",
        mata_kuliah="Mata kuliah"
    )
    @app_commands.checks.has_role("Dosen")
    async def mulai_kuliah(
        self,
        interaction: discord.Interaction,
        kelas: str,
        mata_kuliah: str
    ):
        """Start attendance session."""
        await interaction.response.defer(ephemeral=True)
        
        # Generate attendance code
        code = ''.join(random.choices(
            string.ascii_uppercase + string.digits,
            k=self.settings.attendance_code_length
        ))
        
        async for db in get_db():
            # Get course
            from ...database import Course
            course = await db.query(Course).filter(
                Course.name.ilike(f"%{mata_kuliah}%")
            ).first()
            
            if not course:
                await interaction.followup.send(
                    "❌ Mata kuliah tidak ditemukan.",
                    ephemeral=True
                )
                return
            
            # Create attendance session
            session = AttendanceSession(
                class_id=kelas,
                course_id=course.id,
                session_date=datetime.utcnow(),
                opens_at=datetime.utcnow(),
                attendance_code=code,
                status="active",
                started_by=str(interaction.user.id),
            )
            db.add(session)
            await db.commit()
        
        # Send embed to channel
        embed = discord.Embed(
            title="📋 Absensi Dimulai",
            description=f"Sesi absensi untuk **{mata_kuliah}** kelas **{kelas}** telah dimulai.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Kode Absen", value=f"`{code}`", inline=True)
        embed.add_field(name="Berlaku Hingga", value="15 menit", inline=True)
        embed.add_field(
            name="Cara Absen",
            value="Gunakan `/absen [kode]`",
            inline=False
        )
        embed.set_footer(text=f"Dimulai oleh {interaction.user.display_name}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        logger.info(
            f"Attendance session started for {mata_kuliah} {kelas} "
            f"by {interaction.user.id}"
        )
    
    @app_commands.command(name="tutup-kuliah", description="Tutup sesi absensi")
    @app_commands.checks.has_role("Dosen")
    async def tutup_kuliah(self, interaction: discord.Interaction):
        """Close attendance session."""
        await interaction.response.defer(ephemeral=True)
        
        async for db in get_db():
            # Get active session
            session = await db.query(AttendanceSession).filter(
                AttendanceSession.started_by == str(interaction.user.id),
                AttendanceSession.status == "active"
            ).first()
            
            if not session:
                await interaction.followup.send(
                    "❌ Tidak ada sesi absensi aktif.",
                    ephemeral=True
                )
                return
            
            # Close session
            session.closes_at = datetime.utcnow()
            session.status = "closed"
            await db.commit()
            
            # Get attendance count
            attendance_count = await db.query(AttendanceRecord).filter(
                AttendanceRecord.session_id == session.id
            ).count()
        
        embed = discord.Embed(
            title="📋 Absensi Ditutup",
            description="Sesi absensi telah ditutup.",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Total Hadir", value=str(attendance_count), inline=True)
        embed.set_footer(text=f"Ditutup oleh {interaction.user.display_name}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        logger.info(
            f"Attendance session closed by {interaction.user.id}, "
            f"{attendance_count} students attended"
        )
    
    @app_commands.command(name="absen", description="Absen dengan kode")
    @app_commands.describe(kode="Kode absensi")
    async def absen(self, interaction: discord.Interaction, kode: str):
        """Submit attendance with code."""
        await interaction.response.defer(ephemeral=True)
        
        async for db in get_db():
            # Get active session with code
            session = await db.query(AttendanceSession).filter(
                AttendanceSession.attendance_code == kode.upper(),
                AttendanceSession.status == "active"
            ).first()
            
            if not session:
                await interaction.followup.send(
                    "❌ Kode absensi tidak valid atau sudah tidak aktif.",
                    ephemeral=True
                )
                return
            
            # Check if already attended
            existing = await db.query(AttendanceRecord).filter(
                AttendanceRecord.session_id == session.id,
                AttendanceRecord.student_id == str(interaction.user.id)
            ).first()
            
            if existing:
                await interaction.followup.send(
                    "❌ Anda sudah melakukan absensi.",
                    ephemeral=True
                )
                return
            
            # Check if session expired
            if datetime.utcnow() > session.opens_at + timedelta(
                minutes=self.settings.attendance_code_expiry_minutes
            ):
                session.status = "expired"
                await db.commit()
                
                await interaction.followup.send(
                    "❌ Kode absensi sudah kedaluwarsa.",
                    ephemeral=True
                )
                return
            
            # Record attendance
            record = AttendanceRecord(
                session_id=session.id,
                student_id=str(interaction.user.id),
                status="hadir",
                check_in_time=datetime.utcnow(),
                check_method="code",
                exp_earned=10,  # Base EXP for attendance
            )
            db.add(record)
            
            # Update user EXP
            user = await db.query(User).filter(
                User.discord_id == str(interaction.user.id)
            ).first()
            
            if user:
                user.exp += 10
                # Check level up
                new_level = self.calculate_level(user.exp)
                if new_level > user.level:
                    user.level = new_level
                    await interaction.followup.send(
                        f"✅ Absensi berhasil! 🎉 Level up! Level {new_level}",
                        ephemeral=True
                    )
                    await db.commit()
                    return
            
            await db.commit()
        
        await interaction.followup.send(
            "✅ Absensi berhasil!",
            ephemeral=True
        )
        
        logger.info(
            f"Student {interaction.user.id} attended session {session.id}"
        )
    
    @app_commands.command(name="manual-absen", description="Absensi manual oleh dosen")
    @app_commands.describe(
        mahasiswa="Mahasiswa yang akan diabsen",
        status="Status kehadiran"
    )
    @app_commands.checks.has_role("Dosen")
    async def manual_absen(
        self,
        interaction: discord.Interaction,
        mahasiswa: discord.Member,
        status: str
    ):
        """Manual attendance by lecturer."""
        await interaction.response.defer(ephemeral=True)
        
        valid_statuses = ["hadir", "izin", "sakit"]
        if status.lower() not in valid_statuses:
            await interaction.followup.send(
                f"❌ Status tidak valid. Pilihan: {', '.join(valid_statuses)}",
                ephemeral=True
            )
            return
        
        async for db in get_db():
            # Get active session
            session = await db.query(AttendanceSession).filter(
                AttendanceSession.started_by == str(interaction.user.id),
                AttendanceSession.status == "active"
            ).first()
            
            if not session:
                await interaction.followup.send(
                    "❌ Tidak ada sesi absensi aktif.",
                    ephemeral=True
                )
                return
            
            # Check if already attended
            existing = await db.query(AttendanceRecord).filter(
                AttendanceRecord.session_id == session.id,
                AttendanceRecord.student_id == str(mahasiswa.id)
            ).first()
            
            if existing:
                existing.status = status.lower()
                existing.check_method = "manual"
            else:
                record = AttendanceRecord(
                    session_id=session.id,
                    student_id=str(mahasiswa.id),
                    status=status.lower(),
                    check_in_time=datetime.utcnow(),
                    check_method="manual",
                )
                db.add(record)
            
            await db.commit()
        
        await interaction.followup.send(
            f"✅ Absensi {mahasiswa.mention} diubah menjadi **{status}**.",
            ephemeral=True
        )
        
        logger.info(
            f"Manual attendance for {mahasiswa.id}: {status} by {interaction.user.id}"
        )
    
    @app_commands.command(name="override-attendance", description="Override absensi")
    @app_commands.describe(
        session_id="Session ID",
        mahasiswa="Mahasiswa",
        status="Status baru",
        notes="Catatan"
    )
    @app_commands.checks.has_role("Admin")
    async def override_attendance(
        self,
        interaction: discord.Interaction,
        session_id: str,
        mahasiswa: discord.Member,
        status: str,
        notes: str = ""
    ):
        """Override attendance record."""
        await interaction.response.defer(ephemeral=True)
        
        async for db in get_db():
            session = await db.query(AttendanceSession).filter(
                AttendanceSession.id == session_id
            ).first()
            
            if not session:
                await interaction.followup.send(
                    "❌ Sesi tidak ditemukan.",
                    ephemeral=True
                )
                return
            
            record = await db.query(AttendanceRecord).filter(
                AttendanceRecord.session_id == session_id,
                AttendanceRecord.student_id == str(mahasiswa.id)
            ).first()
            
            if record:
                record.status = status.lower()
                record.check_method = "override"
            else:
                record = AttendanceRecord(
                    session_id=session_id,
                    student_id=str(mahasiswa.id),
                    status=status.lower(),
                    check_in_time=datetime.utcnow(),
                    check_method="override",
                )
                db.add(record)
            
            await db.commit()
        
        await interaction.followup.send(
            f"✅ Absensi {mahasiswa.mention} di-override menjadi **{status}**.",
            ephemeral=True
        )
        
        logger.info(
            f"Attendance overridden for {mahasiswa.id}: {status} "
            f"by {interaction.user.id}"
        )
    
    def calculate_level(self, exp: int) -> int:
        """Calculate level from EXP."""
        level = 1
        while exp >= self.settings.exp_base * (level ** self.settings.exp_level_multiplier):
            level += 1
            if level >= self.settings.max_level:
                break
        return level - 1


async def setup(bot: commands.Bot):
    """Add cog to bot."""
    await bot.add_cog(AttendanceCommands(bot))
