"""Registration commands — Channel-based architecture."""

import re
import logging
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from ...config import get_settings
from ...database.engine import get_db
from ...database.models import (
    Student,
    ClassChannel,
    StudentClass,
    PendingRegistration,
    Relator,
)

logger = logging.getLogger(__name__)


class RegistrationModal(discord.ui.Modal, title="📝 REGISTRASI MAHASISWA FIKTI UMSU"):
    """Modal form for student registration."""
    
    nim = discord.ui.TextInput(
        label="NIM (10 digit angka)",
        placeholder="2471110042",
        required=True,
        max_length=10,
        min_length=10,
        style=discord.TextStyle.short,
    )
    
    nama_lengkap = discord.ui.TextInput(
        label="Nama Lengkap (sesuai KTP, tanpa gelar)",
        placeholder="Budi Santoso",
        required=True,
        max_length=100,
        style=discord.TextStyle.short,
    )
    
    prodi = discord.ui.TextInput(
        label="Program Studi (TI/SI/SD)",
        placeholder="TI",
        required=True,
        max_length=2,
        style=discord.TextStyle.short,
    )
    
    kelas = discord.ui.TextInput(
        label="Kelas (Huruf+Nomor, contoh: A1)",
        placeholder="A1",
        required=True,
        max_length=5,
        style=discord.TextStyle.short,
    )
    
    no_wa = discord.ui.TextInput(
        label="No. WhatsApp (opsional)",
        placeholder="081234567890",
        required=False,
        max_length=20,
        style=discord.TextStyle.short,
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle form submission."""
        await interaction.response.defer(ephemeral=True)
        
        settings = get_settings()
        
        # Validate NIM format (10 digits)
        nim_value = self.nim.value.strip()
        if not re.match(r"^\d{10}$", nim_value):
            await interaction.followup.send(
                "❌ **NIM tidak valid!**\n\n"
                "Format: 10 digit angka tanpa spasi\n"
                "Contoh: `2471110042`\n\n"
                "Penjelasan:\n"
                "• 2 digit pertama = Angkatan (24 = tahun 2024)\n"
                "• 3 digit kedua = Kode Prodi (711=TI, 712=SI, 713=TI Baru)\n"
                "• 5 digit terakhir = Nomor Urut",
                ephemeral=True,
            )
            return
        
        # Validate Prodi
        prodi_value = self.prodi.value.strip().upper()
        if prodi_value not in ["TI", "SI", "SD"]:
            await interaction.followup.send(
                "❌ **Program Studi tidak valid!**\n\n"
                "Format: 2 huruf kode prodi (huruf kapital)\n\n"
                "Pilihan yang benar:\n"
                "• `TI` = Teknik Informatika\n"
                "• `SI` = Sistem Informasi\n"
                "• `SD` = Seni Design",
                ephemeral=True,
            )
            return
        
        # Validate Kelas format (letter + number, e.g., A1, B2, C1)
        kelas_value = self.kelas.value.strip().upper()
        if not re.match(r"^[A-Z]\d{1,2}$", kelas_value):
            await interaction.followup.send(
                "❌ **Format kelas tidak valid!**\n\n"
                "Format: Huruf + Nomor (huruf kapital, tanpa spasi)\n\n"
                "Contoh yang BENAR:\n"
                "• `A1` (Kelas A, Paralel 1)\n"
                "• `B2` (Kelas B, Paralel 2)\n"
                "• `C1` (Kelas C, Paralel 1)\n\n"
                "Contoh yang SALAH:\n"
                "❌ `a1` (huruf kecil)\n"
                "❌ `A 1` (ada spasi)\n"
                "❌ `Kelas A1` (ada tulisan 'Kelas')",
                ephemeral=True,
            )
            return
        
        # Extract angkatan from NIM (first 2 digits)
        angkatan = int(nim_value[:2])
        
        # Check if NIM already registered
        async with get_db() as db:
            existing = await db.execute(
                select(Student).where(Student.nim == nim_value)
            )
            if existing.scalar_one_or_none():
                await interaction.followup.send(
                    "❌ NIM sudah terdaftar oleh mahasiswa lain.",
                    ephemeral=True,
                )
                return
            
            # Check if already pending
            existing_pending = await db.execute(
                select(PendingRegistration).where(
                    PendingRegistration.discord_id == str(interaction.user.id)
                )
            )
            if existing_pending.scalar_one_or_none():
                await interaction.followup.send(
                    "❌ Anda sudah mengajukan registrasi. Menunggu persetujuan admin.",
                    ephemeral=True,
                )
                return
            
            # Save pending registration
            pending = PendingRegistration(
                discord_id=str(interaction.user.id),
                discord_username=interaction.user.display_name,
                nim=nim_value,
                nama_lengkap=self.nama_lengkap.value.strip(),
                prodi=prodi_value,
                angkatan=angkatan,
                kelas=kelas_value,
                no_wa=self.no_wa.value.strip() if self.no_wa.value else None,
                status="pending",
            )
            db.add(pending)
            await db.commit()
        
        # Notify admin channel
        admin_channel = discord.utils.get(interaction.guild.channels, name="admin")
        if admin_channel:
            embed = discord.Embed(
                title="📋 Registrasi Baru",
                description=f"Mahasiswa baru mengajukan registrasi:",
                color=discord.Color.yellow(),
            )
            embed.add_field(name="NIM", value=nim_value, inline=True)
            embed.add_field(
                name="Nama", value=self.nama_lengkap.value.strip(), inline=True
            )
            embed.add_field(name="Prodi", value=prodi_value, inline=True)
            embed.add_field(name="Kelas", value=kelas_value, inline=True)
            embed.add_field(
                name="No WA",
                value=self.no_wa.value.strip() if self.no_wa.value else "-",
                inline=True,
            )
            embed.add_field(
                name="Discord",
                value=interaction.user.mention,
                inline=True,
            )
            embed.set_footer(text=f"ID: {interaction.user.id}")
            
            await admin_channel.send(embed=embed)
        
        # Confirm to user
        embed = discord.Embed(
            title="✅ Registrasi Berhasil Diajukan!",
            description=(
                "Data Anda telah berhasil dikirim ke admin untuk diverifikasi.\n\n"
                "**Yang perlu Anda lakukan:**\n"
                "1. Tunggu persetujuan admin di channel #admin\n"
                "2. Anda akan mendapat notifikasi DM setelah disetujui\n"
                "3. Setelah disetujui, Anda akan otomatis masuk ke channel kelas Anda\n\n"
                "**Data yang Anda kirim:**\n"
                f"```"
                f"NIM    : {nim_value}\n"
                f"Nama   : {self.nama_lengkap.value.strip()}\n"
                f"Prodi  : {prodi_value}\n"
                f"Kelas  : {kelas_value}\n"
                f"No WA  : {self.no_wa.value.strip() if self.no_wa.value else '-'}"
                f"```"
            ),
            color=discord.Color.green(),
        )
        embed.set_footer(text="Menunggu persetujuan admin...")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        logger.info(
            f"Registration submitted: {nim_value} by {interaction.user.id}"
        )


class RegistrationCommands(commands.Cog):
    """Registration commands for student verification."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings = get_settings()
    
    @app_commands.command(name="register", description="Registrasi sebagai mahasiswa")
    async def register(self, interaction: discord.Interaction):
        """Open registration modal."""
        # Check if already verified
        async with get_db() as db:
            existing = await db.execute(
                select(Student).where(
                    Student.discord_id == str(interaction.user.id)
                )
            )
            if existing.scalar_one_or_none():
                await interaction.response.send_message(
                    "❌ Anda sudah terdaftar sebagai mahasiswa.",
                    ephemeral=True,
                )
                return
        
        # Show modal
        modal = RegistrationModal()
        await interaction.response.send_modal(modal)
    
    @app_commands.command(
        name="approve", description="Setujui registrasi mahasiswa"
    )
    @app_commands.describe(user="Mahasiswa yang akan disetujui")
    @app_commands.checks.has_role("Admin")
    async def approve(self, interaction: discord.Interaction, user: discord.Member):
        """Approve student registration and assign to class channel."""
        await interaction.response.defer(ephemeral=True)
        
        async with get_db() as db:
            # Get pending registration
            pending_result = await db.execute(
                select(PendingRegistration).where(
                    PendingRegistration.discord_id == str(user.id),
                    PendingRegistration.status == "pending",
                )
            )
            pending = pending_result.scalar_one_or_none()
            
            if not pending:
                await interaction.followup.send(
                    "❌ Tidak ada registrasi pending untuk pengguna ini.",
                    ephemeral=True,
                )
                return
            
            # Check if NIM already used
            existing_student = await db.execute(
                select(Student).where(Student.nim == pending.nim)
            )
            if existing_student.scalar_one_or_none():
                await interaction.followup.send(
                    f"❌ NIM {pending.nim} sudah terdaftar.",
                    ephemeral=True,
                )
                return
            
            # Create student record
            student = Student(
                discord_id=str(user.id),
                nim=pending.nim,
                nama_lengkap=pending.nama_lengkap,
                prodi=pending.prodi,
                angkatan=pending.angkatan,
                kelas=pending.kelas,
                no_wa=pending.no_wa,
                is_verified=True,
                verified_by=str(interaction.user.id),
                verified_at=datetime.utcnow(),
            )
            db.add(student)
            
            # Update pending status
            pending.status = "approved"
            pending.reviewed_by = str(interaction.user.id)
            pending.reviewed_at = datetime.utcnow()
            
            await db.commit()
            
            # Get or create class channel
            class_channel_name = self._get_class_channel_name(
                pending.prodi, pending.kelas
            )
            
            # Check if class channel exists
            existing_class = await db.execute(
                select(ClassChannel).where(
                    ClassChannel.nama_kelas == class_channel_name
                )
            )
            class_channel = existing_class.scalar_one_or_none()
            
            if not class_channel:
                # Create class channel
                class_channel = await self._create_class_channel(
                    interaction.guild, pending, db
                )
            
            # Add student to class
            student_class = StudentClass(
                student_id=student.id,
                class_channel_id=class_channel.id,
            )
            db.add(student_class)
            await db.commit()
            
            # Assign roles and permissions
            await self._assign_student_permissions(
                interaction.guild, user, class_channel
            )
        
        # Confirm
        await interaction.followup.send(
            f"✅ Registrasi {user.mention} disetujui.\n"
            f"Mahasiswa telah dimasukkan ke kelas {pending.kelas} {pending.prodi}.",
            ephemeral=True,
        )
        
        # DM student
        try:
            await user.send(
                f"🎉 Registrasi Anda disetujui!\n\n"
                f"**NIM:** {pending.nim}\n"
                f"**Nama:** {pending.nama_lengkap}\n"
                f"**Prodi:** {pending.prodi}\n"
                f"**Kelas:** {pending.kelas}\n\n"
                f"Sekarang Anda bisa mengakses channel kelas Anda."
            )
        except discord.Forbidden:
            logger.warning(f"Could not DM user {user.id}")
        
        logger.info(
            f"Registration approved: {pending.nim} by {interaction.user.id}"
        )
    
    @app_commands.command(
        name="reject", description="Tolak registrasi mahasiswa"
    )
    @app_commands.describe(
        user="Mahasiswa yang akan ditolak",
        alasan="Alasan penolakan",
    )
    @app_commands.checks.has_role("Admin")
    async def reject(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        alasan: str,
    ):
        """Reject student registration."""
        await interaction.response.defer(ephemeral=True)
        
        async with get_db() as db:
            pending_result = await db.execute(
                select(PendingRegistration).where(
                    PendingRegistration.discord_id == str(user.id),
                    PendingRegistration.status == "pending",
                )
            )
            pending = pending_result.scalar_one_or_none()
            
            if not pending:
                await interaction.followup.send(
                    "❌ Tidak ada registrasi pending untuk pengguna ini.",
                    ephemeral=True,
                )
                return
            
            # Update status
            pending.status = "rejected"
            pending.reviewed_by = str(interaction.user.id)
            pending.review_notes = alasan
            pending.reviewed_at = datetime.utcnow()
            
            await db.commit()
        
        # DM student
        try:
            await user.send(
                f"❌ Registrasi Anda ditolak.\n\n"
                f"**Alasan:** {alasan}\n\n"
                f"Silakan hubungi admin untuk informasi lebih lanjut."
            )
        except discord.Forbidden:
            logger.warning(f"Could not DM user {user.id}")
        
        await interaction.followup.send(
            f"✅ Registrasi {user.mention} ditolak.",
            ephemeral=True,
        )
        
        logger.info(
            f"Registration rejected: {pending.nim} by {interaction.user.id}"
        )
    
    @app_commands.command(
        name="list-pending", description="Tampilkan semua registrasi pending"
    )
    @app_commands.checks.has_role("Admin")
    async def list_pending(self, interaction: discord.Interaction):
        """List all pending registrations."""
        await interaction.response.defer(ephemeral=True)
        
        async with get_db() as db:
            result = await db.execute(
                select(PendingRegistration).where(
                    PendingRegistration.status == "pending"
                )
            )
            pending_list = result.scalars().all()
        
        if not pending_list:
            await interaction.followup.send(
                "✅ Tidak ada registrasi pending.", ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="📋 Registrasi Pending",
            description=f"Ada {len(pending_list)} registrasi menunggu persetujuan:",
            color=discord.Color.yellow(),
        )
        
        for pending in pending_list:
            embed.add_field(
                name=f"{pending.nama_lengkap} ({pending.nim})",
                value=(
                    f"**Prodi:** {pending.prodi}\n"
                    f"**Kelas:** {pending.kelas}\n"
                    f"**Discord:** <@{pending.discord_id}>"
                ),
                inline=False,
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    def _get_class_channel_name(self, prodi: str, kelas: str) -> str:
        """Generate class channel name."""
        return f"kelas-{kelas.lower()}-{prodi.lower()}"
    
    async def _create_class_channel(
        self,
        guild: discord.Guild,
        pending: PendingRegistration,
        db,
    ) -> ClassChannel:
        """Create a new class channel with role."""
        class_code = pending.kelas
        prodi = pending.prodi
        angkatan = pending.angkatan
        
        # Channel name: kelas-a1-si
        channel_name = self._get_class_channel_name(prodi, class_code)
        
        # Role name: Kelas-A1-SI
        role_name = f"Kelas-{class_code}-{prodi}"
        
        # Create role (no permissions, just for identification)
        class_role = await guild.create_role(
            name=role_name,
            permissions=discord.Permissions(0),
            reason=f"Auto-created for class {class_code} {prodi}",
        )
        
        # Create channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            class_role: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
            ),
        }
        
        # Find category for this prodi
        category = None
        for ch in guild.categories:
            if prodi.upper() in ch.name.upper():
                category = ch
                break
        
        channel = await guild.create_text_channel(
            channel_name,
            overwrites=overwrites,
            category=category,
            topic=f"Kelas {class_code} {prodi} Angkatan {angkatan}",
            reason=f"Auto-created for class {class_code} {prodi}",
        )
        
        # Save to database
        class_channel = ClassChannel(
            nama_kelas=channel_name,
            mata_kuliah="",  # Will be filled when course is assigned
            prodi=prodi,
            angkatan=angkatan,
            kelas_code=class_code,
            channel_id=str(channel.id),
            channel_name=f"#{channel_name}",
            role_id=str(class_role.id),
            role_name=role_name,
        )
        db.add(class_channel)
        await db.commit()
        
        logger.info(f"Created class channel: {channel_name} with role {role_name}")
        
        return class_channel
    
    async def _assign_student_permissions(
        self,
        guild: discord.Guild,
        member: discord.Member,
        class_channel: ClassChannel,
    ):
        """Assign permissions to student for their class."""
        # Get class role
        class_role = guild.get_role(int(class_channel.role_id))
        if class_role:
            await member.add_roles(class_role)
        
        # Add @Mahasiswa role if exists
        mahasiswa_role = discord.utils.get(guild.roles, name="Mahasiswa")
        if mahasiswa_role:
            await member.add_roles(mahasiswa_role)
        
        # Ensure #umum is visible
        umum_channel = discord.utils.get(guild.channels, name="umum")
        if umum_channel:
            # Get @Mahasiswa role permissions for #umum
            if mahasiswa_role:
                await umum_channel.set_permissions(
                    mahasiswa_role,
                    read_messages=True,
                    send_messages=True,
                    read_message_history=True,
                )


async def setup(bot: commands.Bot):
    """Add cog to bot."""
    await bot.add_cog(RegistrationCommands(bot))
