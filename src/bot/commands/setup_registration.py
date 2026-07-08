"""Registration channel setup — Auto-post instructions when bot starts."""

import discord
from discord.ext import commands

from ...database.engine import get_db
from ...database.models import Student


class RegistrationChannelSetup(commands.Cog):
    """Setup registration channel with instructions."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Post registration instructions to #registrasi on bot startup."""
        # Wait a bit for bot to be fully ready
        await self.bot.wait_until_ready()
        
        for guild in self.bot.guilds:
            registrasi_channel = discord.utils.get(
                guild.channels, name="registrasi"
            )
            
            if not registrasi_channel:
                continue
            
            # Check if instructions already posted
            async for message in registrasi_channel.history(limit=50):
                if message.author == self.bot.user and "REGISTRASI MAHASISWA" in message.content:
                    return  # Already posted
            
            # Post instructions
            embed = self._create_registration_embed()
            await registrasi_channel.send(embed=embed)
    
    def _create_registration_embed(self) -> discord.Embed:
        """Create registration instruction embed."""
        embed = discord.Embed(
            title="🎓 REGISTRASI MAHASISWA FIKTI UMSU",
            description=(
                "Selamat datang di Server Discord FIKTI UMSU!\n\n"
                "Untuk mendaftar sebagai mahasiswa, silakan ikuti langkah di bawah."
            ),
            color=discord.Color.blue(),
        )
        
        # Langkah 1
        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            value="",
            inline=False,
        )
        
        embed.add_field(
            name="📋 LANGKAH 1: Ketik /register",
            value=(
                "Ketik `/register` di channel ini untuk membuka form registrasi."
            ),
            inline=False,
        )
        
        # Langkah 2
        embed.add_field(
            name="📝 LANGKAH 2: Isi Form Registrasi",
            value=(
                "Isi semua data dengan benar. **Perhatikan format inputan!**"
            ),
            inline=False,
        )
        
        # Format Inputan
        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            value="",
            inline=False,
        )
        
        embed.add_field(
            name="📌 FORMAT INPUTAN (WAJIB DIPERHATIKAN)",
            value="",
            inline=False,
        )
        
        # NIM
        embed.add_field(
            name="1️⃣ NIM",
            value=(
                "```\n"
                "Format: 10 digit angka\n"
                "Contoh: 2471110042\n"
                "         ^^\n"
                "         Angkatan 2024\n\n"
                "⚠️ HARUS 10 DIGIT, TANPA SPASI\n"
                "```\n"
                "**Penjelasan:**\n"
                "• 2 digit pertama = Angkatan (24 = tahun 2024)\n"
                "• 3 digit kedua = Kode Prodi (711=TI, 712=SI, 713=TI Baru)\n"
                "• 5 digit terakhir = Nomor Urut"
            ),
            inline=False,
        )
        
        # Nama
        embed.add_field(
            name="2️⃣ NAMA LENGKAP",
            value=(
                "```\n"
                "Format: Nama Lengkap sesuai KTP\n"
                "Contoh: Budi Santoso\n"
                "        Ahmad Hidayat\n"
                "        Sarah Putri Amelia\n\n"
                "⚠️ TANPA GELAR, HURUF BESAR/KECIL SESUAI KTP\n"
                "```\n"
                "**Contoh yang BENAR:**\n"
                "✅ Budi Santoso\n"
                "✅ Ahmad Hidayat\n\n"
                "**Contoh yang SALAH:**\n"
                "❌ budi santoso (huruf kecil semua)\n"
                "❌ BUDI SANTOSO (huruf besar semua)\n"
                "❌ Budi Santoso, S.Kom. (ada gelar)"
            ),
            inline=False,
        )
        
        # Prodi
        embed.add_field(
            name="3️⃣ PROGRAM STUDI",
            value=(
                "```\n"
                "Format: 2 huruf kode prodi\n"
                "Pilihan:\n"
                "  • TI = Teknik Informatika\n"
                "  • SI = Sistem Informasi\n"
                "  • SD = Seni Design\n\n"
                "Contoh: TI\n"
                "        SI\n"
                "        SD\n\n"
                "⚠️ HURUF KAPITAL, TANPA SPASI\n"
                "```\n"
                "**Daftar Kode Prodi:**\n"
                "```\n"
                "┌────────┬─────────────────────┐\n"
                "│ Kode   │ Program Studi       │\n"
                "├────────┼─────────────────────┤\n"
                "│ TI     │ Teknik Informatika  │\n"
                "│ SI     │ Sistem Informasi    │\n"
                "│ SD     │ Seni Design         │\n"
                "└────────┴─────────────────────┘\n"
                "```"
            ),
            inline=False,
        )
        
        # Kelas
        embed.add_field(
            name="4️⃣ KELAS",
            value=(
                "```\n"
                "Format: Huruf + Nomor\n"
                "Contoh: A1, B2, C1, D3\n\n"
                "Penjelasan:\n"
                "  • Huruf = Urut kelas (A, B, C, D, ...)\n"
                "  • Nomor = Urut paralel (1, 2, 3, ...)\n\n"
                "⚠️ HURUF KAPITAL + NOMOR, TANPA SPASI\n"
                "```\n"
                "**Contoh yang BENAR:**\n"
                "✅ A1 (Kelas A, Paralel 1)\n"
                "✅ B2 (Kelas B, Paralel 2)\n"
                "✅ C1 (Kelas C, Paralel 1)\n\n"
                "**Contoh yang SALAH:**\n"
                "❌ a1 (huruf kecil)\n"
                "❌ A 1 (ada spasi)\n"
                "❌ Kelas A1 (ada tulisan 'Kelas')"
            ),
            inline=False,
        )
        
        # No WA
        embed.add_field(
            name="5️⃣ NO. WHATSAPP (Opsional)",
            value=(
                "```\n"
                "Format: Nomor HP tanpa spasi\n"
                "Contoh: 081234567890\n"
                "        6281234567890\n\n"
                "⚠️ BISA DIKOSONKAN (tidak wajib)\n"
                "```\n"
                "**Tips:**\n"
                "• Gunakan nomor aktif\n"
                "• Bisa diisi nanti via DM admin"
            ),
            inline=False,
        )
        
        # Contoh Isian
        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            value="",
            inline=False,
        )
        
        embed.add_field(
            name="📝 CONTOH ISIAN LENGKAP",
            value=(
                "```\n"
                "┌─────────────────────────────────────┐\n"
                "│  📝 REGISTRASI MAHASISWA            │\n"
                "│                                     │\n"
                "│  NIM: 2471110042                   │\n"
                "│  Nama: Budi Santoso                 │\n"
                "│  Prodi: TI                          │\n"
                "│  Kelas: A1                          │\n"
                "│  No WA: 081234567890               │\n"
                "│                                     │\n"
                "│  [Cancel]  [Submit]                 │\n"
                "└─────────────────────────────────────┘\n"
                "```"
            ),
            inline=False,
        )
        
        # Setelah Submit
        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            value="",
            inline=False,
        )
        
        embed.add_field(
            name="✅ SETELAH SUBMIT",
            value=(
                "1. Bot akan memvalidasi data Anda\n"
                "2. Jika valid, data dikirim ke admin untuk diverifikasi\n"
                "3. Tunggu persetujuan admin di channel #admin\n"
                "4. Setelah disetujui, Anda akan mendapat notifikasi\n"
                "5. Anda akan otomatis masuk ke channel kelas Anda"
            ),
            inline=False,
        )
        
        # Peringatan
        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            value="",
            inline=False,
        )
        
        embed.add_field(
            name="⚠️ PENTING",
            value=(
                "• **NIM harus benar** — NIM akan digunakan untuk semua penilaian\n"
                "• **Kelas harus sesuai** — Anda hanya bisa akses channel kelas Anda\n"
                "• **Data tidak bisa diubah** setelah disetujui admin\n"
                "• **1 NIM = 1 Akun** — Tidak boleh daftar dua kali"
            ),
            inline=False,
        )
        
        # Quick Start
        embed.add_field(
            name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            value="",
            inline=False,
        )
        
        embed.add_field(
            name="🚀 MULAI SEKARANG",
            value=(
                "Ketik `/register` di bawah untuk memulai registrasi!"
            ),
            inline=False,
        )
        
        embed.set_footer(
            text="FIKTi UMSU | Teaching Assistant Bot v1.0",
            icon_url="https://umsu.ac.id/wp-content/uploads/2020/01/logo-umsu.png",
        )
        
        return embed


async def setup(bot: commands.Bot):
    """Add cog to bot."""
    await bot.add_cog(RegistrationChannelSetup(bot))
