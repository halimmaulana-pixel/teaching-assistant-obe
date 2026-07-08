"""Select menu components — Database-driven dropdowns."""

import logging
from typing import List, Optional

import discord
from discord import ui
from sqlalchemy import select

from ...database.engine import get_db
from ...database.models import (
    ClassChannel,
    PendingRegistration,
    Relator,
    Student,
    StudentClass,
)

logger = logging.getLogger(__name__)


class ClassSelect(ui.Select):
    """Dropdown for selecting a class from class_channels table."""
    
    def __init__(
        self,
        prodi: Optional[str] = None,
        angkatan: Optional[int] = None,
        custom_id: str = "class_select",
    ):
        self.prodi = prodi
        self.angkatan = angkatan
        self.fetched = False
        super().__init__(
            placeholder="🎓 Pilih Kelas...",
            min_values=1,
            max_values=1,
            custom_id=custom_id,
            options=[],  # Will be populated dynamically
        )
    
    async def fetch_options(self) -> List[discord.SelectOption]:
        """Fetch classes from database."""
        options = []
        async with get_db() as db:
            query = select(ClassChannel).where(ClassChannel.is_active == True)
            
            if self.prodi:
                query = query.where(ClassChannel.prodi == self.prodi)
            if self.angkatan:
                query = query.where(ClassChannel.angkatan == self.angkatan)
            
            result = await db.execute(query)
            classes = result.scalars().all()
            
            for cls in classes:
                # Format: "Algoritma Pemrograman - A1 (TI)"
                label = f"{cls.mata_kuliah or 'Kelas'} - {cls.kelas_code}"
                if len(label) > 100:
                    label = label[:97] + "..."
                
                description = f"Prodi: {cls.prodi} | Angkatan: {cls.angkatan}"
                if len(description) > 100:
                    description = description[:97] + "..."
                
                # Emoji based on prodi
                emoji_map = {"TI": "💻", "SI": "📊", "SD": "🎨"}
                emoji = emoji_map.get(cls.prodi, "📘")
                
                options.append(
                    discord.SelectOption(
                        label=label,
                        value=str(cls.id),
                        description=description,
                        emoji=emoji,
                    )
                )
        
        # Discord allows max 25 options
        self.options = options[:25]
        self.fetched = True
        return self.options
    
    async def callback(self, interaction: discord.Interaction):
        """Handle class selection."""
        selected_id = int(self.values[0])
        
        async with get_db() as db:
            result = await db.execute(
                select(ClassChannel).where(ClassChannel.id == selected_id)
            )
            cls = result.scalar_one_or_none()
            
            if not cls:
                await interaction.response.send_message(
                    "❌ Kelas tidak ditemukan", ephemeral=True
                )
                return
            
            # Store in view for parent access
            self.view.selected_class = cls
            
            # Update placeholder to show selection
            self.placeholder = f"✅ {cls.nama_kelas}"
            
            await interaction.response.defer()
            self.view.stop()


class StudentSelect(ui.Select):
    """Dropdown for selecting students from pending_registrations."""
    
    def __init__(
        self,
        status: str = "pending",
        custom_id: str = "student_select",
    ):
        self.status = status
        self.fetched = False
        super().__init__(
            placeholder="👤 Pilih Mahasiswa...",
            min_values=1,
            max_values=1,
            custom_id=custom_id,
            options=[],
        )
    
    async def fetch_options(self) -> List[discord.SelectOption]:
        """Fetch pending students from database."""
        options = []
        async with get_db() as db:
            query = (
                select(PendingRegistration)
                .where(PendingRegistration.status == self.status)
                .order_by(PendingRegistration.created_at.desc())
            )
            
            result = await db.execute(query)
            students = result.scalars().all()
            
            for student in students:
                label = student.nama_lengkap
                if len(label) > 100:
                    label = label[:97] + "..."
                
                description = f"NIM: {student.nim} | {student.prodi} {student.kelas}"
                if len(description) > 100:
                    description = description[:97] + "..."
                
                options.append(
                    discord.SelectOption(
                        label=label,
                        value=student.discord_id,
                        description=description,
                        emoji="👨‍🎓",
                    )
                )
        
        self.options = options[:25]
        self.fetched = True
        return self.options
    
    async def callback(self, interaction: discord.Interaction):
        """Handle student selection."""
        selected_discord_id = self.values[0]
        
        async with get_db() as db:
            result = await db.execute(
                select(PendingRegistration).where(
                    PendingRegistration.discord_id == selected_discord_id
                )
            )
            student = result.scalar_one_or_none()
            
            if not student:
                await interaction.response.send_message(
                    "❌ Mahasiswa tidak ditemukan", ephemeral=True
                )
                return
            
            self.view.selected_student = student
            self.placeholder = f"✅ {student.nama_lengkap}"
            
            await interaction.response.defer()
            self.view.stop()


class RelatorSelect(ui.Select):
    """Dropdown for selecting a relator (dosen)."""
    
    def __init__(self, custom_id: str = "relator_select"):
        self.fetched = False
        super().__init__(
            placeholder="👨‍🏫 Pilih Relator (Dosen)...",
            min_values=1,
            max_values=1,
            custom_id=custom_id,
            options=[],
        )
    
    async def fetch_options(self) -> List[discord.SelectOption]:
        """Fetch dosen list from database."""
        options = []
        async with get_db() as db:
            result = await db.execute(select(Relator))
            relators = result.scalars().all()
            
            for relator in relators:
                # Get class info
                class_result = await db.execute(
                    select(ClassChannel).where(
                        ClassChannel.id == relator.class_channel_id
                    )
                )
                cls = class_result.scalar_one_or_none()
                
                class_name = f"{cls.nama_kelas}" if cls else "Unknown"
                
                label = relator.dosen_nama
                if len(label) > 100:
                    label = label[:97] + "..."
                
                description = f"Relator: {class_name}"
                if len(description) > 100:
                    description = description[:97] + "..."
                
                options.append(
                    discord.SelectOption(
                        label=label,
                        value=relator.dosen_discord_id,
                        description=description,
                        emoji="👨‍🏫",
                    )
                )
        
        self.options = options[:25]
        self.fetched = True
        return self.options
    
    async def callback(self, interaction: discord.Interaction):
        """Handle relator selection."""
        selected_discord_id = self.values[0]
        
        async with get_db() as db:
            result = await db.execute(
                select(Relator).where(
                    Relator.dosen_discord_id == selected_discord_id
                )
            )
            relator = result.scalar_one_or_none()
            
            if not relator:
                await interaction.response.send_message(
                    "❌ Relator tidak ditemukan", ephemeral=True
                )
                return
            
            self.view.selected_relator = relator
            self.placeholder = f"✅ {relator.dosen_nama}"
            
            await interaction.response.defer()
            self.view.stop()


class MultiStudentSelect(ui.Select):
    """Multi-select dropdown for batch operations."""
    
    def __init__(
        self,
        class_channel_id: Optional[int] = None,
        custom_id: str = "multi_student_select",
    ):
        self.class_channel_id = class_channel_id
        self.fetched = False
        super().__init__(
            placeholder="👥 Pilih Mahasiswa (max 10)...",
            min_values=1,
            max_values=10,
            custom_id=custom_id,
            options=[],
        )
    
    async def fetch_options(self) -> List[discord.SelectOption]:
        """Fetch students from class for batch operations."""
        options = []
        async with get_db() as db:
            if self.class_channel_id:
                # Get students in specific class
                query = (
                    select(Student)
                    .join(StudentClass)
                    .where(StudentClass.class_channel_id == self.class_channel_id)
                    .where(Student.is_verified == True)
                )
            else:
                # Get all verified students
                query = select(Student).where(Student.is_verified == True).limit(25)
            
            result = await db.execute(query)
            students = result.scalars().all()
            
            for student in students:
                label = student.nama_lengkap
                if len(label) > 100:
                    label = label[:97] + "..."
                
                description = f"NIM: {student.nim} | {student.kelas}"
                if len(description) > 100:
                    description = description[:97] + "..."
                
                options.append(
                    discord.SelectOption(
                        label=label,
                        value=str(student.discord_id),
                        description=description,
                        emoji="👨‍🎓",
                    )
                )
        
        self.options = options[:25]
        self.fetched = True
        return self.options
    
    async def callback(self, interaction: discord.Interaction):
        """Handle multi-student selection."""
        self.view.selected_students = self.values
        self.placeholder = f"✅ {len(self.values)} mahasiswa dipilih"
        await interaction.response.defer()
        self.view.stop()
