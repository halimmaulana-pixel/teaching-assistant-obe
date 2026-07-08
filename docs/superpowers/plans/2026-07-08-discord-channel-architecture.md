# Discord Channel Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement complete Discord channel permission system with class isolation, registration flow, and relator assignment for UMSU FIKTI Teaching Assistant Bot.

**Architecture:** Private class channels with role-based access control. Students see only their own class channel. Registration flow auto-generates channels and assigns roles. Relators (dosen) get access to their assigned class channels.

**Tech Stack:** Python 3.11+, discord.py 2.x, SQLAlchemy 2.0, PostgreSQL 15+

---

## File Structure

```
src/
├── bot/
│   ├── __init__.py
│   ├── client.py                    # Discord client with on_member_join
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── registration.py          # /verify, /register commands
│   │   ├── admin.py                 # /setup-server, /set-relator
│   │   └── channel.py              # /create-class, /delete-class
│   ├── events/
│   │   ├── __init__.py
│   │   ├── on_member_join.py        # Welcome flow
│   │   └── on_member_update.py      # Role change handlers
│   └── views/
│       ├── __init__.py
│       └── modals.py                # Registration modal
├── services/
│   ├── __init__.py
│   ├── channel_manager.py           # Channel CRUD + permissions
│   ├── role_manager.py              # Role CRUD + assignments
│   ├── registration.py              # Registration logic
│   └── relator.py                   # Relator assignment logic
├── database/
│   ├── __init__.py
│   ├── engine.py                    # SQLAlchemy engine
│   └── models.py                    # All database models
└── utils/
    ├── __init__.py
    ├── validators.py                # Input validation
    └── constants.py                 # Role/channel names
```

---

## Task 1: Database Models for Channel Architecture

**Files:**
- Create: `src/database/models.py`
- Create: `src/database/engine.py`

- [ ] **Step 1: Create database engine**

```python
# src/database/engine.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 2: Create Student model**

```python
# src/database/models.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, BigInteger, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, DeclarativeBase

class Base(DeclarativeBase):
    pass

class Student(Base):
    __tablename__ = "students"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nim = Column(String(10), unique=True, nullable=False, index=True)
    nama_lengkap = Column(String(100), nullable=False)
    angkatan = Column(Integer, nullable=False)
    prodi = Column(String(50), nullable=False)  # Teknik Informatika, Sistem Informasi, Teknologi Informasi
    kelas = Column(String(5), nullable=False)  # A1, B1, etc.
    discord_id = Column(BigInteger, unique=True, index=True)
    discord_username = Column(String(100))
    email = Column(String(100))
    is_verified = Column(Boolean, default=False)
    verified_at = Column(DateTime)
    verified_by = Column(String(50))  # 'self', 'admin', 'otp'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    class_assignments = relationship("ClassAssignment", back_populates="student")
    relator = relationship("Relator", back_populates="students", uselist=False)
```

- [ ] **Step 3: Create ClassChannel model**

```python
class ClassChannel(Base):
    __tablename__ = "class_channels"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nama_kelas = Column(String(50), unique=True, nullable=False)  # e.g., "alpro-a1-si"
    prodi = Column(String(50), nullable=False)
    angkatan = Column(Integer, nullable=False)
    kelas_code = Column(String(5), nullable=False)  # A1, B1
    discord_channel_id = Column(BigInteger, unique=True)
    discord_category_id = Column(BigInteger)
    discord_role_id = Column(BigInteger)  # @Kelas-[kelas] role
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(BigInteger)  # admin discord_id
    
    # Relationships
    relator = relationship("Relator", back_populates="kelas", uselist=False)
    students = relationship("ClassAssignment", back_populates="kelas")
```

- [ ] **Step 4: Create Relator model**

```python
class Relator(Base):
    __tablename__ = "relators"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dosen_discord_id = Column(BigInteger, nullable=False, index=True)
    dosen_nama = Column(String(100), nullable=False)
    kelas_id = Column(UUID(as_uuid=True), ForeignKey("class_channels.id"), unique=True)
    discord_role_id = Column(BigInteger)  # @Relator-[kelas] role
    is_active = Column(Boolean, default=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    assigned_by = Column(BigInteger)  # admin discord_id
    
    # Relationships
    kelas = relationship("ClassChannel", back_populates="relator")
    students = relationship("Student", back_populates="relator", uselist=False)
```

- [ ] **Step 5: Create ClassAssignment model**

```python
class ClassAssignment(Base):
    __tablename__ = "class_assignments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False)
    kelas_id = Column(UUID(as_uuid=True), ForeignKey("class_channels.id"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    assigned_by = Column(String(50))  # 'system', 'admin'
    
    # Relationships
    student = relationship("Student", back_populates="class_assignments")
    kelas = relationship("ClassChannel", back_populates="students")
    
    __table_args__ = (
        # Student can only be in one active class at a time
        # This is enforced at application level
    )
```

- [ ] **Step 6: Create PendingRegistration model**

```python
class PendingRegistration(Base):
    __tablename__ = "pending_registrations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    discord_id = Column(BigInteger, nullable=False, index=True)
    discord_username = Column(String(100), nullable=False)
    nim = Column(String(10), nullable=False)
    nama_lengkap = Column(String(100), nullable=False)
    angkatan = Column(Integer, nullable=False)
    prodi = Column(String(50), nullable=False)
    kelas = Column(String(5), nullable=False)
    no_wa = Column(String(20))
    status = Column(String(20), default='pending')  # pending, approved, rejected, expired
    submitted_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime)
    reviewed_by = Column(String(100))
    rejection_reason = Column(Text)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 7: Create AuditLog model**

```python
class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(50), nullable=False, index=True)
    discord_id = Column(BigInteger, index=True)
    actor_id = Column(BigInteger)
    metadata = Column(Text)  # JSON string
    ip_address = Column(String(45))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
```

- [ ] **Step 8: Run migration**

```bash
alembic revision --autogenerate -m "create channel architecture tables"
alembic upgrade head
```

---

## Task 2: Discord Role Manager

**Files:**
- Create: `src/services/role_manager.py`
- Create: `src/utils/constants.py`

- [ ] **Step 1: Define role constants**

```python
# src/utils/constants.py
from enum import Enum

class RoleNames:
    MAHASISWA = "Mahasiswa Verified"
    DOSEN = "Dosen"
    ADMIN = "Admin"
    
    @staticmethod
    def kelas_role(kelas_code: str, prodi: str) -> str:
        """Generate role name for a class. E.g., 'Kelas A1-SI'"""
        prodi_short = {
            "Teknik Informatika": "TI",
            "Sistem Informasi": "SI",
            "Teknologi Informasi": "TI-Baru"
        }
        return f"Kelas {kelas_code}-{prodi_short.get(prodi, 'XX')}"
    
    @staticmethod
    def relator_role(kelas_nama: str) -> str:
        """Generate role name for relator. E.g., 'Relator-Alpro-A1-SI'"""
        return f"Relator-{kelas_nama}"

class ChannelNames:
    UMUM = "umum"
    PENGUMUMAN = "pengumuman"
    REGISTRASI = "registrasi"
    ADMIN = "admin"
    ADMIN_LOGS = "admin-logs"
    ADMIN_REGISTRATIONS = "admin-registrations"
    VERIFIKASI = "verifikasi"
    BANTUAN = "bantuan"
    
    @staticmethod
    def class_channel(nama_kelas: str) -> str:
        """Generate channel name for class. E.g., 'alpro-a1-si'"""
        return nama_kelas.lower().replace(" ", "-")

class CategoryNames:
    UMUM = "📁 UMUM"
    ADMIN = "🔧 ADMIN & DOSEN"
    KELAS = "📚 KELAS"
    VERIFIKASI = "🔐 VERIFIKASI"
```

- [ ] **Step 2: Create RoleManager class**

```python
# src/services/role_manager.py
import logging
from typing import Optional
from discord import Guild, Role, Member
from src.utils.constants import RoleNames

logger = logging.getLogger(__name__)

class RoleManager:
    def __init__(self, guild: Guild):
        self.guild = guild
    
    async def get_or_create_role(self, role_name: str, color: int = 0x3498db) -> Role:
        """Get existing role or create new one."""
        existing = self.guild.get_role_named(role_name)
        if existing:
            return existing
        
        role = await self.guild.create_role(
            name=role_name,
            color=color,
            hoist=True,  # Show separately in member list
            mentionable=True
        )
        logger.info(f"Created role: {role_name} (ID: {role.id})")
        return role
    
    async def setup_base_roles(self) -> dict[str, Role]:
        """Create all base roles (Mahasiswa, Dosen, Admin)."""
        roles = {}
        
        # Mahasiswa role - blue color
        roles['mahasiswa'] = await self.get_or_create_role(
            RoleNames.MAHASISWA, 
            color=0x3498db
        )
        
        # Dosen role - green color
        roles['dosen'] = await self.get_or_create_role(
            RoleNames.DOSEN,
            color=0x2ecc71
        )
        
        # Admin role - red color
        roles['admin'] = await self.get_or_create_role(
            RoleNames.ADMIN,
            color=0xe74c3c
        )
        
        return roles
    
    async def create_kelas_role(self, kelas_code: str, prodi: str) -> Role:
        """Create role for a specific class."""
        role_name = RoleNames.kelas_role(kelas_code, prodi)
        return await self.get_or_create_role(role_name, color=0x9b59b6)
    
    async def create_relator_role(self, kelas_nama: str) -> Role:
        """Create role for a relator."""
        role_name = RoleNames.relator_role(kelas_nama)
        return await self.get_or_create_role(role_name, color=0xf39c12)
    
    async def assign_role_to_member(self, member: Member, role: Role) -> bool:
        """Assign role to member. Returns True if successful."""
        try:
            if role in member.roles:
                logger.warning(f"Member {member.id} already has role {role.name}")
                return True
            
            await member.add_roles(role)
            logger.info(f"Assigned role {role.name} to member {member.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to assign role {role.name} to member {member.id}: {e}")
            return False
    
    async def remove_role_from_member(self, member: Member, role: Role) -> bool:
        """Remove role from member. Returns True if successful."""
        try:
            if role not in member.roles:
                return True
            
            await member.remove_roles(role)
            logger.info(f"Removed role {role.name} from member {member.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove role {role.name} from member {member.id}: {e}")
            return False
    
    def get_role_by_name(self, role_name: str) -> Optional[Role]:
        """Get role by name."""
        return self.guild.get_role_named(role_name)
    
    async def assign_verified_roles(
        self, 
        member: Member, 
        prodi: str, 
        kelas_code: str
    ) -> dict[str, Role]:
        """Assign all roles for a verified student."""
        roles_assigned = {}
        
        # 1. Mahasiswa role
        mahasiswa_role = self.get_role_by_name(RoleNames.MAHASISWA)
        if mahasiswa_role:
            await self.assign_role_to_member(member, mahasiswa_role)
            roles_assigned['mahasiswa'] = mahasiswa_role
        
        # 2. Kelas role
        kelas_role_name = RoleNames.kelas_role(kelas_code, prodi)
        kelas_role = self.get_role_by_name(kelas_role_name)
        if kelas_role:
            await self.assign_role_to_member(member, kelas_role)
            roles_assigned['kelas'] = kelas_role
        
        return roles_assigned
```

- [ ] **Step 3: Test role creation**

```python
# tests/test_role_manager.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.role_manager import RoleManager

@pytest.fixture
def mock_guild():
    guild = AsyncMock()
    guild.get_role_named.return_value = None
    guild.create_role = AsyncMock(return_value=MagicMock(id=123, name="TestRole"))
    return guild

@pytest.mark.asyncio
async def test_get_or_create_role_creates_new(mock_guild):
    manager = RoleManager(mock_guild)
    role = await manager.get_or_create_role("TestRole")
    
    mock_guild.create_role.assert_called_once()
    assert role.id == 123

@pytest.mark.asyncio
async def test_get_or_create_role_returns_existing(mock_guild):
    existing_role = MagicMock(id=456, name="ExistingRole")
    mock_guild.get_role_named.return_value = existing_role
    
    manager = RoleManager(mock_guild)
    role = await manager.get_or_create_role("ExistingRole")
    
    mock_guild.create_role.assert_not_called()
    assert role.id == 456
```

---

## Task 3: Discord Channel Manager

**Files:**
- Create: `src/services/channel_manager.py`

- [ ] **Step 1: Create ChannelManager class**

```python
# src/services/channel_manager.py
import logging
from typing import Optional
from discord import Guild, CategoryChannel, TextChannel, PermissionOverwrite, Role
from src.utils.constants import ChannelNames, CategoryNames, RoleNames

logger = logging.getLogger(__name__)

class ChannelManager:
    def __init__(self, guild: Guild):
        self.guild = guild
    
    async def get_or_create_category(self, name: str) -> CategoryChannel:
        """Get existing category or create new one."""
        existing = self.guild.get_channel_named(name)
        if existing and isinstance(existing, CategoryChannel):
            return existing
        
        category = await self.guild.create_category(name)
        logger.info(f"Created category: {name} (ID: {category.id})")
        return category
    
    async def setup_base_channels(self, admin_role: Role, dosen_role: Role, mahasiswa_role: Role) -> dict[str, TextChannel]:
        """Create all base server channels."""
        channels = {}
        
        # 1. #umum - visible to all verified members
        umum_category = await self.get_or_create_category(CategoryNames.UMUM)
        channels['umum'] = await self._create_channel(
            name=ChannelNames.UMUM,
            category=umum_category,
            topic="Forum umum untuk semua mahasiswa dan dosen FIKTI UMSU",
            overwrites={
                self.guild.default_role: PermissionOverwrite(
                    read_messages=False,
                    send_messages=False
                ),
                mahasiswa_role: PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    add_reactions=True,
                    attach_files=True,
                    embed_links=True
                ),
                dosen_role: PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    add_reactions=True,
                    attach_files=True,
                    embed_links=True,
                    manage_messages=True
                ),
                admin_role: PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                    manage_channels=True
                )
            }
        )
        
        # 2. #pengumuman - read-only for students, write for dosen/admin
        channels['pengumuman'] = await self._create_channel(
            name=ChannelNames.PENGUMUMAN,
            category=umum_category,
            topic="Pengumuman resmi dari dosen dan admin",
            overwrites={
                self.guild.default_role: PermissionOverwrite(read_messages=False),
                mahasiswa_role: PermissionOverwrite(
                    read_messages=True,
                    send_messages=False,
                    add_reactions=True
                ),
                dosen_role: PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    attach_files=True,
                    embed_links=True
                ),
                admin_role: PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True
                )
            }
        )
        
        # 3. #registrasi - visible to unverified users
        verifikasi_category = await self.get_or_create_category(CategoryNames.VERIFIKASI)
        channels['registrasi'] = await self._create_channel(
            name=ChannelNames.REGISTRASI,
            category=verifikasi_category,
            topic="Channel registrasi untuk mahasiswa baru",
            overwrites={
                self.guild.default_role: PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    add_reactions=True
                ),
                mahasiswa_role: PermissionOverwrite(read_messages=False),
                dosen_role: PermissionOverwrite(read_messages=False),
                admin_role: PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True
                )
            }
        )
        
        # 4. #admin - admin only
        admin_category = await self.get_or_create_category(CategoryNames.ADMIN)
        channels['admin'] = await self._create_channel(
            name=ChannelNames.ADMIN,
            category=admin_category,
            topic="Channel admin only",
            overwrites={
                self.guild.default_role: PermissionOverwrite(read_messages=False),
                admin_role: PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True
                )
            }
        )
        
        # 5. #admin-logs - admin only, read-only
        channels['admin_logs'] = await self._create_channel(
            name=ChannelNames.ADMIN_LOGS,
            category=admin_category,
            topic="Logs aktivitas bot",
            overwrites={
                self.guild.default_role: PermissionOverwrite(read_messages=False),
                admin_role: PermissionOverwrite(
                    read_messages=True,
                    send_messages=False
                )
            }
        )
        
        # 6. #admin-registrations - admin only
        channels['admin_registrations'] = await self._create_channel(
            name=ChannelNames.ADMIN_REGISTRATIONS,
            category=admin_category,
            topic="Registrasi menunggu persetujuan",
            overwrites={
                self.guild.default_role: PermissionOverwrite(read_messages=False),
                admin_role: PermissionOverwrite(
                    read_messages=True,
                    send_messages=True
                )
            }
        )
        
        return channels
    
    async def _create_channel(
        self,
        name: str,
        category: CategoryChannel,
        topic: str = "",
        overwrites: dict[Role, PermissionOverwrite] = None
    ) -> TextChannel:
        """Create a text channel with permissions."""
        channel = await self.guild.create_text_channel(
            name=name,
            category=category,
            topic=topic,
            overwrites=overwrites or {}
        )
        logger.info(f"Created channel: #{name} (ID: {channel.id})")
        return channel
    
    async def create_class_channel(
        self,
        nama_kelas: str,
        prodi: str,
        kelas_role: Role,
        relator_role: Role,
        dosen_role: Role,
        admin_role: Role
    ) -> TextChannel:
        """Create a private class channel with proper permissions."""
        
        # Get or create KELAS category
        kelas_category = await self.get_or_create_category(CategoryNames.KELAS)
        
        # Generate channel name
        channel_name = ChannelNames.class_channel(nama_kelas)
        
        # Define permissions
        overwrites = {
            self.guild.default_role: PermissionOverwrite(
                read_messages=False,  # Hidden by default
                send_messages=False
            ),
            kelas_role: PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                add_reactions=True,
                attach_files=True,
                embed_links=True,
                read_message_history=True
            ),
            relator_role: PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_messages=True,
                add_reactions=True,
                attach_files=True,
                embed_links=True,
                read_message_history=True,
                mention_everyone=True
            ),
            dosen_role: PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                add_reactions=True,
                read_message_history=True
            ),
            admin_role: PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_messages=True,
                manage_channels=True
            )
        }
        
        # Create channel
        channel = await self.guild.create_text_channel(
            name=channel_name,
            category=kelas_category,
            topic=f"Kelas {nama_kelas} - {prodi}",
            overwrites=overwrites
        )
        
        logger.info(f"Created class channel: #{channel_name} (ID: {channel.id})")
        return channel
    
    async def delete_class_channel(self, channel_id: int) -> bool:
        """Delete a class channel."""
        try:
            channel = self.guild.get_channel(channel_id)
            if channel:
                await channel.delete()
                logger.info(f"Deleted channel: #{channel.name} (ID: {channel_id})")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete channel {channel_id}: {e}")
            return False
    
    async def update_channel_permissions(
        self,
        channel_id: int,
        role: Role,
        permissions: PermissionOverwrite
    ) -> bool:
        """Update permissions for a role in a channel."""
        try:
            channel = self.guild.get_channel(channel_id)
            if channel:
                await channel.set_permissions(role, overwrite=permissions)
                logger.info(f"Updated permissions for role {role.name} in #{channel.name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update permissions: {e}")
            return False
```

- [ ] **Step 2: Test channel creation**

```python
# tests/test_channel_manager.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.channel_manager import ChannelManager

@pytest.fixture
def mock_guild():
    guild = AsyncMock()
    guild.get_channel_named.return_value = None
    guild.get_role_named.return_value = None
    guild.create_category = AsyncMock(return_value=MagicMock(id=100, name="TestCategory"))
    guild.create_text_channel = AsyncMock(return_value=MagicMock(id=200, name="test-channel"))
    return guild

@pytest.mark.asyncio
async def test_create_class_channel(mock_guild):
    manager = ChannelManager(mock_guild)
    
    kelas_role = MagicMock(id=300, name="Kelas A1-SI")
    relator_role = MagicMock(id=400, name="Relator-Alpro-A1-SI")
    dosen_role = MagicMock(id=500, name="Dosen")
    admin_role = MagicMock(id=600, name="Admin")
    
    channel = await manager.create_class_channel(
        nama_kelas="Alpro A1 SI",
        prodi="Sistem Informasi",
        kelas_role=kelas_role,
        relator_role=relator_role,
        dosen_role=dosen_role,
        admin_role=admin_role
    )
    
    mock_guild.create_text_channel.assert_called_once()
    assert channel.id == 200
```

---

## Task 4: Registration Service

**Files:**
- Create: `src/services/registration.py`

- [ ] **Step 1: Create RegistrationService class**

```python
# src/services/registration.py
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import Student, PendingRegistration, ClassChannel, ClassAssignment
from src.utils.constants import RoleNames

logger = logging.getLogger(__name__)

class RegistrationService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def validate_nim(self, nim: str) -> tuple[bool, str, Optional[dict]]:
        """
        Validate NIM format and structure.
        Returns: (is_valid, message, parsed_data)
        """
        import re
        
        # Format check
        if not re.match(r'^[0-9]{10}$', nim):
            return False, "NIM harus 10 digit angka", None
        
        # Structure validation
        angkatan = int(nim[:2])
        prodi_code = nim[2:5]
        nomor_urut = int(nim[5:])
        
        # Validate angkatan (20-30 means 2020-2030)
        if not (20 <= angkatan <= 30):
            return False, "Angkatan tidak valid (20-30)", None
        
        # Validate prodi
        valid_prodi = {"711", "712", "713"}
        if prodi_code not in valid_prodi:
            return False, f"Kode prodi tidak valid: {prodi_code}", None
        
        # Validate nomor urut
        if not (1 <= nomor_urut <= 99999):
            return False, "Nomor urut tidak valid", None
        
        # Map prodi code to name
        prodi_map = {
            "711": "Teknik Informatika",
            "712": "Sistem Informasi",
            "713": "Teknologi Informasi"
        }
        
        parsed_data = {
            "angkatan": 2000 + angkatan,
            "prodi": prodi_map[prodi_code],
            "prodi_code": prodi_code,
            "nomor_urut": nomor_urut
        }
        
        return True, "Valid", parsed_data
    
    async def check_existing_student(self, nim: str) -> Optional[Student]:
        """Check if student with NIM exists."""
        result = await self.db.execute(
            select(Student).where(Student.nim == nim)
        )
        return result.scalar_one_or_none()
    
    async def check_existing_discord(self, discord_id: int) -> Optional[Student]:
        """Check if Discord account is already linked."""
        result = await self.db.execute(
            select(Student).where(Student.discord_id == discord_id)
        )
        return result.scalar_one_or_none()
    
    async def register_student(
        self,
        nim: str,
        nama_lengkap: str,
        angkatan: int,
        prodi: str,
        kelas: str,
        discord_id: int,
        discord_username: str,
        no_wa: str = None
    ) -> tuple[bool, str, Optional[Student]]:
        """
        Register a new student.
        Returns: (success, message, student)
        """
        # Check if NIM already registered
        existing = await self.check_existing_student(nim)
        if existing:
            if existing.discord_id == discord_id:
                return True, "Kamu sudah terverifikasi!", existing
            elif existing.discord_id is None:
                # NIM exists but not linked - need admin approval
                return False, "NIM sudah terdaftar tapi belum terhubung. Hubungi admin.", None
            else:
                return False, "NIM sudah terhubung ke akun Discord lain.", None
        
        # Check if Discord already linked
        existing_discord = await self.check_existing_discord(discord_id)
        if existing_discord:
            return False, "Akun Discord ini sudah terhubung ke NIM lain.", None
        
        # Create new student
        student = Student(
            nim=nim,
            nama_lengkap=nama_lengkap,
            angkatan=angkatan,
            prodi=prodi,
            kelas=kelas,
            discord_id=discord_id,
            discord_username=discord_username,
            is_verified=True,
            verified_at=datetime.utcnow(),
            verified_by='self'
        )
        
        self.db.add(student)
        await self.db.commit()
        await self.db.refresh(student)
        
        logger.info(f"Registered student: {nim} ({nama_lengkap})")
        return True, "Registrasi berhasil!", student
    
    async def create_pending_registration(
        self,
        discord_id: int,
        discord_username: str,
        nim: str,
        nama_lengkap: str,
        angkatan: int,
        prodi: str,
        kelas: str,
        no_wa: str = None
    ) -> PendingRegistration:
        """Create a pending registration for admin approval."""
        pending = PendingRegistration(
            discord_id=discord_id,
            discord_username=discord_username,
            nim=nim,
            nama_lengkap=nama_lengkap,
            angkatan=angkatan,
            prodi=prodi,
            kelas=kelas,
            no_wa=no_wa,
            status='pending',
            expires_at=datetime.utcnow() + timedelta(hours=48)
        )
        
        self.db.add(pending)
        await self.db.commit()
        await self.db.refresh(pending)
        
        logger.info(f"Created pending registration for {discord_username}")
        return pending
    
    async def approve_registration(self, pending_id: str, approved_by: str) -> tuple[bool, str, Optional[Student]]:
        """Approve a pending registration."""
        result = await self.db.execute(
            select(PendingRegistration).where(PendingRegistration.id == pending_id)
        )
        pending = result.scalar_one_or_none()
        
        if not pending:
            return False, "Registrasi tidak ditemukan.", None
        
        if pending.status != 'pending':
            return False, f"Registrasi sudah {pending.status}.", None
        
        # Check expiration
        if pending.expires_at < datetime.utcnow():
            pending.status = 'expired'
            await self.db.commit()
            return False, "Registrasi sudah kedaluwarsa.", None
        
        # Create student record
        student = Student(
            nim=pending.nim,
            nama_lengkap=pending.nama_lengkap,
            angkatan=pending.angkatan,
            prodi=pending.prodi,
            kelas=pending.kelas,
            discord_id=pending.discord_id,
            discord_username=pending.discord_username,
            is_verified=True,
            verified_at=datetime.utcnow(),
            verified_by='admin'
        )
        
        self.db.add(student)
        
        # Update pending status
        pending.status = 'approved'
        pending.reviewed_at = datetime.utcnow()
        pending.reviewed_by = approved_by
        
        await self.db.commit()
        await self.db.refresh(student)
        
        logger.info(f"Approved registration: {pending.nim} by {approved_by}")
        return True, "Registrasi disetujui!", student
    
    async def reject_registration(self, pending_id: str, rejected_by: str, reason: str) -> tuple[bool, str]:
        """Reject a pending registration."""
        result = await self.db.execute(
            select(PendingRegistration).where(PendingRegistration.id == pending_id)
        )
        pending = result.scalar_one_or_none()
        
        if not pending:
            return False, "Registrasi tidak ditemukan."
        
        if pending.status != 'pending':
            return False, f"Registrasi sudah {pending.status}."
        
        # Update pending status
        pending.status = 'rejected'
        pending.reviewed_at = datetime.utcnow()
        pending.reviewed_by = rejected_by
        pending.rejection_reason = reason
        
        await self.db.commit()
        
        logger.info(f"Rejected registration: {pending.nim} by {rejected_by}")
        return True, "Registrasi ditolak."
    
    async def get_pending_registrations(self) -> list[PendingRegistration]:
        """Get all pending registrations."""
        result = await self.db.execute(
            select(PendingRegistration)
            .where(PendingRegistration.status == 'pending')
            .where(PendingRegistration.expires_at > datetime.utcnow())
            .order_by(PendingRegistration.submitted_at)
        )
        return list(result.scalars().all())
    
    async def cleanup_expired_registrations(self) -> int:
        """Mark expired registrations. Returns count of expired."""
        result = await self.db.execute(
            select(PendingRegistration)
            .where(PendingRegistration.status == 'pending')
            .where(PendingRegistration.expires_at <= datetime.utcnow())
        )
        expired = result.scalars().all()
        
        for reg in expired:
            reg.status = 'expired'
        
        await self.db.commit()
        logger.info(f"Expired {len(expired)} pending registrations")
        return len(expired)
```

---

## Task 5: Relator Assignment Service

**Files:**
- Create: `src/services/relator.py`

- [ ] **Step 1: Create RelatorService class**

```python
# src/services/relator.py
import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from discord import Guild, Member
from src.database.models import Relator, ClassChannel
from src.services.role_manager import RoleManager
from src.services.channel_manager import ChannelManager
from src.utils.constants import RoleNames

logger = logging.getLogger(__name__)

class RelatorService:
    def __init__(self, db: AsyncSession, guild: Guild):
        self.db = db
        self.guild = guild
        self.role_manager = RoleManager(guild)
        self.channel_manager = ChannelManager(guild)
    
    async def set_relator(
        self,
        kelas_nama: str,
        dosen_member: Member,
        admin_id: int
    ) -> tuple[bool, str, Optional[Relator]]:
        """
        Assign a relator to a class.
        
        Flow:
        1. Find or create class channel
        2. Create @Relator-[kelas] role
        3. Assign role to dosen
        4. Update class channel permissions
        5. Save to database
        """
        # 1. Find class channel
        result = await self.db.execute(
            select(ClassChannel).where(ClassChannel.nama_kelas == kelas_nama)
        )
        kelas = result.scalar_one_or_none()
        
        if not kelas:
            return False, f"Kelas '{kelas_nama}' tidak ditemukan.", None
        
        # 2. Check if relator already assigned
        existing_result = await self.db.execute(
            select(Relator).where(
                Relator.kelas_id == kelas.id,
                Relator.is_active == True
            )
        )
        existing_relator = existing_result.scalar_one_or_none()
        
        if existing_relator:
            return False, f"Kelas sudah memiliki relator (ID: {existing_relator.dosen_discord_id}).", None
        
        # 3. Create relator role
        relator_role = await self.role_manager.create_relator_role(kelas_nama)
        
        # 4. Assign role to dosen
        assigned = await self.role_manager.assign_role_to_member(dosen_member, relator_role)
        if not assigned:
            return False, "Gagal assign role ke dosen.", None
        
        # 5. Update channel permissions
        if kelas.discord_channel_id:
            from discord import PermissionOverwrite
            await self.channel_manager.update_channel_permissions(
                channel_id=kelas.discord_channel_id,
                role=relator_role,
                permissions=PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                    add_reactions=True,
                    attach_files=True,
                    embed_links=True,
                    read_message_history=True,
                    mention_everyone=True
                )
            )
        
        # 6. Save to database
        relator = Relator(
            dosen_discord_id=dosen_member.id,
            dosen_nama=dosen_member.display_name,
            kelas_id=kelas.id,
            discord_role_id=relator_role.id,
            is_active=True,
            assigned_by=admin_id
        )
        
        self.db.add(relator)
        await self.db.commit()
        await self.db.refresh(relator)
        
        logger.info(f"Assigned relator {dosen_member.id} to class {kelas_nama}")
        return True, f"Relator berhasil ditugaskan ke kelas {kelas_nama}.", relator
    
    async def remove_relator(self, kelas_nama: str) -> tuple[bool, str]:
        """Remove relator from a class."""
        # Find class
        result = await self.db.execute(
            select(ClassChannel).where(ClassChannel.nama_kelas == kelas_nama)
        )
        kelas = result.scalar_one_or_none()
        
        if not kelas:
            return False, f"Kelas '{kelas_nama}' tidak ditemukan."
        
        # Find active relator
        relator_result = await self.db.execute(
            select(Relator).where(
                Relator.kelas_id == kelas.id,
                Relator.is_active == True
            )
        )
        relator = relator_result.scalar_one_or_none()
        
        if not relator:
            return False, "Kelas tidak memiliki relator."
        
        # Remove role from dosen
        dosen_member = self.guild.get_member(relator.dosen_discord_id)
        if dosen_member:
            relator_role = self.guild.get_role(relator.discord_role_id)
            if relator_role:
                await self.role_manager.remove_role_from_member(dosen_member, relator_role)
        
        # Mark as inactive
        relator.is_active = False
        await self.db.commit()
        
        logger.info(f"Removed relator from class {kelas_nama}")
        return True, "Relator berhasil dihapus."
    
    async def get_relator(self, kelas_nama: str) -> Optional[Relator]:
        """Get active relator for a class."""
        result = await self.db.execute(
            select(Relator)
            .join(ClassChannel)
            .where(
                ClassChannel.nama_kelas == kelas_nama,
                Relator.is_active == True
            )
        )
        return result.scalar_one_or_none()
    
    async def get_classes_by_relator(self, dosen_discord_id: int) -> list[ClassChannel]:
        """Get all classes managed by a relator."""
        result = await self.db.execute(
            select(ClassChannel)
            .join(Relator)
            .where(
                Relator.dosen_discord_id == dosen_discord_id,
                Relator.is_active == True
            )
        )
        return list(result.scalars().all())
```

---

## Task 6: Channel Setup Command

**Files:**
- Create: `src/bot/commands/admin.py`

- [ ] **Step 1: Create admin command group**

```python
# src/bot/commands/admin.py
import discord
from discord import app_commands, Interaction, Member, Role
from discord.ext import commands
from src.services.channel_manager import ChannelManager
from src.services.role_manager import RoleManager
from src.services.relator import RelatorService
from src.database.engine import get_db
from src.utils.constants import ChannelNames, CategoryNames

class AdminCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="setup-server", description="Setup server FIKTI UMSU (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_server(self, interaction: Interaction):
        """Setup complete server structure."""
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        role_manager = RoleManager(guild)
        channel_manager = ChannelManager(guild)
        
        try:
            # 1. Create base roles
            roles = await role_manager.setup_base_roles()
            
            # 2. Create base channels
            channels = await channel_manager.setup_base_channels(
                admin_role=roles['admin'],
                dosen_role=roles['dosen'],
                mahasiswa_role=roles['mahasiswa']
            )
            
            # 3. Send success message
            embed = discord.Embed(
                title="✅ Server Setup Complete",
                description="Server FIKTI UMSU berhasil disetup!",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Roles Created",
                value="\n".join([f"• {r.name}" for r in roles.values()]),
                inline=False
            )
            embed.add_field(
                name="Channels Created",
                value="\n".join([f"• #{c.name}" for c in channels.values()]),
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="set-relator", description="Assign relator to a class")
    @app_commands.describe(
        kelas="Nama kelas (e.g., alpro-a1-si)",
        dosen="Dosen yang akan jadi relator"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_relator(
        self,
        interaction: Interaction,
        kelas: str,
        dosen: Member
    ):
        """Assign a relator to a class."""
        await interaction.response.defer(ephemeral=True)
        
        async for db in get_db():
            relator_service = RelatorService(db, interaction.guild)
            success, message, relator = await relator_service.set_relator(
                kelas_nama=kelas,
                dosen_member=dosen,
                admin_id=interaction.user.id
            )
            
            if success:
                embed = discord.Embed(
                    title="✅ Relator Assigned",
                    description=message,
                    color=discord.Color.green()
                )
                embed.add_field(name="Kelas", value=kelas, inline=True)
                embed.add_field(name="Relator", value=dosen.mention, inline=True)
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description=message,
                    color=discord.Color.red()
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="create-class", description="Create a new class channel")
    @app_commands.describe(
        nama_kelas="Nama kelas (e.g., Alpro A1 SI)",
        prodi="Program Studi",
        angkatan="Angkatan"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def create_class(
        self,
        interaction: Interaction,
        nama_kelas: str,
        prodi: str,
        angkatan: int
    ):
        """Create a new class channel with role."""
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        role_manager = RoleManager(guild)
        channel_manager = ChannelManager(guild)
        
        try:
            # 1. Create class role
            kelas_code = nama_kelas.split()[-1] if " " in nama_kelas else "A1"
            kelas_role = await role_manager.create_kelas_role(kelas_code, prodi)
            
            # 2. Get required roles
            dosen_role = role_manager.get_role_by_name("Dosen")
            admin_role = role_manager.get_role_by_name("Admin")
            
            if not dosen_role or not admin_role:
                await interaction.followup.send(
                    "❌ Base roles belum dibuat. Jalankan /setup-server dulu.",
                    ephemeral=True
                )
                return
            
            # 3. Create channel
            channel = await channel_manager.create_class_channel(
                nama_kelas=nama_kelas,
                prodi=prodi,
                kelas_role=kelas_role,
                relator_role=None,  # Will be assigned later
                dosen_role=dosen_role,
                admin_role=admin_role
            )
            
            # 4. Save to database
            async for db in get_db():
                from src.database.models import ClassChannel
                kelas = ClassChannel(
                    nama_kelas=nama_kelas,
                    prodi=prodi,
                    angkatan=angkatan,
                    kelas_code=kelas_code,
                    discord_channel_id=channel.id,
                    discord_role_id=kelas_role.id,
                    created_by=interaction.user.id
                )
                db.add(kelas)
                await db.commit()
            
            # 5. Send success message
            embed = discord.Embed(
                title="✅ Class Channel Created",
                description=f"Channel {channel.mention} berhasil dibuat!",
                color=discord.Color.green()
            )
            embed.add_field(name="Kelas", value=nama_kelas, inline=True)
            embed.add_field(name="Prodi", value=prodi, inline=True)
            embed.add_field(name="Role", value=kelas_role.mention, inline=True)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )
```

---

## Task 7: Registration Command with Modal

**Files:**
- Create: `src/bot/commands/registration.py`
- Create: `src/bot/views/modals.py`

- [ ] **Step 1: Create Registration Modal**

```python
# src/bot/views/modals.py
import discord
from discord import ui, Interaction

class RegistrationModal(ui.Modal, title="📝 Formulir Registrasi Mahasiswa"):
    """Modal form for student registration."""
    
    nim = ui.TextInput(
        label="NIM",
        placeholder="2471110042",
        style=discord.TextInputStyle.short,
        required=True,
        max_length=10,
        min_length=10
    )
    
    nama_lengkap = ui.TextInput(
        label="Nama Lengkap",
        placeholder="Ahmad Fauzi",
        style=discord.TextInputStyle.short,
        required=True,
        max_length=100
    )
    
    prodi = ui.TextInput(
        label="Program Studi",
        placeholder="Teknik Informatika / Sistem Informasi / Teknologi Informasi",
        style=discord.TextInputStyle.short,
        required=True
    )
    
    kelas = ui.TextInput(
        label="Kelas",
        placeholder="A1, B1, dll",
        style=discord.TextInputStyle.short,
        required=True,
        max_length=5
    )
    
    no_wa = ui.TextInput(
        label="No. WhatsApp",
        placeholder="08123456789",
        style=discord.TextInputStyle.short,
        required=True,
        max_length=15
    )
    
    async def on_submit(self, interaction: Interaction):
        """Handle form submission."""
        from src.services.registration import RegistrationService
        from src.database.engine import AsyncSessionLocal
        
        async with AsyncSessionLocal() as db:
            service = RegistrationService(db)
            
            # Validate NIM
            is_valid, message, parsed_data = await service.validate_nim(self.nim.value)
            
            if not is_valid:
                await interaction.response.send_message(
                    f"❌ {message}",
                    ephemeral=True
                )
                return
            
            # Check existing student
            existing = await service.check_existing_student(self.nim.value)
            if existing:
                if existing.discord_id == interaction.user.id:
                    await interaction.response.send_message(
                        "⚠️ Kamu sudah terverifikasi!",
                        ephemeral=True
                    )
                    return
                elif existing.discord_id is None:
                    await interaction.response.send_message(
                        "⚠️ NIM sudah terdaftar tapi belum terhubung. Hubungi admin.",
                        ephemeral=True
                    )
                    return
                else:
                    await interaction.response.send_message(
                        "❌ NIM sudah terhubung ke akun Discord lain.",
                        ephemeral=True
                    )
                    return
            
            # Create pending registration
            pending = await service.create_pending_registration(
                discord_id=interaction.user.id,
                discord_username=interaction.user.name,
                nim=self.nim.value,
                nama_lengkap=self.nama_lengkap.value,
                angkatan=parsed_data['angkatan'],
                prodi=parsed_data['prodi'],
                kelas=self.kelas.value,
                no_wa=self.no_wa.value
            )
            
            # Send confirmation
            embed = discord.Embed(
                title="✅ Registrasi Dikirim",
                description="Registrasi kamu sedang menunggu persetujuan admin.",
                color=discord.Color.green()
            )
            embed.add_field(name="NIM", value=self.nim.value, inline=True)
            embed.add_field(name="Nama", value=self.nama_lengkap.value, inline=True)
            embed.add_field(name="Prodi", value=parsed_data['prodi'], inline=True)
            embed.add_field(name="Kelas", value=self.kelas.value, inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Notify admin channel
            admin_channel = interaction.guild.get_channel_named("admin-registrations")
            if admin_channel:
                admin_embed = discord.Embed(
                    title="📝 Registrasi Baru",
                    color=discord.Color.yellow()
                )
                admin_embed.add_field(name="Discord", value=interaction.user.mention, inline=True)
                admin_embed.add_field(name="NIM", value=self.nim.value, inline=True)
                admin_embed.add_field(name="Nama", value=self.nama_lengkap.value, inline=True)
                admin_embed.add_field(name="Prodi", value=parsed_data['prodi'], inline=True)
                admin_embed.add_field(name="Kelas", value=self.kelas.value, inline=True)
                admin_embed.add_field(name="No WA", value=self.no_wa.value, inline=True)
                admin_embed.set_footer(text=f"ID: {pending.id}")
                
                await admin_channel.send(embed=admin_embed)
    
    async def on_error(self, interaction: Interaction, error: Exception):
        """Handle errors."""
        await interaction.response.send_message(
            f"❌ Terjadi kesalahan: {str(error)}",
            ephemeral=True
        )
```

- [ ] **Step 2: Create Registration Commands**

```python
# src/bot/commands/registration.py
import discord
from discord import app_commands, Interaction
from discord.ext import commands
from src.bot.views.modals import RegistrationModal

class RegistrationCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="register", description="Registrasi mahasiswa baru")
    async def register(self, interaction: Interaction):
        """Open registration modal."""
        modal = RegistrationModal()
        await interaction.response.send_modal(modal)
    
    @app_commands.command(name="verify", description="Verifikasi NIM (untuk yang sudah punya data)")
    @app_commands.describe(nim="NIM kamu")
    async def verify(self, interaction: Interaction, nim: str):
        """Verify existing NIM."""
        from src.services.registration import RegistrationService
        from src.database.engine import AsyncSessionLocal
        from src.services.role_manager import RoleManager
        
        await interaction.response.defer(ephemeral=True)
        
        async with AsyncSessionLocal() as db:
            service = RegistrationService(db)
            
            # Validate NIM
            is_valid, message, parsed_data = await service.validate_nim(nim)
            if not is_valid:
                await interaction.followup.send(
                    f"❌ {message}",
                    ephemeral=True
                )
                return
            
            # Check existing
            student = await service.check_existing_student(nim)
            if not student:
                await interaction.followup.send(
                    "❌ NIM tidak ditemukan. Gunakan /register untuk mendaftar.",
                    ephemeral=True
                )
                return
            
            if student.discord_id and student.discord_id != interaction.user.id:
                await interaction.followup.send(
                    "❌ NIM sudah terhubung ke akun Discord lain.",
                    ephemeral=True
                )
                return
            
            if student.discord_id == interaction.user.id:
                await interaction.followup.send(
                    "⚠️ Kamu sudah terverifikasi!",
                    ephemeral=True
                )
                return
            
            # Link Discord ID
            student.discord_id = interaction.user.id
            student.discord_username = interaction.user.name
            student.is_verified = True
            student.verified_at = datetime.utcnow()
            student.verified_by = 'self'
            await db.commit()
            
            # Assign roles
            role_manager = RoleManager(interaction.guild)
            await role_manager.assign_verified_roles(
                member=interaction.user,
                prodi=student.prodi,
                kelas_code=student.kelas
            )
            
            # Send success
            embed = discord.Embed(
                title="✅ Verifikasi Berhasil",
                description=f"Selamat datang, {student.nama_lengkap}!",
                color=discord.Color.green()
            )
            embed.add_field(name="NIM", value=nim, inline=True)
            embed.add_field(name="Prodi", value=student.prodi, inline=True)
            embed.add_field(name="Kelas", value=student.kelas, inline=True)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
```

---

## Task 8: Event Handlers

**Files:**
- Create: `src/bot/events/on_member_join.py`

- [ ] **Step 1: Create on_member_join handler**

```python
# src/bot/events/on_member_join.py
import discord
from discord.ext import commands
from datetime import datetime, timedelta

class MemberJoinHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Handle new member joining the server."""
        guild = member.guild
        
        # Skip bots
        if member.bot:
            return
        
        # Log join event
        await self.log_join_event(member)
        
        # Send welcome DM
        await self.send_welcome_dm(member)
        
        # Send notification to admin-logs
        await self.notify_admin_logs(member)
    
    async def log_join_event(self, member: discord.Member):
        """Log join event to database."""
        from src.database.engine import AsyncSessionLocal
        from src.database.models import AuditLog
        import json
        
        async with AsyncSessionLocal() as db:
            log = AuditLog(
                event_type="member_join",
                discord_id=member.id,
                actor_id=member.id,
                metadata=json.dumps({
                    "username": member.name,
                    "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                    "verification_deadline": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
                    "kick_deadline": (datetime.utcnow() + timedelta(hours=72)).isoformat()
                })
            )
            db.add(log)
            await db.commit()
    
    async def send_welcome_dm(self, member: discord.Member):
        """Send welcome DM with verification instructions."""
        try:
            embed = discord.Embed(
                title="🎓 Selamat Datang di FIKTI UMSU!",
                description=(
                    f"Halo {member.mention}! 👋\n\n"
                    "Selamat datang di server resmi FIKTI UMSU.\n"
                    "Untuk mengakses semua channel, kamu perlu **verifikasi NIM**."
                ),
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📋 Langkah Verifikasi",
                value=(
                    "1. Pergi ke channel <#registrasi>\n"
                    "2. Ketik `/register` untuk mengisi formulir\n"
                    "3. Atau ketik `/verify [NIM_KAMU]` jika sudah punya data"
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
            embed.set_footer(text="FIKTI UMSU — Teaching Assistant Bot")
            
            await member.send(embed=embed)
        except discord.Forbidden:
            # Member has DMs disabled
            pass
    
    async def notify_admin_logs(self, member: discord.Member):
        """Send notification to admin-logs channel."""
        admin_logs = member.guild.get_channel_named("admin-logs")
        if not admin_logs:
            return
        
        embed = discord.Embed(
            title="📥 Member Joined",
            description=f"{member.mention} joined the server",
            color=discord.Color.blue()
        )
        embed.add_field(name="Username", value=member.name, inline=True)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(
            name="Account Created",
            value=member.created_at.strftime("%Y-%m-%d %H:%M"),
            inline=True
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Verification deadline: 24 hours")
        
        await admin_logs.send(embed=embed)
```

---

## Task 9: Permission Matrix Reference

**File:** `docs/permission-matrix.md`

- [ ] **Step 1: Create permission matrix document**

```markdown
# Discord Permission Matrix

## Channel Permissions

| Channel | @everyone | @Mahasiswa | @Dosen | @Admin | @Relator-[kelas] | @Kelas-[kelas] |
|---------|-----------|------------|--------|--------|------------------|----------------|
| #umum | ❌ | ✅ R/W | ✅ R/W | ✅ R/W/M | ✅ R/W | ✅ R/W |
| #pengumuman | ❌ | ✅ R | ✅ R/W | ✅ R/W/M | ✅ R/W | ✅ R |
| #registrasi | ✅ R/W | ❌ | ❌ | ✅ R/W/M | ❌ | ❌ |
| #admin | ❌ | ❌ | ❌ | ✅ R/W/M | ❌ | ❌ |
| #admin-logs | ❌ | ❌ | ❌ | ✅ R | ❌ | ❌ |
| #admin-registrations | ❌ | ❌ | ❌ | ✅ R/W | ❌ | ❌ |
| #[kelas] | ❌ | ❌ | ✅ R | ✅ R/W/M | ✅ R/W/M | ✅ R/W |

**Legend:** R = Read, W = Write, M = Manage

## Role Hierarchy

```
@Admin (highest)
  └─► Full server access
  └─► Manage channels, roles, members
  
@Dosen
  └─► Read/write in #umum, #pengumuman
  └─► Read in class channels (if assigned)
  └─► Manage messages in their channels
  
@Relator-[kelas]
  └─► Full access to assigned class channel
  └─► Read/write in #umum, #pengumuman
  └─► Manage messages in class channel
  
@Mahasiswa Verified
  └─► Read/write in #umum
  └─► Read in #pengumuman
  └─► Read/write in assigned class channel
  
@Kelas-[kelas]
  └─► Read/write in class channel only
  └─► No access to other class channels
  
@everyone (lowest)
  └─► Only access to #registrasi
  └─► No access to other channels
```

## Class Isolation

Each class channel has unique permissions:
- `@Kelas-A1-SI` → Can see `#alpro-a1-si` only
- `@Kelas-B1-SI` → Can see `#alpro-b1-si` only
- `@Kelas-A1-TI` → Can see `#alpro-a1-ti` only

Students from Class A CANNOT see Class B channels.

## Registration Flow

```
New Member Joins
    ↓
Sees: #registrasi only
    ↓
Fills form via /register
    ↓
Admin approves
    ↓
Bot assigns: @Mahasiswa + @Kelas-[kelas]
    ↓
Now sees: #umum + #[kelas] + #pengumuman
```
```

---

## Task 10: Database Schema Reference

**File:** `docs/database-schema.md`

- [ ] **Step 1: Create database schema document**

```markdown
# Database Schema

## ER Diagram

```
┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────┐
│    students      │     │  class_channels     │     │   relators      │
├─────────────────┤     ├─────────────────────┤     ├─────────────────┤
│ id (PK)         │     │ id (PK)             │     │ id (PK)         │
│ nim (UNIQUE)    │     │ nama_kelas (UNIQUE) │     │ dosen_discord_id│
│ nama_lengkap    │     │ prodi               │     │ dosen_nama      │
│ angkatan        │     │ angkatan            │     │ kelas_id (FK)   │
│ prodi           │     │ kelas_code          │     │ discord_role_id │
│ kelas           │     │ discord_channel_id  │     │ is_active       │
│ discord_id      │     │ discord_role_id     │     │ assigned_at     │
│ discord_username│     │ is_active           │     │ assigned_by     │
│ is_verified     │     │ created_at          │     └─────────────────┘
│ verified_at     │     │ created_by          │
│ verified_by     │     └─────────────────────┘
│ created_at      │              │
│ updated_at      │              │
└─────────────────┘              │
         │                       │
         │    ┌──────────────────┘
         │    │
         ▼    ▼
┌─────────────────────────┐
│  class_assignments      │
├─────────────────────────┤
│ id (PK)                 │
│ student_id (FK)         │
│ kelas_id (FK)           │
│ assigned_at             │
│ assigned_by             │
└─────────────────────────┘

┌─────────────────────────┐
│ pending_registrations   │
├─────────────────────────┤
│ id (PK)                 │
│ discord_id              │
│ discord_username        │
│ nim                     │
│ nama_lengkap            │
│ angkatan                │
│ prodi                   │
│ kelas                   │
│ no_wa                   │
│ status                  │
│ submitted_at            │
│ reviewed_at             │
│ reviewed_by             │
│ rejection_reason        │
│ expires_at              │
└─────────────────────────┘

┌─────────────────────────┐
│      audit_log          │
├─────────────────────────┤
│ id (PK)                 │
│ event_type              │
│ discord_id              │
│ actor_id                │
│ metadata (JSONB)        │
│ ip_address              │
│ created_at              │
└─────────────────────────┘
```

## Table Relationships

- `students.discord_id` → Discord user ID
- `class_channels.discord_channel_id` → Discord channel ID
- `class_channels.discord_role_id` → Discord role ID (@Kelas-[kelas])
- `relators.discord_role_id` → Discord role ID (@Relator-[kelas])
- `class_assignments.student_id` → students.id
- `class_assignments.kelas_id` → class_channels.id
- `relators.kelas_id` → class_channels.id

## Indexes

```sql
-- Performance indexes
CREATE INDEX idx_students_nim ON students(nim);
CREATE INDEX idx_students_discord_id ON students(discord_id);
CREATE INDEX idx_students_kelas ON students(kelas);
CREATE INDEX idx_class_channels_nama ON class_channels(nama_kelas);
CREATE INDEX idx_relators_dosen ON relators(disen_discord_id);
CREATE INDEX idx_pending_reg_discord ON pending_registrations(discord_id);
CREATE INDEX idx_pending_reg_status ON pending_registrations(status);
CREATE INDEX idx_audit_event ON audit_log(event_type);
CREATE INDEX idx_audit_discord ON audit_log(discord_id);
```
```

---

## Self-Review Checklist

- [ ] **Spec coverage:** All requirements from user request are covered
- [ ] **No placeholders:** All code blocks are complete
- [ ] **Type consistency:** Model names, function signatures match across tasks
- [ ] **Permission matrix:** Covers all channel/role combinations
- [ ] **Registration flow:** Complete from join to verification
- [ ] **Relator system:** Assignment, permissions, database storage
- [ ] **Class isolation:** Students from Class A cannot see Class B

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-08-discord-channel-architecture.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration

2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
