"""Admin commands — Server setup and management with dropdowns."""

import logging
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from ...config import get_settings
from ...database.engine import get_db
from ...database.models import (
    ClassChannel,
    Relator,
    Student,
    StudentClass,
    PendingRegistration,
)
from ..views.select_views import (
    SetRelatorViewV2,
    ApproveStudentView,
    ClassInfoView,
    BatchApproveView,
)

logger = logging.getLogger(__name__)


class AdminCommands(commands.Cog):
    """Admin commands for server setup and management."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings = get_settings()
    
    @app_commands.command(
        name="setup-server",
        description="Initialize server with base roles and channels",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_server(self, interaction: discord.Interaction):
        """Setup server with base structure."""
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        
        # Create base roles
        roles_created = []
        
        # Admin role
        admin_role = discord.utils.get(guild.roles, name="Admin")
        if not admin_role:
            admin_role = await guild.create_role(
                name="Admin",
                permissions=discord.Permissions.all(),
                reason="Server admin role",
            )
            roles_created.append("Admin")
        
        # Dosen role
        dosen_role = discord.utils.get(guild.roles, name="Dosen")
        if not dosen_role:
            dosen_role = await guild.create_role(
                name="Dosen",
                permissions=discord.Permissions(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                    kick_members=True,
                ),
                reason="Lecturer role",
            )
            roles_created.append("Dosen")
        
        # Mahasiswa role
        mahasiswa_role = discord.utils.get(guild.roles, name="Mahasiswa")
        if not mahasiswa_role:
            mahasiswa_role = await guild.create_role(
                name="Mahasiswa",
                permissions=discord.Permissions(0),
                reason="Student role",
            )
            roles_created.append("Mahasiswa")
        
        # Create base channels
        channels_created = []
        
        # #umum - global forum
        umum_channel = discord.utils.get(guild.channels, name="umum")
        if not umum_channel:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                mahasiswa_role: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True,
                ),
                dosen_role: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                ),
                admin_role: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                ),
            }
            umum_channel = await guild.create_text_channel(
                "umum",
                overwrites=overwrites,
                topic="Forum umum untuk semua mahasiswa dan dosen",
                reason="Global forum channel",
            )
            channels_created.append("#umum")
        
        # #pengumuman - announcements
        pengumuman_channel = discord.utils.get(guild.channels, name="pengumuman")
        if not pengumuman_channel:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                mahasiswa_role: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=False,
                ),
                dosen_role: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                ),
                admin_role: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                ),
            }
            pengumuman_channel = await guild.create_text_channel(
                "pengumuman",
                overwrites=overwrites,
                topic="Pengumuman dari dosen dan admin",
                reason="Announcements channel",
            )
            channels_created.append("#pengumuman")
        
        # #registrasi - for new students
        registrasi_channel = discord.utils.get(
            guild.channels, name="registrasi"
        )
        if not registrasi_channel:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                ),
                mahasiswa_role: discord.PermissionOverwrite(
                    read_messages=False,
                ),
                dosen_role: discord.PermissionOverwrite(
                    read_messages=False,
                ),
                admin_role: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                ),
            }
            registrasi_channel = await guild.create_text_channel(
                "registrasi",
                overwrites=overwrites,
                topic="Registrasi mahasiswa baru - Ketik /register",
                reason="Registration channel",
            )
            channels_created.append("#registrasi")
        
        # #admin - admin only
        admin_channel = discord.utils.get(guild.channels, name="admin")
        if not admin_channel:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    read_messages=False
                ),
                mahasiswa_role: discord.PermissionOverwrite(
                    read_messages=False
                ),
                dosen_role: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                ),
                admin_role: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                ),
            }
            admin_channel = await guild.create_text_channel(
                "admin",
                overwrites=overwrites,
                topic="Admin only - Kelola mahasiswa",
                reason="Admin channel",
            )
            channels_created.append("#admin")
        
        # Create categories for prodi
        categories_created = []
        for prodi in ["TI", "SI", "SD"]:
            category = discord.utils.get(guild.categories, name=prodi)
            if not category:
                category = await guild.create_category(
                    prodi,
                    overwrites={
                        guild.default_role: discord.PermissionOverwrite(
                            read_messages=False
                        ),
                    },
                    reason=f"Category for {prodi}",
                )
                categories_created.append(prodi)
        
        # Summary
        embed = discord.Embed(
            title="✅ Server Setup Complete",
            description="Server telah dikonfigurasi dengan benar.",
            color=discord.Color.green(),
        )
        
        if roles_created:
            embed.add_field(
                name="Roles Dibuat",
                value=", ".join(roles_created),
                inline=False,
            )
        
        if channels_created:
            embed.add_field(
                name="Channels Dibuat",
                value=", ".join(channels_created),
                inline=False,
            )
        
        if categories_created:
            embed.add_field(
                name="Categories Dibuat",
                value=", ".join(categories_created),
                inline=False,
            )
        
        embed.add_field(
            name="Next Steps",
            value=(
                "1. Assign role Admin ke diri sendiri\n"
                "2. Assign role Dosen ke dosen-dosen\n"
                "3. Gunakan /set-relator untuk assign PIC kelas\n"
                "4. Mahasiswa baru ketik /register di #registrasi"
            ),
            inline=False,
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        logger.info(
            f"Server setup completed by {interaction.user.id}: "
            f"roles={roles_created}, channels={channels_created}"
        )
    
    @app_commands.command(
        name="set-relator",
        description="Assign dosen sebagai relator (PIC) kelas",
    )
    @app_commands.checks.has_role("Admin")
    async def set_relator(self, interaction: discord.Interaction):
        """Set relator using dropdown selection."""
        view = SetRelatorViewV2()
        
        # Load options from database
        await view.class_select.fetch_options()
        await view.dosen_select.fetch_options(interaction.guild)
        
        # Check if options available
        if not view.class_select.options:
            await interaction.response.send_message(
                "❌ Tidak ada kelas yang tersedia. "
                "Buat kelas terlebih dahulu dengan membuat channel kelas.",
                ephemeral=True,
            )
            return
        
        if not view.dosen_select.options:
            await interaction.response.send_message(
                "❌ Tidak ada dosen yang tersedia. "
                "Assign role Dosen ke dosen terlebih dahulu.",
                ephemeral=True,
            )
            return
        
        embed = discord.Embed(
            title="📝 Set Relator (PIC Kelas)",
            description=(
                "Pilih kelas dan dosen dari dropdown di bawah:\n\n"
                "1. **Pilih Kelas** — Kelas yang akan diberikan relator\n"
                "2. **Pilih Dosen** — Dosen yang akan ditugaskan\n"
                "3. **Klik Konfirmasi** — Untuk menyelesaikan"
            ),
            color=discord.Color.blue(),
        )
        
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
        )
        
        # Wait for view to complete
        await view.wait()
        
        if view.result == "confirm" and view.selected_class and view.selected_dosen:
            # Process the assignment
            await self._process_set_relator(
                interaction,
                view.selected_class,
                view.selected_dosen,
            )
    
    async def _process_set_relator(
        self,
        interaction: discord.Interaction,
        class_channel: ClassChannel,
        dosen: discord.Member,
    ):
        """Process relator assignment."""
        guild = interaction.guild
        
        # Check if class already has relator
        async with get_db() as db:
            existing = await db.execute(
                select(Relator).where(
                    Relator.class_channel_id == class_channel.id
                )
            )
            if existing.scalar_one_or_none():
                await interaction.followup.send(
                    f"❌ Kelas {class_channel.nama_kelas} sudah memiliki relator.",
                    ephemeral=True,
                )
                return
            
            # Create relator role
            relator_role_name = f"Relator-{class_channel.nama_kelas}"
            relator_role = discord.utils.get(guild.roles, name=relator_role_name)
            
            if not relator_role:
                relator_role = await guild.create_role(
                    name=relator_role_name,
                    permissions=discord.Permissions(0),
                    reason=f"Relator role for {class_channel.nama_kelas}",
                )
            
            # Assign role to dosen
            await dosen.add_roles(relator_role)
            
            # Update channel permissions
            channel = guild.get_channel(int(class_channel.channel_id))
            if channel:
                await channel.set_permissions(
                    relator_role,
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                    attach_files=True,
                    embed_links=True,
                )
            
            # Save to database
            relator = Relator(
                dosen_discord_id=str(dosen.id),
                dosen_nama=dosen.display_name,
                class_channel_id=class_channel.id,
                assigned_by=str(interaction.user.id),
            )
            db.add(relator)
            await db.commit()
        
        # Confirm
        embed = discord.Embed(
            title="✅ Relator Ditugaskan",
            description=(
                f"{dosen.mention} ditugaskan sebagai relator "
                f"kelas {class_channel.nama_kelas}"
            ),
            color=discord.Color.green(),
        )
        embed.add_field(name="Kelas", value=class_channel.nama_kelas, inline=True)
        embed.add_field(name="Relator", value=dosen.mention, inline=True)
        embed.add_field(
            name="Channel",
            value=f"<#{class_channel.channel_id}>",
            inline=True,
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        # DM dosen
        try:
            await dosen.send(
                f"🎓 Anda ditugaskan sebagai relator kelas "
                f"{class_channel.nama_kelas}\n\n"
                f"Channel: <#{class_channel.channel_id}>\n"
                f"Anda sekarang bisa mengakses channel tersebut."
            )
        except discord.Forbidden:
            logger.warning(f"Could not DM dosen {dosen.id}")
        
        logger.info(
            f"Relator assigned: {dosen.id} to {class_channel.nama_kelas} "
            f"by {interaction.user.id}"
        )
    
    async def _process_approval(
        self,
        interaction: discord.Interaction,
        view: ApproveStudentView,
    ):
        """Process student approval/rejection."""
        student = view.selected_student
        
        if view.result == "approve":
            # Approve student
            async with get_db() as db:
                # Check if NIM already used
                existing = await db.execute(
                    select(Student).where(Student.nim == student.nim)
                )
                if existing.scalar_one_or_none():
                    await interaction.followup.send(
                        f"❌ NIM {student.nim} sudah terdaftar.",
                        ephemeral=True,
                    )
                    return
                
                # Create student record
                new_student = Student(
                    discord_id=student.discord_id,
                    nim=student.nim,
                    nama_lengkap=student.nama_lengkap,
                    prodi=student.prodi,
                    angkatan=student.angkatan,
                    kelas=student.kelas,
                    no_wa=student.no_wa,
                    is_verified=True,
                    verified_by=str(interaction.user.id),
                    verified_at=datetime.utcnow(),
                )
                db.add(new_student)
                
                # Update pending status
                student.status = "approved"
                student.reviewed_by = str(interaction.user.id)
                student.reviewed_at = datetime.utcnow()
                
                await db.commit()
                
                # Get or create class channel
                class_channel_name = f"kelas-{student.kelas.lower()}-{student.prodi.lower()}"
                
                existing_class = await db.execute(
                    select(ClassChannel).where(
                        ClassChannel.nama_kelas == class_channel_name
                    )
                )
                class_channel = existing_class.scalar_one_or_none()
                
                if not class_channel:
                    # Create class channel
                    class_channel = await self._create_class_channel(
                        interaction.guild, student, db
                    )
                
                # Add student to class
                student_class = StudentClass(
                    student_id=new_student.id,
                    class_channel_id=class_channel.id,
                )
                db.add(student_class)
                await db.commit()
            
            # Assign roles
            member = interaction.guild.get_member(int(student.discord_id))
            if member:
                await self._assign_student_permissions(
                    interaction.guild, member, class_channel
                )
            
            # DM student
            member = interaction.guild.get_member(int(student.discord_id))
            if member:
                try:
                    await member.send(
                        f"🎉 Registrasi Anda disetujui!\n\n"
                        f"**NIM:** {student.nim}\n"
                        f"**Nama:** {student.nama_lengkap}\n"
                        f"**Prodi:** {student.prodi}\n"
                        f"**Kelas:** {student.kelas}\n\n"
                        f"Sekarang Anda bisa mengakses channel kelas Anda."
                    )
                except discord.Forbidden:
                    logger.warning(f"Could not DM student {student.discord_id}")
            
            await interaction.followup.send(
                f"✅ {student.nama_lengkap} berhasil di-approve.",
                ephemeral=True,
            )
            
        elif view.result == "reject":
            # Reject student
            async with get_db() as db:
                student.status = "rejected"
                student.reviewed_by = str(interaction.user.id)
                student.reviewed_at = datetime.utcnow()
                await db.commit()
            
            # DM student
            member = interaction.guild.get_member(int(student.discord_id))
            if member:
                try:
                    await member.send(
                        f"❌ Registrasi Anda ditolak.\n\n"
                        f"Silakan hubungi admin untuk informasi lebih lanjut."
                    )
                except discord.Forbidden:
                    logger.warning(f"Could not DM student {student.discord_id}")
            
            await interaction.followup.send(
                f"❌ {student.nama_lengkap} ditolak.",
                ephemeral=True,
            )
    
    async def _create_class_channel(
        self,
        guild: discord.Guild,
        student: PendingRegistration,
        db,
    ) -> ClassChannel:
        """Create a new class channel with role."""
        class_code = student.kelas
        prodi = student.prodi
        angkatan = student.angkatan
        
        # Channel name: kelas-a1-si
        channel_name = f"kelas-{class_code.lower()}-{prodi.lower()}"
        
        # Role name: Kelas-A1-SI
        role_name = f"Kelas-{class_code}-{prodi}"
        
        # Create role
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
            mata_kuliah="",
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
        
        # Add @Mahasiswa role
        mahasiswa_role = discord.utils.get(guild.roles, name="Mahasiswa")
        if mahasiswa_role:
            await member.add_roles(mahasiswa_role)
        
        # Ensure #umum is visible
        umum_channel = discord.utils.get(guild.channels, name="umum")
        if umum_channel and mahasiswa_role:
            await umum_channel.set_permissions(
                mahasiswa_role,
                read_messages=True,
                send_messages=True,
                read_message_history=True,
            )
    
    @app_commands.command(
        name="class-info",
        description="Lihat informasi kelas",
    )
    @app_commands.checks.has_role("Admin")
    async def class_info(self, interaction: discord.Interaction):
        """Display class information using dropdown."""
        view = ClassInfoView()
        
        # Load classes
        await view.class_select.fetch_options()
        
        if not view.class_select.options:
            await interaction.response.send_message(
                "❌ Tidak ada kelas yang tersedia.",
                ephemeral=True,
            )
            return
        
        embed = discord.Embed(
            title="📋 Class Info",
            description="Pilih kelas dari dropdown di bawah:",
            color=discord.Color.blue(),
        )
        
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
        )
    
    @app_commands.command(
        name="list-classes",
        description="Tampilkan semua kelas dengan relator",
    )
    @app_commands.checks.has_role("Admin")
    async def list_classes(self, interaction: discord.Interaction):
        """List all classes with relator."""
        await interaction.response.defer(ephemeral=True)
        
        async with get_db() as db:
            result = await db.execute(
                select(ClassChannel).order_by(
                    ClassChannel.prodi, ClassChannel.kelas_code
                )
            )
            classes = result.scalars().all()
        
        if not classes:
            await interaction.followup.send(
                "❌ Belum ada kelas yang dibuat.", ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="📚 Daftar Kelas",
            description=f"Total: {len(classes)} kelas",
            color=discord.Color.blue(),
        )
        
        for cls in classes:
            # Get relator info
            relator_info = "Belum ditugaskan"
            if cls.relator:
                relator_info = f"{cls.relator.dosen_nama} (<@{cls.relator.dosen_discord_id}>)"
            
            embed.add_field(
                name=f"{cls.nama_kelas} ({cls.prodi})",
                value=(
                    f"**Kelas:** {cls.kelas_code}\n"
                    f"**Angkatan:** {cls.angkatan}\n"
                    f"**Relator:** {relator_info}\n"
                    f"**Channel:** <#{cls.channel_id}>"
                ),
                inline=False,
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    """Add cog to bot."""
    await bot.add_cog(AdminCommands(bot))
