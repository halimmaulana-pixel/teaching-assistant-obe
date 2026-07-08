"""Main entry point for the bot — Railway deployment ready."""

import asyncio
import logging
import signal
import sys
from pathlib import Path

import discord
from discord.ext import commands

from .config import get_settings
from .database.engine import init_db, close_db

logger = logging.getLogger(__name__)

# Health check server for Railway
_health_server = None


async def start_health_server(port: int = 8080) -> None:
    """Start a simple HTTP health check server."""
    from aiohttp import web
    
    async def health_handler(request):
        return web.json_response({"status": "ok", "service": "teaching-assistant-bot"})
    
    app = web.Application()
    app.router.add_get("/", health_handler)
    app.router.add_get("/health", health_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health check server running on port {port}")


def setup_logging() -> None:
    """Set up logging configuration — console only for Railway."""
    settings = get_settings()
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    # Only add file handler in development
    if settings.environment == "development":
        handlers.append(logging.FileHandler("bot.log"))
    
    logging.basicConfig(
        level=getattr(logging, settings.bot_log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )


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


async def load_cogs(bot: commands.Bot) -> None:
    """Load all cog extensions."""
    cogs_path = Path(__file__).parent / "bot" / "commands"
    
    for cog_file in cogs_path.glob("*.py"):
        if cog_file.name.startswith("_"):
            continue
        
        cog_name = f"src.bot.commands.{cog_file.stem}"
        try:
            await bot.load_extension(cog_name)
            logger.info(f"Loaded extension: {cog_name}")
        except Exception as e:
            logger.error(f"Failed to load extension {cog_name}: {e}")


async def main() -> None:
    """Main entry point."""
    setup_logging()
    
    logger.info("Starting Teaching Assistant Bot...")
    
    # Start health check server FIRST (before anything else)
    import os
    port = int(os.getenv("PORT", 8080))
    try:
        await start_health_server(port)
        logger.info(f"Health check server started on port {port}")
    except Exception as e:
        logger.error(f"Failed to start health server: {e}")
        # Continue anyway - bot might still work
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # Continue anyway - might be able to connect later
    
    bot = create_bot()
    
    # Graceful shutdown handler
    shutdown_event = asyncio.Event()
    
    def signal_handler():
        logger.info("Received shutdown signal")
        shutdown_event.set()
    
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass
    
    @bot.event
    async def on_ready() -> None:
        """Called when the bot is ready."""
        logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
        logger.info("------")
        
        # Sync slash commands
        try:
            synced = await bot.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
    
    try:
        await load_cogs(bot)
        
        settings = get_settings()
        
        # Start bot and wait for shutdown signal
        bot_task = asyncio.create_task(bot.start(settings.discord_token))
        shutdown_task = asyncio.create_task(shutdown_event.wait())
        
        # Wait for either bot to stop or shutdown signal
        done, pending = await asyncio.wait(
            [bot_task, shutdown_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
    except KeyboardInterrupt:
        logger.info("Bot shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        # Cleanup
        try:
            await bot.close()
        except Exception:
            pass
        await close_db()
        logger.info("Bot shutdown complete")


def run() -> None:
    """Run the bot."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
