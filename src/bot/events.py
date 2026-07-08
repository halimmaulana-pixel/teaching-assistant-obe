"""Event handlers — Welcome wizard for new members."""

import logging

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


class EventHandlers(commands.Cog):
    """Event handlers for bot events."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Show welcome wizard when new member joins."""
        logger.info(f"New member joined: {member.id} ({member.display_name})")

        # Check if already registered
        mahasiswa_role = discord.utils.get(member.guild.roles, name="Mahasiswa")
        if mahasiswa_role in member.roles:
            return

        # Find registrasi channel
        registrasi_channel = discord.utils.get(
            member.guild.channels, name="registrasi"
        )

        if registrasi_channel:
            embed = discord.Embed(
                title="🎓 Selamat Datang di Server FIKTI UMSU!",
                description=(
                    f"Halo {member.mention}! 👋\n\n"
                    "Selamat datang di server resmi **Fakultas Ilmu Komputer dan Teknologi Informasi** "
                    "Universitas Muhammadiyah Sumatera Utara.\n\n"
                    "---\n\n"
                    "## 📋 Langkah Selanjutnya\n\n"
                    "Untuk bisa mengakses channel kelas dan materi perkuliahan, "
                    "silakan ikuti langkah berikut:\n\n"
                    "### Step 1️⃣ — Ketik `/register`\n"
                    "Ketik perintah `/register` di channel ini.\n\n"
                    "### Step 2️⃣ — Isi Formulir Registrasi\n"
                    "Isi data Anda di modal yang muncul:\n"
                    "• **NIM** — 10 digit angka (contoh: `2471110042`)\n"
                    "• **Nama Lengkap** — Sesuai KTP\n"
                    "• **Program Studi** — `TI` / `SI` / `SD`\n"
                    "• **Kelas** — Huruf + Nomor (contoh: `A1`, `B2`)\n"
                    "• **No. WhatsApp** — (opsional)\n\n"
                    "### Step 3️⃣ — Langsung Masuk Kelas!\n"
                    "Setelah mengisi formulir, Anda akan **otomatis** masuk ke channel kelas Anda. "
                    "Tidak perlu menunggu persetujuan admin! ✅\n\n"
                    "---\n\n"
                    "## 💡 Info Penting\n\n"
                    "• **Channel Kelas** — Hanya Anda dan teman sekelas yang bisa melihat\n"
                    "• **#umum** — Channel diskusi untuk semua mahasiswa\n"
                    "• **#pengumuman** — Informasi dari dosen dan admin\n\n"
                    "## ⚠️ Catatan\n\n"
                    "• Pastikan NIM dan data Anda **benar** sebelum submit\n"
                    "• Satu akun Discord hanya bisa registrasi **satu kali**\n"
                    "• Jika ada kendala, hubungi admin di channel **#admin**\n\n"
                    "---\n\n"
                    "**Ketik `/register` untuk memulai!** 👇"
                ),
                color=discord.Color.blue(),
            )
            embed.set_thumbnail(
                url=member.display_avatar.url if member.display_avatar else None
            )
            embed.set_footer(
                text="FIKTi UMSU • Teaching Assistant Bot",
                icon_url=member.guild.icon.url if member.guild.icon else None,
            )

            await registrasi_channel.send(embed=embed)

        # DM welcome
        try:
            await member.send(
                f"👋 Selamat datang di Server FIKTI UMSU!\n\n"
                f"Untuk mendaftar sebagai mahasiswa:\n"
                f"1. Buka channel **#registrasi** di server\n"
                f"2. Ketik `/register`\n"
                f"3. Isi formulir yang muncul\n"
                f"4. Anda akan otomatis masuk ke channel kelas!\n\n"
                f"Tidak perlu menunggu persetujuan admin. 🎉"
            )
        except discord.Forbidden:
            logger.warning(f"Could not DM new member {member.id}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Handle member leaving the server."""
        logger.info(f"Member left: {member.id} ({member.display_name})")

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ):
        """Handle command errors."""
        if isinstance(error, commands.MissingRole):
            await ctx.send(
                f"❌ Anda tidak memiliki role yang diperlukan: {error.missing_role}",
                ephemeral=True,
            )
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(
                "❌ Anda tidak memiliki izin untuk menjalankan perintah ini.",
                ephemeral=True,
            )
        elif isinstance(error, commands.CommandNotFound):
            pass
        else:
            logger.error(f"Command error: {error}", exc_info=True)
            await ctx.send(
                "❌ Terjadi kesalahan saat menjalankan perintah.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    """Add cog to bot."""
    await bot.add_cog(EventHandlers(bot))
