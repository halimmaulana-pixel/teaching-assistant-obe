"""Member join event handler."""

import logging
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from ...config import get_settings
from ...database import User, get_db

logger = logging.getLogger(__name__)


async def on_member_join(member: discord.Member):
    """Handle member join event."""
    settings = get_settings()
    
    logger.info(f"Member joined: {member.id} ({member.name})")
    
    # Send welcome DM
    try:
        embed = discord.Embed(
            title="🎓 Selamat Datang di FIKTI UMSU!",
            description=(
                f"Halo {member.mention}! 👋\n\n"
                "Selamat datang di server resmi FIKTI UMSU.\n"
                "Untuk mengakses semua channel, kamu perlu **verifikasi NIM**."
            ),
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(
            name="📋 Langkah Verifikasi",
            value=(
                "1. Pergi ke channel <#verifikasi>\n"
                "2. Ketik `/verify [NIM_KAMU]`\n"
                "3. Ikuti instruksi selanjutnya"
            ),
            inline=False
        )
        embed.add_field(
            name="⏰ Deadline",
            value="Verifikasi harus diselesaikan dalam **24 jam**.",
            inline=True
        )
        embed.add_field(
            name="❓ Masalah?",
            value="Hubungi admin di <#bantuan>",
            inline=True
        )
        
        await member.send(embed=embed)
        logger.info(f"Welcome DM sent to {member.id}")
    except discord.Forbidden:
        logger.warning(f"Could not send DM to {member.id}")
    
    # Log to database
    async for db in get_db():
        user = User(
            discord_id=str(member.id),
            is_verified=False,
            role="mahasiswa",
        )
        db.add(user)
        await db.commit()
    
    # Notify admin channel
    guild = member.guild
    admin_channel = discord.utils.get(guild.channels, name="admin-logs")
    
    if admin_channel:
        embed = discord.Embed(
            title="👤 Member Joined",
            description=f"{member.mention} ({member.name}) joined the server.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="ID", value=str(member.id), inline=True)
        embed.add_field(name="Created At", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        
        await admin_channel.send(embed=embed)
