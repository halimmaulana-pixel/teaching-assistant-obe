"""Database models for the Teaching Assistant Bot — Channel-based architecture."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .engine import Base


class Student(Base):
    """Student model — registered via Discord."""
    
    __tablename__ = "students"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    discord_id = Column(String(20), unique=True, nullable=False, index=True)
    nim = Column(String(10), unique=True, nullable=False, index=True)
    nama_lengkap = Column(String(100), nullable=False)
    prodi = Column(String(10), nullable=False)  # 'TI', 'SI', 'SD'
    angkatan = Column(Integer, nullable=False)  # 24, 25, etc.
    kelas = Column(String(10), nullable=False)  # 'A1', 'B1', 'C1'
    no_wa = Column(String(20), nullable=True)
    role = Column(String(20), default="mahasiswa")  # mahasiswa, relator, admin
    is_verified = Column(Boolean, default=False)
    verified_by = Column(String(20), nullable=True)  # admin discord_id
    verified_at = Column(DateTime, nullable=True)
    exp = Column(Integer, default=0)
    level = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    class_memberships = relationship("StudentClass", back_populates="student")
    
    def __repr__(self) -> str:
        return f"<Student {self.nim} ({self.nama_lengkap})>"


class ClassChannel(Base):
    """ClassChannel model — one per class section."""
    
    __tablename__ = "class_channels"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    nama_kelas = Column(String(50), unique=True, nullable=False, index=True)
    # e.g., "alpro-a1-si", "pweb-b2-ti"
    mata_kuliah = Column(String(100), nullable=False)
    # e.g., "Algoritma & Pemrograman"
    prodi = Column(String(10), nullable=False)  # 'TI', 'SI', 'SD'
    angkatan = Column(Integer, nullable=False)
    kelas_code = Column(String(10), nullable=False)  # 'A1', 'B1', 'C1'
    channel_id = Column(String(20), unique=True, nullable=True)  # Discord channel ID
    channel_name = Column(String(50), nullable=True)  # e.g., '#alpro-a1-si'
    role_id = Column(String(20), unique=True, nullable=True)  # Discord role ID
    role_name = Column(String(50), nullable=True)  # e.g., 'Kelas-alpro-a1-si'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    students = relationship("StudentClass", back_populates="class_channel")
    relator = relationship("Relator", back_populates="class_channel", uselist=False)
    
    def __repr__(self) -> str:
        return f"<ClassChannel {self.nama_kelas}>"


class Relator(Base):
    """Relator model — PIC per class."""
    
    __tablename__ = "relators"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dosen_discord_id = Column(String(20), unique=True, nullable=False, index=True)
    dosen_nama = Column(String(100), nullable=False)
    class_channel_id = Column(Integer, ForeignKey("class_channels.id"), nullable=False)
    assigned_by = Column(String(20), nullable=True)  # admin discord_id
    assigned_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    class_channel = relationship("ClassChannel", back_populates="relator")
    
    def __repr__(self) -> str:
        return f"<Relator {self.dosen_nama} -> {self.class_channel_id}>"


class StudentClass(Base):
    """StudentClass — mapping student to class channel."""
    
    __tablename__ = "student_classes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    class_channel_id = Column(Integer, ForeignKey("class_channels.id"), nullable=False)
    enrolled_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    student = relationship("Student", back_populates="class_memberships")
    class_channel = relationship("ClassChannel", back_populates="students")
    
    __table_args__ = (
        UniqueConstraint("student_id", "class_channel_id", name="uq_student_class"),
    )
    
    def __repr__(self) -> str:
        return f"<StudentClass {self.student_id} -> {self.class_channel_id}>"


class PendingRegistration(Base):
    """PendingRegistration — waiting for admin approval."""
    
    __tablename__ = "pending_registrations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    discord_id = Column(String(20), unique=True, nullable=False, index=True)
    discord_username = Column(String(100), nullable=True)
    nim = Column(String(10), nullable=False)
    nama_lengkap = Column(String(100), nullable=False)
    prodi = Column(String(10), nullable=False)
    angkatan = Column(Integer, nullable=False)
    kelas = Column(String(10), nullable=False)
    no_wa = Column(String(20), nullable=True)
    status = Column(String(20), default="pending")  # pending, approved, rejected
    reviewed_by = Column(String(20), nullable=True)
    review_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    
    def __repr__(self) -> str:
        return f"<PendingRegistration {self.nim} ({self.status})>"


class Badge(Base):
    """Badge model for gamification."""
    
    __tablename__ = "badges"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(10), nullable=True)  # Emoji icon
    exp_reward = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    users = relationship("UserBadge", back_populates="badge")
    
    def __repr__(self) -> str:
        return f"<Badge {self.name}>"


class UserBadge(Base):
    """User badge model for earned badges."""
    
    __tablename__ = "user_badges"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    badge_id = Column(Integer, ForeignKey("badges.id"), nullable=False)
    earned_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    student = relationship("Student")
    badge = relationship("Badge", back_populates="users")
    
    __table_args__ = (
        UniqueConstraint("student_id", "badge_id", name="uq_user_badge"),
    )
    
    def __repr__(self) -> str:
        return f"<UserBadge {self.student_id} -> {self.badge_id}>"


class Leaderboard(Base):
    """Leaderboard model for rankings."""
    
    __tablename__ = "leaderboard"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    class_channel_id = Column(Integer, ForeignKey("class_channels.id"), nullable=True)
    period = Column(String(20), nullable=False)  # weekly, monthly, alltime
    exp_earned = Column(Integer, default=0)
    rank = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    student = relationship("Student")
    class_channel = relationship("ClassChannel")
    
    __table_args__ = (
        UniqueConstraint("student_id", "class_channel_id", "period", name="uq_leaderboard"),
    )
    
    def __repr__(self) -> str:
        return f"<Leaderboard {self.student_id} ({self.period}) Rank {self.rank}>"
