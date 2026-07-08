"""Event handlers for the bot."""

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
        """Handle new member joining the server."""
        logger.info(f"New member joined: {member.id} ({member.display_name})")
        
        # Check if member already has Mahasiswa role
        mahasiswa_role = discord.utils.get(member.guild.roles, name="Mahasiswa")
        if mahasiswa_role in member.roles:
            return  # Already registered
        
        # Find registrasi channel
        registrasi_channel = discord.utils.get(
            member.guild.channels, name="registrasi"
        )
        
        if registrasi_channel:
            # Send welcome message to registrasi channel
            embed = discord.Embed(
                title="👋 Selamat Datang!",
                description=(
                    f"Selamat datang di Server FIKTI UMSU, {member.mention}!\n\n"
                    "Untuk mendaftar sebagai mahasiswa, silakan ketik:\n"
                    "```\n/register\n```\n\n"
                    "Anda akan diminta mengisi data:\n"
                    "• NIM (10 digit)\n"
                    "• Nama Lengkap\n"
                    "• Program Studi (TI/SI/SD)\n"
                    "• Kelas (contoh: A1, B2)\n"
                    "• No. WhatsApp (opsional)\n\n"
                    "Setelah registrasi, admin akan memverifikasi data Anda."
                ),
                color=discord.Color.blue(),
            )
            embed.set_thumbnail(
                url=member.display_avatar.url
                if member.display_avatar
                else None
            )
            
            await registrasi_channel.send(embed=embed)
        
        # DM welcome message
        try:
            await member.send(
                f"👋 Selamat datang di Server FIKTI UMSU!\n\n"
                f"Untuk mendaftar, silakan join channel #registrasi di server "
                f"dan ketik `/register`.\n\n"
                f"Anda akan diminta mengisi data mahasiswa Anda."
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
            pass  # Ignore unknown commands
        else:
            logger.error(f"Command error: {error}", exc_info=True)
            await ctx.send(
                "❌ Terjadi kesalahan saat menjalankan perintah.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    """Add cog to bot."""
    await bot.add_cog(EventHandlers(bot))
