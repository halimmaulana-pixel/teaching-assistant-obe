"""Button components for Discord interactions."""

import discord
from discord import ui


class SubmitButton(ui.Button):
    """Button for submitting assignments."""
    
    def __init__(self, assignment_id: str):
        super().__init__(
            label="Submit Tugas",
            style=discord.ButtonStyle.primary,
            custom_id=f"submit_{assignment_id}"
        )
        self.assignment_id = assignment_id
    
    async def callback(self, interaction: discord.Interaction):
        """Handle button click."""
        from .modals import SubmissionModal
        modal = SubmissionModal()
        await interaction.response.send_modal(modal)


class GradeButton(ui.Button):
    """Button for grading submissions."""
    
    def __init__(self, submission_id: str):
        super().__init__(
            label="Grade",
            style=discord.ButtonStyle.success,
            custom_id=f"grade_{submission_id}"
        )
        self.submission_id = submission_id
    
    async def callback(self, interaction: discord.Interaction):
        """Handle button click."""
        from .modals import GradingModal
        modal = GradingModal()
        await interaction.response.send_modal(modal)


class ViewSubmissionButton(ui.Button):
    """Button for viewing submission details."""
    
    def __init__(self, submission_id: str):
        super().__init__(
            label="View",
            style=discord.ButtonStyle.secondary,
            custom_id=f"view_{submission_id}"
        )
        self.submission_id = submission_id
    
    async def callback(self, interaction: discord.Interaction):
        """Handle button click."""
        await interaction.response.send_message(
            f"📄 Viewing submission {self.submission_id}",
            ephemeral=True
        )


class JoinGroupButton(ui.Button):
    """Button for joining a group."""
    
    def __init__(self, group_id: str):
        super().__init__(
            label="Join Kelompok",
            style=discord.ButtonStyle.primary,
            custom_id=f"join_group_{group_id}"
        )
        self.group_id = group_id
    
    async def callback(self, interaction: discord.Interaction):
        """Handle button click."""
        await interaction.response.send_message(
            f"✅ Bergabung dengan kelompok {self.group_id}",
            ephemeral=True
        )


class StartExamButton(ui.Button):
    """Button for starting an exam."""
    
    def __init__(self, exam_id: str):
        super().__init__(
            label="Mulai Ujian",
            style=discord.ButtonStyle.danger,
            custom_id=f"start_exam_{exam_id}"
        )
        self.exam_id = exam_id
    
    async def callback(self, interaction: discord.Interaction):
        """Handle button click."""
        await interaction.response.send_message(
            f"📝 Memulai ujian {self.exam_id}...",
            ephemeral=True
        )


class SubmitExamButton(ui.Button):
    """Button for submitting an exam."""
    
    def __init__(self, exam_id: str):
        super().__init__(
            label="Selesai",
            style=discord.ButtonStyle.success,
            custom_id=f"submit_exam_{exam_id}"
        )
        self.exam_id = exam_id
    
    async def callback(self, interaction: discord.Interaction):
        """Handle button click."""
        await interaction.response.send_message(
            f"✅ Ujian {self.exam_id} selesai!",
            ephemeral=True
        )
