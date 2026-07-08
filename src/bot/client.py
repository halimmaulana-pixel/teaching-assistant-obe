"""Discord bot client configuration."""

import discord
from discord.ext import commands

from ..config import get_settings


def create_bot() -> commands.Bot:
    """Create and configure the Discord bot."""
    settings = get_settings()
    
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    
    bot = commands.Bot(
        command_prefix=settings.bot_prefix,
        intents=intents,
        application_id=settings.discord_application_id,
    )
    
    return bot
