"""Registration commands — Auto-approve, instant channel access."""

import re
import logging
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from ...config import get_settings
from ...database.engine import get_db
from ...database.models import Student, ClassChannel, StudentClass

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
        """Handle form submission — auto-approve and assign to class."""
        await interaction.response.defer(ephemeral=True)

        nim_value = self.nim.value.strip()
        prodi_value = self.prodi.value.strip().upper()
        kelas_value = self.kelas.value.strip().upper()
        nama_value = self.nama_lengkap.value.strip()
        no_wa_value = self.no_wa.value.strip() if self.no_wa.value else None

        # --- Validation ---
        if not re.match(r"^\d{10}$", nim_value):
            await interaction.followup.send(
                "❌ **NIM tidak valid!**\n\n"
                "Format: 10 digit angka tanpa spasi\n"
                "Contoh: `2471110042`\n\n"
                "• 2 digit pertama = Angkatan (24 = 2024)\n"
                "• 3 digit kedua = Kode Prodi (711=TI, 712=SI, 713=TI Baru)\n"
                "• 5 digit terakhir = Nomor Urut",
                ephemeral=True,
            )
            return

        if prodi_value not in ["TI", "SI", "SD"]:
            await interaction.followup.send(
                "❌ **Program Studi tidak valid!**\n\n"
                "Pilihan: `TI` (Teknik Informatika) / `SI` (Sistem Informasi) / `SD` (Seni Design)",
                ephemeral=True,
            )
            return

        if not re.match(r"^[A-Z]\d{1,2}$", kelas_value):
            await interaction.followup.send(
                "❌ **Format kelas tidak valid!**\n\n"
                "Format: Huruf + Nomor (huruf kapital)\n"
                "Contoh: `A1`, `B2`, `C1`\n\n"
                "Yang salah: `a1` (kecil), `A 1` (spasi), `Kelas A1`",
                ephemeral=True,
            )
            return

        angkatan = int(nim_value[:2])

        # --- Check duplicates ---
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

            existing_discord = await db.execute(
                select(Student).where(
                    Student.discord_id == str(interaction.user.id)
                )
            )
            if existing_discord.scalar_one_or_none():
                await interaction.followup.send(
                    "❌ Anda sudah terdaftar sebagai mahasiswa.",
                    ephemeral=True,
                )
                return

            # --- Create student record (auto-approved) ---
            student = Student(
                discord_id=str(interaction.user.id),
                nim=nim_value,
                nama_lengkap=nama_value,
                prodi=prodi_value,
                angkatan=angkatan,
                kelas=kelas_value,
                no_wa=no_wa_value,
                is_verified=True,
                verified_by="auto",
                verified_at=datetime.utcnow(),
            )
            db.add(student)
            await db.commit()

            # --- Get or create class channel ---
            class_channel_name = f"kelas-{kelas_value.lower()}-{prodi_value.lower()}"

            existing_class = await db.execute(
                select(ClassChannel).where(
                    ClassChannel.nama_kelas == class_channel_name
                )
            )
            class_channel = existing_class.scalar_one_or_none()

            if not class_channel:
                class_channel = await self._create_class_channel(
                    interaction.guild, prodi_value, kelas_value, angkatan, db
                )

            # --- Add student to class ---
            student_class = StudentClass(
                student_id=student.id,
                class_channel_id=class_channel.id,
            )
            db.add(student_class)
            await db.commit()

        # --- Assign roles and permissions ---
        await self._assign_student_permissions(
            interaction.guild, interaction.user, class_channel
        )

        # --- Success embed with wizard next steps ---
        channel_mention = f"<#{class_channel.channel_id}>"

        embed = discord.Embed(
            title="🎉 Registrasi Berhasil! Selamat Datang!",
            description=(
                f"Halo **{nama_value}**! Anda sudah resmi terdaftar.\n\n"
                "---\n\n"
                "## ✅ Data Anda\n\n"
                f"```"
                f"NIM    : {nim_value}\n"
                f"Nama   : {nama_value}\n"
                f"Prodi  : {prodi_value}\n"
                f"Kelas  : {kelas_value}\n"
                f"No WA  : {no_wa_value or '-'}"
                f"```\n\n"
                "---\n\n"
                "## 🚀 Langkah Selanjutnya\n\n"
                f"Anda sudah otomatis masuk ke channel kelas: {channel_mention}\n\n"
                "Berikut channel yang bisa Anda akses:\n\n"
                f"📌 **{channel_mention}** — Channel kelas Anda\n"
                "📌 **#umum** — Diskusi dengan semua mahasiswa\n"
                "📌 **#pengumuman** — Informasi dari dosen & admin\n\n"
                "---\n\n"
                "## 💡 Tips\n\n"
                "• Baca pengumuman di **#pengumuman** untuk jadwal kuliah\n"
                "• Gunakan **#umum** untuk diskusi umum\n"
                "• Gunakan channel kelas untuk tugas dan diskusi kelas\n"
                "• Jika ada pertanyaan, tanyakan di channel kelas Anda\n\n"
                "---\n\n"
                f"**Mulai eksplor server!** Klik {channel_mention} untuk masuk ke kelas Anda. 🎓"
            ),
            color=discord.Color.green(),
        )
        embed.set_thumbnail(
            url=interaction.user.display_avatar.url
            if interaction.user.display_avatar
            else None
        )
        embed.set_footer(
            text="FIKTi UMSU • Teaching Assistant Bot",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

        # Notify admin channel (informational only)
        admin_channel = discord.utils.get(interaction.guild.channels, name="admin")
        if admin_channel:
            info_embed = discord.Embed(
                title="🆕 Mahasiswa Baru Terdaftar",
                description=f"{interaction.user.mention} sudah terdaftar otomatis.",
                color=discord.Color.green(),
            )
            info_embed.add_field(name="NIM", value=nim_value, inline=True)
            info_embed.add_field(name="Nama", value=nama_value, inline=True)
            info_embed.add_field(name="Prodi", value=prodi_value, inline=True)
            info_embed.add_field(name="Kelas", value=kelas_value, inline=True)
            info_embed.add_field(name="Channel", value=channel_mention, inline=True)
            info_embed.set_footer(text=f"Auto-approved • ID: {interaction.user.id}")

            await admin_channel.send(embed=info_embed)

        logger.info(
            f"Auto-approved registration: {nim_value} by {interaction.user.id} → {class_channel_name}"
        )

    async def _create_class_channel(
        self,
        guild: discord.Guild,
        prodi: str,
        kelas_code: str,
        angkatan: int,
        db,
    ) -> ClassChannel:
        """Create a new class channel with role."""
        channel_name = f"kelas-{kelas_code.lower()}-{prodi.lower()}"
        role_name = f"Kelas-{kelas_code}-{prodi}"

        # Create role
        class_role = await guild.create_role(
            name=role_name,
            permissions=discord.Permissions(0),
            reason=f"Auto-created for class {kelas_code} {prodi}",
        )

        # Channel permissions
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

        # Find category
        category = None
        for ch in guild.categories:
            if prodi.upper() in ch.name.upper():
                category = ch
                break

        channel = await guild.create_text_channel(
            channel_name,
            overwrites=overwrites,
            category=category,
            topic=f"Kelas {kelas_code} {prodi} Angkatan {angkatan}",
            reason=f"Auto-created for class {kelas_code} {prodi}",
        )

        # Save to database
        class_channel = ClassChannel(
            nama_kelas=channel_name,
            mata_kuliah="",
            prodi=prodi,
            angkatan=angkatan,
            kelas_code=kelas_code,
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

        # Ensure #umum is visible for Mahasiswa
        umum_channel = discord.utils.get(guild.channels, name="umum")
        if umum_channel and mahasiswa_role:
            await umum_channel.set_permissions(
                mahasiswa_role,
                read_messages=True,
                send_messages=True,
                read_message_history=True,
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


async def setup(bot: commands.Bot):
    """Add cog to bot."""
    await bot.add_cog(RegistrationCommands(bot))
