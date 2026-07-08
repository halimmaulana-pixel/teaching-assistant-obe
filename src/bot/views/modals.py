"""Modal forms for Discord interactions."""

import discord
from discord import ui


class SubmissionModal(ui.Modal, title="Submit Tugas"):
    """Modal for submitting assignments."""
    
    google_drive_link = ui.TextInput(
        label="Link Google Drive",
        placeholder="https://drive.google.com/file/d/...",
        required=False,
        style=discord.TextStyle.short
    )
    
    notes = ui.TextInput(
        label="Catatan",
        placeholder="Catatan untuk dosen (opsional)",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=500
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        await interaction.response.send_message(
            "✅ Tugas berhasil dikirim!",
            ephemeral=True
        )
    
    async def on_error(self, interaction: discord.Interaction, error: Exception):
        """Handle modal error."""
        await interaction.response.send_message(
            f"❌ Error: {str(error)}",
            ephemeral=True
        )


class GradingModal(ui.Modal, title="Grade Tugas"):
    """Modal for grading assignments."""
    
    score = ui.TextInput(
        label="Skor (0-100)",
        placeholder="85",
        required=True,
        style=discord.TextStyle.short,
        max_length=3
    )
    
    feedback = ui.TextInput(
        label="Feedback",
        placeholder="Feedback untuk mahasiswa",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=1000
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        try:
            score = int(self.score.value)
            if not 0 <= score <= 100:
                raise ValueError("Score must be between 0 and 100")
        except ValueError:
            await interaction.response.send_message(
                "❌ Skor harus antara 0-100",
                ephemeral=True
            )
            return
        
        await interaction.response.send_message(
            f"✅ Tugas dinilai: {score}",
            ephemeral=True
        )
    
    async def on_error(self, interaction: discord.Interaction, error: Exception):
        """Handle modal error."""
        await interaction.response.send_message(
            f"❌ Error: {str(error)}",
            ephemeral=True
        )


class ExamAnswerModal(ui.Modal, title="Jawab Soal"):
    """Modal for answering exam questions."""
    
    answer = ui.TextInput(
        label="Jawaban",
        placeholder="Masukkan jawaban Anda",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=2000
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        await interaction.response.send_message(
            "✅ Jawaban tersimpan!",
            ephemeral=True
        )
    
    async def on_error(self, interaction: discord.Interaction, error: Exception):
        """Handle modal error."""
        await interaction.response.send_message(
            f"❌ Error: {str(error)}",
            ephemeral=True
        )
