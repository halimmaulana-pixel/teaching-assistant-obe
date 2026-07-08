"""Group commands for group management and peer assessment."""

import logging
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands

from ...config import get_settings
from ...database import (
    User,
    Assignment,
    Submission,
    get_db,
)

logger = logging.getLogger(__name__)


class GroupCommands(commands.Cog):
    """Group commands for group management."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings = get_settings()
    
    @app_commands.command(name="group-create", description="Buat kelompok")
    @app_commands.describe(
        assignment_id="ID Tugas",
        members="Anggota kelompok (mention, pisahkan dengan koma)"
    )
    async def group_create(
        self,
        interaction: discord.Interaction,
        assignment_id: str,
        members: str
    ):
        """Create group for assignment."""
        await interaction.response.defer(ephemeral=True)
        
        # Parse member mentions
        member_ids = []
        for member_str in members.split(","):
            member_str = member_str.strip()
            if member_str.startswith("<@") and member_str.endswith(">"):
                user_id = member_str[2:-1].replace("!", "")
                member_ids.append(user_id)
            else:
                await interaction.followup.send(
                    f"❌ Format member tidak valid: {member_str}",
                    ephemeral=True
                )
                return
        
        # Add leader
        member_ids.append(str(interaction.user.id))
        
        # Validate member count
        if len(member_ids) < 2:
            await interaction.followup.send(
                "❌ Minimal 2 anggota kelompok.",
                ephemeral=True
            )
            return
        
        if len(member_ids) > 5:
            await interaction.followup.send(
                "❌ Maksimal 5 anggota kelompok.",
                ephemeral=True
            )
            return
        
        async for db in get_db():
            # Get assignment
            assignment = await db.query(Assignment).filter(
                Assignment.id == assignment_id
            ).first()
            
            if not assignment:
                await interaction.followup.send(
                    "❌ Tugas tidak ditemukan.",
                    ephemeral=True
                )
                return
            
            if not assignment.kelompok_mode:
                await interaction.followup.send(
                    "❌ Tugas ini bukan tugas kelompok.",
                    ephemeral=True
                )
                return
            
            # Check if any member already in a group
            for member_id in member_ids:
                existing = await db.query(Submission).filter(
                    Submission.assignment_id == assignment_id,
                    Submission.student_id == member_id,
                    Submission.group_id.isnot(None)
                ).first()
                
                if existing:
                    await interaction.followup.send(
                        f"❌ Anggota <@{member_id}> sudah ada di kelompok lain.",
                        ephemeral=True
                    )
                    return
            
            # Create group submission
            submission = Submission(
                assignment_id=assignment_id,
                student_id=str(interaction.user.id),
                group_id=str(interaction.user.id),  # Use leader as group ID
                status="draft",
            )
            db.add(submission)
            await db.commit()
        
        embed = discord.Embed(
            title="✅ Kelompok Dibuat",
            description="Kelompok telah dibuat.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(
            name="Anggota",
            value=", ".join([f"<@{m}>" for m in member_ids]),
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        logger.info(f"Group created for assignment {assignment_id} by {interaction.user.id}")
    
    @app_commands.command(name="group-join", description="Join kelompok")
    @app_commands.describe(group_id="ID Kelompok (leader ID)")
    async def group_join(
        self,
        interaction: discord.Interaction,
        group_id: str
    ):
        """Join existing group."""
        await interaction.response.defer(ephemeral=True)
        
        async for db in get_db():
            # Get group submission
            group_submission = await db.query(Submission).filter(
                Submission.student_id == group_id,
                Submission.group_id.isnot(None)
            ).first()
            
            if not group_submission:
                await interaction.followup.send(
                    "❌ Kelompok tidak ditemukan.",
                    ephemeral=True
                )
                return
            
            # Check if already in a group
            existing = await db.query(Submission).filter(
                Submission.assignment_id == group_submission.assignment_id,
                Submission.student_id == str(interaction.user.id),
                Submission.group_id.isnot(None)
            ).first()
            
            if existing:
                await interaction.followup.send(
                    "❌ Anda sudah ada di kelompok lain.",
                    ephemeral=True
                )
                return
            
            # Create submission for this student
            submission = Submission(
                assignment_id=group_submission.assignment_id,
                student_id=str(interaction.user.id),
                group_id=group_id,
                status="draft",
            )
            db.add(submission)
            await db.commit()
        
        embed = discord.Embed(
            title="✅ Berhasil Join Kelompok",
            description="Anda telah bergabung dengan kelompok.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        logger.info(f"Student {interaction.user.id} joined group {group_id}")
    
    @app_commands.command(name="group-leave", description="Leave kelompok")
    async def group_leave(self, interaction: discord.Interaction):
        """Leave current group."""
        await interaction.response.defer(ephemeral=True)
        
        async for db in get_db():
            # Get user's group submission
            submission = await db.query(Submission).filter(
                Submission.student_id == str(interaction.user.id),
                Submission.group_id.isnot(None)
            ).first()
            
            if not submission:
                await interaction.followup.send(
                    "❌ Anda tidak ada di kelompok manapun.",
                    ephemeral=True
                )
                return
            
            # Check if user is leader
            if submission.student_id == str(interaction.user.id):
                await interaction.followup.send(
                    "❌ Leader tidak bisa leave kelompok. Gunakan `/group-dissolve`.",
                    ephemeral=True
                )
                return
            
            # Delete submission
            await db.delete(submission)
            await db.commit()
        
        embed = discord.Embed(
            title="✅ Keluar dari Kelompok",
            description="Anda telah keluar dari kelompok.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        logger.info(f"Student {interaction.user.id} left group")
    
    @app_commands.command(name="group-members", description="Lihat anggota kelompok")
    async def group_members(self, interaction: discord.Interaction):
        """View group members."""
        await interaction.response.defer(ephemeral=True)
        
        async for db in get_db():
            # Get user's group
            submission = await db.query(Submission).filter(
                Submission.student_id == str(interaction.user.id),
                Submission.group_id.isnot(None)
            ).first()
            
            if not submission:
                await interaction.followup.send(
                    "❌ Anda tidak ada di kelompok manapun.",
                    ephemeral=True
                )
                return
            
            # Get all members
            members = await db.query(Submission).filter(
                Submission.assignment_id == submission.assignment_id,
                Submission.group_id == submission.group_id
            ).all()
        
        embed = discord.Embed(
            title="👥 Anggota Kelompok",
            description=f"Kelompok untuk tugas",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        member_list = []
        for m in members:
            user = await self.bot.fetch_user(int(m.student_id))
            member_list.append(f"• {user.mention}")
        
        embed.add_field(
            name="Anggota",
            value="\n".join(member_list),
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)


class PeerAssessmentCommands(commands.Cog):
    """Peer assessment commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings = get_settings()
    
    @app_commands.command(name="peer-start", description="Mulai peer assessment")
    @app_commands.describe(assignment_id="ID Tugas")
    @app_commands.checks.has_role("Dosen")
    async def peer_start(
        self,
        interaction: discord.Interaction,
        assignment_id: str
    ):
        """Start peer assessment session."""
        await interaction.response.defer(ephemeral=True)
        
        # TODO: Implement peer assessment logic
        await interaction.followup.send(
            "⚠️ Fitur peer assessment akan segera hadir.",
            ephemeral=True
        )
    
    @app_commands.command(name="peer-submit", description="Submit penilaian peer")
    @app_commands.describe(
        scores="Skor untuk setiap anggota (format: @member:score, pisahkan dengan koma)",
        feedback="Feedback untuk kelompok"
    )
    async def peer_submit(
        self,
        interaction: discord.Interaction,
        scores: str,
        feedback: str = ""
    ):
        """Submit peer assessment."""
        await interaction.response.defer(ephemeral=True)
        
        # TODO: Implement peer assessment submission
        await interaction.followup.send(
            "⚠️ Fitur peer assessment akan segera hadir.",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    """Add cogs to bot."""
    await bot.add_cog(GroupCommands(bot))
    await bot.add_cog(PeerAssessmentCommands(bot))
