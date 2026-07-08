"""Admin commands — Server setup and management with dropdowns."""

import logging

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from ...config import get_settings
from ...database.engine import get_db
from ...database.models import ClassChannel, Relator
from ..views.select_views import SetRelatorViewV2, ClassInfoView

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

        admin_role = discord.utils.get(guild.roles, name="Admin")
        if not admin_role:
            admin_role = await guild.create_role(
                name="Admin",
                permissions=discord.Permissions.all(),
                reason="Server admin role",
            )
            roles_created.append("Admin")

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

        # #registrasi - for new students (visible to everyone)
        registrasi_channel = discord.utils.get(guild.channels, name="registrasi")
        if not registrasi_channel:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    read_messages=True, send_messages=True
                ),
            }
            registrasi_channel = await guild.create_text_channel(
                "registrasi",
                overwrites=overwrites,
                topic="Registrasi mahasiswa baru - Ketik /register",
                reason="Registration channel",
            )
            channels_created.append("#registrasi")

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
                    read_messages=True, send_messages=False
                ),
                dosen_role: discord.PermissionOverwrite(
                    read_messages=True, send_messages=True
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

        # #admin - admin only
        admin_channel = discord.utils.get(guild.channels, name="admin")
        if not admin_channel:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                mahasiswa_role: discord.PermissionOverwrite(read_messages=False),
                dosen_role: discord.PermissionOverwrite(
                    read_messages=True, send_messages=True
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
                "4. Mahasiswa baru ketik /register di #registrasi\n"
                "   → Langsung auto-approved, tidak perlu persetujuan admin"
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

        await view.class_select.fetch_options()
        await view.dosen_select.fetch_options(interaction.guild)

        if not view.class_select.options:
            await interaction.response.send_message(
                "❌ Tidak ada kelas yang tersedia. "
                "Kelas akan otomatis dibuat saat mahasiswa pertama mendaftar.",
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
            embed=embed, view=view, ephemeral=True
        )

        await view.wait()

        if view.result == "confirm" and view.selected_class and view.selected_dosen:
            await self._process_set_relator(
                interaction, view.selected_class, view.selected_dosen
            )

    async def _process_set_relator(
        self,
        interaction: discord.Interaction,
        class_channel: ClassChannel,
        dosen: discord.Member,
    ):
        """Process relator assignment."""
        guild = interaction.guild

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

            relator_role_name = f"Relator-{class_channel.nama_kelas}"
            relator_role = discord.utils.get(guild.roles, name=relator_role_name)

            if not relator_role:
                relator_role = await guild.create_role(
                    name=relator_role_name,
                    permissions=discord.Permissions(0),
                    reason=f"Relator role for {class_channel.nama_kelas}",
                )

            await dosen.add_roles(relator_role)

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

            relator = Relator(
                dosen_discord_id=str(dosen.id),
                dosen_nama=dosen.display_name,
                class_channel_id=class_channel.id,
                assigned_by=str(interaction.user.id),
            )
            db.add(relator)
            await db.commit()

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

    @app_commands.command(
        name="class-info",
        description="Lihat informasi kelas",
    )
    @app_commands.checks.has_role("Admin")
    async def class_info(self, interaction: discord.Interaction):
        """Display class information using dropdown."""
        view = ClassInfoView()
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
            embed=embed, view=view, ephemeral=True
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
                "❌ Belum ada kelas yang dibuat. Kelas akan otomatis dibuat saat mahasiswa mendaftar.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="📚 Daftar Kelas",
            description=f"Total: {len(classes)} kelas",
            color=discord.Color.blue(),
        )

        for cls in classes:
            relator_info = "Belum ditugaskan"
            if cls.relator:
                relator_info = (
                    f"{cls.relator.dosen_nama} (<@{cls.relator.dosen_discord_id}>)"
                )

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
