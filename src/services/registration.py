"""Registration service for student verification."""

import re
import logging
from datetime import datetime, timedelta

from ..config import get_settings
from ..database import User, get_db

logger = logging.getLogger(__name__)


class RegistrationService:
    """Service for handling student registration."""
    
    def __init__(self):
        self.settings = get_settings()
    
    def validate_nim(self, nim: str) -> bool:
        """Validate NIM format."""
        return bool(re.match(self.settings.umsu_nim_pattern, nim))
    
    async def register_student(
        self,
        discord_id: str,
        nim: str,
        nama_lengkap: str = "",
        angkatan: int = 0,
        prodi: str = "",
        kelas: str = ""
    ) -> dict:
        """Register a new student."""
        async for db in get_db():
            # Check if NIM already exists
            existing = await db.query(User).filter(User.nim == nim).first()
            if existing:
                return {
                    "success": False,
                    "error": "NIM sudah terdaftar oleh pengguna lain"
                }
            
            # Check if Discord ID already exists
            existing_discord = await db.query(User).filter(
                User.discord_id == discord_id
            ).first()
            
            if existing_discord:
                # Update existing user
                existing_discord.nim = nim
                existing_discord.nama_lengkap = nama_lengkap
                existing_discord.angkatan = angkatan
                existing_discord.prodi = prodi
                existing_discord.kelas = kelas
                existing_discord.is_verified = True
                existing_discord.updated_at = datetime.utcnow()
                user = existing_discord
            else:
                # Create new user
                user = User(
                    discord_id=discord_id,
                    nim=nim,
                    nama_lengkap=nama_lengkap,
                    angkatan=angkatan,
                    prodi=prodi,
                    kelas=kelas,
                    is_verified=True,
                    role="mahasiswa",
                )
                db.add(user)
            
            await db.commit()
            
            logger.info(f"Student registered: {nim} ({discord_id})")
            
            return {
                "success": True,
                "user": {
                    "id": str(user.id),
                    "discord_id": user.discord_id,
                    "nim": user.nim,
                    "nama_lengkap": user.nama_lengkap,
                    "role": user.role,
                }
            }
    
    async def approve_registration(self, discord_id: str) -> dict:
        """Approve student registration."""
        async for db in get_db():
            user = await db.query(User).filter(
                User.discord_id == discord_id
            ).first()
            
            if not user:
                return {
                    "success": False,
                    "error": "Pengguna tidak ditemukan"
                }
            
            if user.is_verified:
                return {
                    "success": False,
                    "error": "Pengguna sudah terverifikasi"
                }
            
            user.is_verified = True
            user.updated_at = datetime.utcnow()
            await db.commit()
            
            logger.info(f"Registration approved: {discord_id}")
            
            return {
                "success": True,
                "user": {
                    "id": str(user.id),
                    "discord_id": user.discord_id,
                    "nim": user.nim,
                    "nama_lengkap": user.nama_lengkap,
                }
            }
    
    async def reject_registration(self, discord_id: str) -> dict:
        """Reject student registration."""
        async for db in get_db():
            user = await db.query(User).filter(
                User.discord_id == discord_id
            ).first()
            
            if not user:
                return {
                    "success": False,
                    "error": "Pengguna tidak ditemukan"
                }
            
            await db.delete(user)
            await db.commit()
            
            logger.info(f"Registration rejected: {discord_id}")
            
            return {
                "success": True,
                "message": "Registrasi ditolak"
            }
    
    async def get_user_by_discord_id(self, discord_id: str) -> dict:
        """Get user by Discord ID."""
        async for db in get_db():
            user = await db.query(User).filter(
                User.discord_id == discord_id
            ).first()
            
            if not user:
                return None
            
            return {
                "id": str(user.id),
                "discord_id": user.discord_id,
                "nim": user.nim,
                "nama_lengkap": user.nama_lengkap,
                "angkatan": user.angkatan,
                "prodi": user.prodi,
                "kelas": user.kelas,
                "role": user.role,
                "is_verified": user.is_verified,
                "exp": user.exp,
                "level": user.level,
            }
    
    async def get_user_by_nim(self, nim: str) -> dict:
        """Get user by NIM."""
        async for db in get_db():
            user = await db.query(User).filter(User.nim == nim).first()
            
            if not user:
                return None
            
            return {
                "id": str(user.id),
                "discord_id": user.discord_id,
                "nim": user.nim,
                "nama_lengkap": user.nama_lengkap,
                "angkatan": user.angkatan,
                "prodi": user.prodi,
                "kelas": user.kelas,
                "role": user.role,
                "is_verified": user.is_verified,
                "exp": user.exp,
                "level": user.level,
            }
