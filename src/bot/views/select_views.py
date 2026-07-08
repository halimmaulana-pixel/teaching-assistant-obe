"""Combined views — Select menus + Action buttons."""

import logging
from typing import Optional

import discord
from discord import ui

from .selects import (
    ClassSelect,
    StudentSelect,
    RelatorSelect,
    MultiStudentSelect,
)

logger = logging.getLogger(__name__)


class SetRelatorView(ui.View):
    """View for /set-relator: Class dropdown + Relator dropdown + Confirm."""
    
    def __init__(self):
        super().__init__(timeout=120)
        self.selected_class = None
        self.selected_relator = None
        self.result = None
        
        # Add selects
        self.class_select = ClassSelect()
        self.relator_select = RelatorSelect()
        self.add_item(self.class_select)
        self.add_item(self.relator_select)
    
    @ui.button(label="✅ Konfirmasi", style=discord.ButtonStyle.success, row=2)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        """Handle confirm button."""
        if not self.selected_class or not self.selected_relator:
            await interaction.response.send_message(
                "❌ Pilih kelas dan relator terlebih dahulu!",
                ephemeral=True,
            )
            return
        
        self.result = "confirm"
        
        embed = discord.Embed(
            title="✅ Konfirmasi",
            description=(
                f"**Kelas:** {self.selected_class.nama_kelas}\n"
                f"**Relator:** {self.selected_relator.dosen_nama}\n\n"
                f"Apakah Anda yakin?"
            ),
            color=discord.Color.green(),
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        self.stop()
    
    @ui.button(label="❌ Batal", style=discord.ButtonStyle.secondary, row=2)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        """Handle cancel button."""
        self.result = "cancel"
        await interaction.response.send_message(
            "❌ Dibatalkan", ephemeral=True
        )
        self.stop()
    
    async def on_timeout(self):
        """Handle timeout."""
        logger.warning("SetRelatorView timed out")


class ApproveStudentView(ui.View):
    """View for /approve: Student dropdown + Approve/Reject buttons."""
    
    def __init__(self):
        super().__init__(timeout=120)
        self.selected_student = None
        self.result = None
        
        # Add select
        self.student_select = StudentSelect(status="pending")
        self.add_item(self.student_select)
    
    @ui.button(label="✅ Approve", style=discord.ButtonStyle.success, row=1)
    async def approve(self, interaction: discord.Interaction, button: ui.Button):
        """Handle approve button."""
        if not self.selected_student:
            await interaction.response.send_message(
                "❌ Pilih mahasiswa terlebih dahulu!",
                ephemeral=True,
            )
            return
        
        self.result = "approve"
        
        embed = discord.Embed(
            title="✅ Approve Mahasiswa",
            description=(
                f"**Nama:** {self.selected_student.nama_lengkap}\n"
                f"**NIM:** {self.selected_student.nim}\n"
                f"**Prodi:** {self.selected_student.prodi}\n"
                f"**Kelas:** {self.selected_student.kelas}\n\n"
                f"Apakah Anda yakin ingin approve?"
            ),
            color=discord.Color.green(),
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        self.stop()
    
    @ui.button(label="❌ Reject", style=discord.ButtonStyle.danger, row=1)
    async def reject(self, interaction: discord.Interaction, button: ui.Button):
        """Handle reject button."""
        if not self.selected_student:
            await interaction.response.send_message(
                "❌ Pilih mahasiswa terlebih dahulu!",
                ephemeral=True,
            )
            return
        
        self.result = "reject"
        
        embed = discord.Embed(
            title="❌ Reject Mahasiswa",
            description=(
                f"**Nama:** {self.selected_student.nama_lengkap}\n"
                f"**NIM:** {self.selected_student.nim}\n\n"
                f"Apakah Anda yakin ingin reject?"
            ),
            color=discord.Color.red(),
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        self.stop()
    
    async def on_timeout(self):
        """Handle timeout."""
        logger.warning("ApproveStudentView timed out")


class ClassInfoView(ui.View):
    """View for /class-info: Class dropdown + Info button."""
    
    def __init__(self):
        super().__init__(timeout=120)
        self.selected_class = None
        
        # Add select
        self.class_select = ClassSelect()
        self.add_item(self.class_select)
    
    @ui.button(label="📋 Lihat Info", style=discord.ButtonStyle.primary, row=1)
    async def info(self, interaction: discord.Interaction, button: ui.Button):
        """Handle info button."""
        if not self.selected_class:
            await interaction.response.send_message(
                "❌ Pilih kelas terlebih dahulu!",
                ephemeral=True,
            )
            return
        
        embed = discord.Embed(
            title=f"📋 Info Kelas: {self.selected_class.nama_kelas}",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="Mata Kuliah",
            value=self.selected_class.mata_kuliah or "-",
            inline=True,
        )
        embed.add_field(
            name="Prodi",
            value=self.selected_class.prodi,
            inline=True,
        )
        embed.add_field(
            name="Kelas",
            value=self.selected_class.kelas_code,
            inline=True,
        )
        embed.add_field(
            name="Angkatan",
            value=str(self.selected_class.angkatan),
            inline=True,
        )
        embed.add_field(
            name="Channel",
            value=f"<#{self.selected_class.channel_id}>"
            if self.selected_class.channel_id
            else "-",
            inline=True,
        )
        
        # Get relator info
        from ...database.engine import get_db
        from ...database.models import Relator
        
        async with get_db() as db:
            result = await db.execute(
                select(Relator).where(
                    Relator.class_channel_id == self.selected_class.id
                )
            )
            relator = result.scalar_one_or_none()
        
        embed.add_field(
            name="Relator",
            value=relator.dosen_nama if relator else "Belum ditugaskan",
            inline=True,
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        self.stop()


class BatchApproveView(ui.View):
    """View for batch approve: Multi-select students + action buttons."""
    
    def __init__(self, class_channel_id: Optional[int] = None):
        super().__init__(timeout=180)
        self.selected_students = []
        self.result = None
        
        # Add multi-select
        self.multi_select = MultiStudentSelect(class_channel_id=class_channel_id)
        self.add_item(self.multi_select)
    
    @ui.button(label="✅ Bulk Approve", style=discord.ButtonStyle.success, row=2)
    async def bulk_approve(self, interaction: discord.Interaction, button: ui.Button):
        """Handle bulk approve."""
        if not self.selected_students:
            await interaction.response.send_message(
                "❌ Pilih minimal 1 mahasiswa!",
                ephemeral=True,
            )
            return
        
        self.result = "bulk_approve"
        count = len(self.selected_students)
        
        await interaction.response.send_message(
            f"✅ {count} mahasiswa akan di-approve. Memproses...",
            ephemeral=True,
        )
        self.stop()
    
    @ui.button(label="❌ Bulk Reject", style=discord.ButtonStyle.danger, row=2)
    async def bulk_reject(self, interaction: discord.Interaction, button: ui.Button):
        """Handle bulk reject."""
        if not self.selected_students:
            await interaction.response.send_message(
                "❌ Pilih minimal 1 mahasiswa!",
                ephemeral=True,
            )
            return
        
        self.result = "bulk_reject"
        count = len(self.selected_students)
        
        await interaction.response.send_message(
            f"❌ {count} mahasiswa akan di-reject. Memproses...",
            ephemeral=True,
        )
        self.stop()
    
    async def on_timeout(self):
        """Handle timeout."""
        logger.warning("BatchApproveView timed out")


class DosenSelect(ui.Select):
    """Dropdown for selecting a dosen (not yet assigned as relator)."""
    
    def __init__(self, custom_id: str = "dosen_select"):
        self.fetched = False
        super().__init__(
            placeholder="👨‍🏫 Pilih Dosen...",
            min_values=1,
            max_values=1,
            custom_id=custom_id,
            options=[],
        )
    
    async def fetch_options(self, guild: discord.Guild) -> list:
        """Fetch dosen from Discord members with Dosen role."""
        options = []
        
        dosen_role = discord.utils.get(guild.roles, name="Dosen")
        if not dosen_role:
            return options
        
        for member in dosen_role.members:
            # Skip if already relator
            from ...database.engine import get_db
            from ...database.models import Relator
            
            async with get_db() as db:
                result = await db.execute(
                    select(Relator).where(
                        Relator.dosen_discord_id == str(member.id)
                    )
                )
                existing = result.scalar_one_or_none()
                
                if not existing:  # Not yet a relator
                    label = member.display_name
                    if len(label) > 100:
                        label = label[:97] + "..."
                    
                    description = f"ID: {member.id}"
                    if len(description) > 100:
                        description = description[:97] + "..."
                    
                    options.append(
                        discord.SelectOption(
                            label=label,
                            value=str(member.id),
                            description=description,
                            emoji="👨‍🏫",
                        )
                    )
        
        self.options = options[:25]
        self.fetched = True
        return self.options
    
    async def callback(self, interaction: discord.Interaction):
        """Handle dosen selection."""
        selected_id = self.values[0]
        
        # Get member from guild
        member = interaction.guild.get_member(int(selected_id))
        if member:
            self.view.selected_dosen = member
            self.placeholder = f"✅ {member.display_name}"
        
        await interaction.response.defer()
        self.view.stop()


class SetRelatorViewV2(ui.View):
    """View for /set-relator v2: Class dropdown + Dosen dropdown + Confirm."""
    
    def __init__(self):
        super().__init__(timeout=120)
        self.selected_class = None
        self.selected_dosen = None
        self.result = None
        
        # Add selects
        self.class_select = ClassSelect()
        self.dosen_select = DosenSelect()
        self.add_item(self.class_select)
        self.add_item(self.dosen_select)
    
    @ui.button(label="✅ Konfirmasi", style=discord.ButtonStyle.success, row=2)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        """Handle confirm button."""
        if not self.selected_class or not self.selected_dosen:
            await interaction.response.send_message(
                "❌ Pilih kelas dan dosen terlebih dahulu!",
                ephemeral=True,
            )
            return
        
        self.result = "confirm"
        
        embed = discord.Embed(
            title="✅ Konfirmasi Set Relator",
            description=(
                f"**Kelas:** {self.selected_class.nama_kelas}\n"
                f"**Dosen:** {self.selected_dosen.mention}\n\n"
                f"Apakah Anda yakin?"
            ),
            color=discord.Color.green(),
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        self.stop()
    
    @ui.button(label="❌ Batal", style=discord.ButtonStyle.secondary, row=2)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        """Handle cancel button."""
        self.result = "cancel"
        await interaction.response.send_message(
            "❌ Dibatalkan", ephemeral=True
        )
        self.stop()
