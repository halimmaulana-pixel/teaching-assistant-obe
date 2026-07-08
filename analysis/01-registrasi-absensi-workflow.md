# SISTEM ANALISIS: Workflow Registrasi & Absensi Mahasiswa

**Proyek**: Discord Teaching Assistant Bot — OBE FIKTI UMSU
**Versi**: 1.0
**Tanggal**: 2026-07-08
**Status**: Production-Ready Analysis

---

## DAFTAR ISI

1. [Registrasi Mahasiswa (Full Flow)](#1-registrasi-mahasiswa-full-flow)
2. [Absensi Pertemuan (Full Flow)](#2-absensi-pertemuan-full-flow)
3. [Rekap Absensi & Alert System](#3-rekap-absensi--alert-system)
4. [Flow Diagram Lengkap](#4-flow-diagram-lengkap)
5. [Command List Detail](#5-command-list-detail)

---

## 1. REGISTRASI MAHASISWA (Full Flow)

### 1.1 Phase 1: Join Server

#### Trigger
Mahasiswa baru join Discord server FIKTI UMSU.

#### Sequence of Events

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. USER JOINS SERVER                                            │
│    - Discord assign role @everyone (default)                    │
│    - Bot event: on_member_join(member) triggered                │
├─────────────────────────────────────────────────────────────────┤
│ 2. BOT ACTIONS (within 3 seconds)                              │
│    a. Log join event to audit_log table                         │
│    b. Check if member already exists in students table          │
│    c. Send DM welcome message (embed)                           │
│    d. Send notification to #admin-logs channel                  │
│    e. Create pending_verification record                        │
├─────────────────────────────────────────────────────────────────┤
│ 3. WELCOME DM CONTENT (Embed)                                  │
│    Title: "🎓 Selamat Datang di FIKTI UMSU!"                    │
│    Fields:                                                      │
│    - Instruksi verifikasi NIM                                   │
│    - Link ke #verifikasi channel                                │
│    - Deadline verifikasi (24 jam)                               │
│    - Kontak admin jika bermasalah                               │
├─────────────────────────────────────────────────────────────────┤
│ 4. CHANNEL VISIBILITY                                           │
│    - #general: visible (read-only)                              │
│    - #verifikasi: visible (write for @everyone)                 │
│    - #pengumuman: visible (read-only)                           │
│    - All other channels: HIDDEN                                 │
├─────────────────────────────────────────────────────────────────┤
│ 5. TIMEOUT MECHANISM                                            │
│    - Scheduled task: check every 1 hour                         │
│    - If not verified within 24 hours:                           │
│      → DM reminder (24h warning)                                │
│    - If not verified within 48 hours:                           │
│      → DM final warning + mention timeout                       │
│    - If not verified within 72 hours:                           │
│      → Auto-kick from server                                    │
│      → Log to audit_log (reason: verification_timeout)          │
│      → Notify #admin-logs                                       │
└─────────────────────────────────────────────────────────────────┘
```

#### Welcome DM Template

```python
WELCOME_EMBED = Embed(
    title="🎓 Selamat Datang di Server FIKTI UMSU!",
    description=(
        "Halo {member.mention}! 👋\n\n"
        "Selamat datang di server resmi FIKTI UMSU.\n"
        "Untuk mengakses semua channel, kamu perlu **verifikasi NIM**."
    ),
    color=Color.blue(),
    fields=[
        EmbedField(
            name="📋 Langkah Verifikasi",
            value=(
                "1. Pergi ke channel <#verifikasi>\n"
                "2. Ketik `/verify [NIM_KAMU]`\n"
                "3. Ikuti instruksi selanjutnya"
            ),
            inline=False
        ),
        EmbedField(
            name="⏰ Deadline",
            value="Verifikasi harus diselesaikan dalam **24 jam**.",
            inline=True
        ),
        EmbedField(
            name="❓ Masalah?",
            value="Hubungi admin di <#bantuan>",
            inline=True
        )
    ],
    footer=Text(text="FIKTI UMSU — Teaching Assistant Bot"),
    timestamp=now()
)
```

#### Audit Log Entry

```python
# Table: audit_log
{
    "id": uuid4(),
    "event_type": "member_join",
    "discord_id": member.id,
    "username": member.name,
    "discriminator": member.discriminator,
    "joined_at": member.joined_at,
    "metadata": {
        "verification_deadline": now() + timedelta(hours=24),
        "kick_deadline": now() + timedelta(hours=72),
        "status": "pending_verification"
    },
    "created_at": now()
}
```

---

### 1.2 Phase 2: Verifikasi NIM

#### Trigger
Mahasiswa ketik `/verify [NIM]` di channel `#verifikasi`.

#### Command Syntax
```
/verify <nim:string>
```

#### Validation Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ INPUT VALIDATION (Layer 1)                                      │
├─────────────────────────────────────────────────────────────────┤
│ 1. Format NIM Check                                            │
│    Pattern: ^[0-9]{2}[0-9]{3}[0-9]{4}$                        │
│    Contoh: 2471110042 (24=angkatan, 711=prodi, 10042=nomor)   │
│    Reject: "Format NIM tidak valid. Contoh: 2471110042"        │
├─────────────────────────────────────────────────────────────────┤
│ 2. Check Database                                               │
│    Query: SELECT * FROM students WHERE nim = $1                 │
│    → Result: NOT FOUND → Go to Phase 3 (Self-Registration)     │
│    → Result: FOUND → Continue to Step 3                        │
├─────────────────────────────────────────────────────────────────┤
│ 3. Check Link Status                                            │
│    a. NOT LINKED (discord_id IS NULL):                          │
│       → Show confirmation modal                                 │
│       → "Apakah kamu [nama_mahasiswa]?"                         │
│       → If YES: link Discord ID + assign role                   │
│       → If NO: "NIM sudah terdaftar tapi bukan kamu. Hubungi admin."│
│                                                              │
│    b. LINKED TO DIFFERENT DISCORD:                              │
│       → "NIM ini sudah terhubung ke akun Discord lain."        │
│       → "Jika ini akun baru, hubungi admin untuk unlink."      │
│       → Log suspicious attempt                                  │
│                                                              │
│    c. LINKED TO THIS DISCORD:                                   │
│       → "Kamu sudah terverifikasi! Role: [role_name]"          │
│       → No action needed                                        │
└─────────────────────────────────────────────────────────────────┘
```

#### Verification Scenarios

**Scenario A: NIM Found, Not Linked**
```
Bot: "🔍 Memverifikasi NIM 2471110042..."

Bot: "✅ NIM ditemukan di database!"
     "Nama: Ahmad Fauzi"
     "Prodi: Teknik Informatika"
     "Angkatan: 2024"
     "Kelas: B1"
     
     "Apakah ini data kamu?"
     [✅ Ya, itu saya] [❌ Bukan]
```

**Scenario B: NIM Found, Already Linked**
```
Bot: "⚠️ NIM 2471110042 sudah terhubung ke akun Discord."
     "Jika ini akun baru kamu, silakan hubungi admin."
     "Jika kamu mengalami masalah, buka tiket di #bantuan."
```

**Scenario C: NIM Not Found**
```
Bot: "❌ NIM 2471110042 tidak ditemukan di database FIKTI."
     
     "Apakah kamu ingin mendaftar secara manual?"
     [📝 Ya, daftar manual] [❌ Batal]
```

#### Role Assignment (After Verification)

```python
# Role assignment logic
def assign_roles(member, student):
    roles_to_add = []
    
    # 1. Base verified role
    roles_to_add.append(get_role("Mahasiswa Verified"))
    
    # 2. Angkatan role
    angkatan = student.nim[:2]  # First 2 digits
    roles_to_add.append(get_role(f"Angkatan {angkatan}"))
    
    # 3. Program Studi role
    prodi_code = student.nim[2:5]  # Digits 3-5
    prodi_map = {
        "711": "Teknik Informatika",
        "712": "Sistem Informasi",
        "713": "Teknologi Informasi"
    }
    prodi_name = prodi_map.get(prodi_code, "Unknown")
    roles_to_add.append(get_role(prodi_name))
    
    # 4. Kelas role
    if student.kelas:
        roles_to_add.append(get_role(f"Kelas {student.kelas}"))
    
    # Apply roles
    await member.add_roles(*roles_to_add)
    
    # Log role assignment
    log_audit("role_assigned", member.id, {
        "roles": [r.name for r in roles_to_add],
        "student_id": student.id
    })
```

#### Verification Token (Optional — Email OTP)

```
Jika diperlukan verifikasi email kampus:

1. Bot generate 6-digit OTP
2. Bot query: SELECT email FROM students WHERE nim = $1
3. Bot send email via SMTP:
   Subject: "Verifikasi Akun Discord FIKTI UMSU"
   Body: "Kode verifikasi kamu: {otp}"
   Expires: 10 minutes
4. Mahasiswa ketik: /verify-otp [kode]
5. Bot validate OTP + mark email_verified = true
6. Proceed with role assignment
```

---

### 1.3 Phase 3: Self-Registration Flow

#### Trigger
Mahasiswa pilih "📝 Ya, daftar manual" setelah NIM tidak ditemukan.

#### Registration Modal (Discord Modal)

```python
class RegistrationModal(Modal, title="📝 Registrasi Mahasiswa"):
    nim = TextInput(
        label="NIM",
        placeholder="2471110042",
        style=TextInputStyle.short,
        required=True,
        max_length=10,
        min_length=10
    )
    
    nama_lengkap = TextInput(
        label="Nama Lengkap",
        placeholder="Ahmad Fauzi",
        style=TextInputStyle.short,
        required=True,
        max_length=100
    )
    
    angkatan = TextInput(
        label="Angkatan",
        placeholder="2024",
        style=TextInputStyle.short,
        required=True,
        max_length=4
    )
    
    prodi = TextInput(
        label="Program Studi",
        placeholder="Teknik Informatika",
        style=TextInputStyle.short,
        required=True
    )
    
    kelas = TextInput(
        label="Kelas",
        placeholder="B1",
        style=TextInputStyle.short,
        required=True,
        max_length=5
    )
```

#### Validation Rules

```python
VALIDATION_RULES = {
    "nim": {
        "pattern": r"^[0-9]{10}$",
        "custom_check": validate_nim_structure,
        "error_messages": {
            "pattern": "NIM harus 10 digit angka",
            "structure": "Struktur NIM tidak valid (angkatan-prodi-nomor)"
        }
    },
    "nama_lengkap": {
        "min_length": 3,
        "max_length": 100,
        "pattern": r"^[a-zA-Z\s]+$",
        "error_messages": {
            "pattern": "Nama hanya boleh huruf dan spasi"
        }
    },
    "angkatan": {
        "pattern": r"^(20[0-2][0-9])$",
        "range_check": lambda x: 2020 <= int(x) <= 2030,
        "error_messages": {
            "pattern": "Angkatan harus format YYYY (2020-2030)"
        }
    },
    "prodi": {
        "allowed_values": [
            "Teknik Informatika",
            "Sistem Informasi", 
            "Teknologi Informasi"
        ],
        "error_messages": {
            "allowed": "Prodi harus salah satu dari: TI, SI, TI"
        }
    },
    "kelas": {
        "pattern": r"^[A-Z][0-9]{1,2}$",
        "error_messages": {
            "pattern": "Format kelas: huruf + angka (contoh: B1, A12)"
        }
    }
}
```

#### NIM Structure Validation

```python
def validate_nim_structure(nim: str) -> tuple[bool, str]:
    """
    Validasi struktur NIM UMSU:
    - 2 digit pertama: angkatan (YY)
    - 3 digit berikutnya: prodi (711=TI, 712=SI, 713=TI)
    - 5 digit terakhir: nomor urut
    
    Contoh: 2471110042
    - 24 = angkatan 2024
    - 711 = Teknik Informatika
    - 0042 = nomor urut 42
    """
    angkatan = int(nim[:2])
    prodi_code = nim[2:5]
    nomor_urut = int(nim[5:])
    
    # Validate angkatan
    if not (20 <= angkatan <= 30):
        return False, "Angkatan tidak valid (20-30)"
    
    # Validate prodi
    valid_prodi = {"711", "712", "713"}
    if prodi_code not in valid_prodi:
        return False, f"Kode prodi tidak valid: {prodi_code}"
    
    # Validate nomor urut
    if not (1 <= nomor_urut <= 99999):
        return False, "Nomor urut tidak valid"
    
    return True, "Valid"
```

#### Pending Registration Record

```sql
-- Insert ke pending_registrations
INSERT INTO pending_registrations (
    id,
    discord_id,
    discord_username,
    nim,
    nama_lengkap,
    angkatan,
    prodi,
    kelas,
    status,
    submitted_at,
    expires_at
) VALUES (
    uuid_generate_v4(),
    '123456789012345678',  -- discord_id
    'ahmad_fauzi',
    '2471110042',
    'Ahmad Fauzi',
    2024,
    'Teknik Informatika',
    'B1',
    'pending',
    NOW(),
    NOW() + INTERVAL '48 hours'  -- expires in 48h
);
```

#### Admin Notification

```python
# Send to #admin-registrations channel
ADMIN_EMBED = Embed(
    title="📝 Registrasi Baru Menunggu Persetujuan",
    color=Color.yellow(),
    fields=[
        EmbedField(name="Discord", value=f"<@{discord_id}>", inline=True),
        EmbedField(name="NIM", value=nim, inline=True),
        EmbedField(name="Nama", value=nama_lengkap, inline=True),
        EmbedField(name="Prodi", value=prodi, inline=True),
        EmbedField(name="Kelas", value=kelas, inline=True),
        EmbedField(name="Angkatan", value=str(angkatan), inline=True),
        EmbedField(name="Waktu", value=format_time(submitted_at), inline=True),
        EmbedField(
            name="Aksi",
            value=(
                f"[✅ Approve](approve:{pending_id}) | "
                f"[❌ Reject](reject:{pending_id}) | "
                f"[👤 Verify](verify:{pending_id})"
            ),
            inline=False
        )
    ],
    footer=Text(text=f"ID: {pending_id}")
)

await admin_channel.send(embed=ADMIN_EMBED)
```

#### Admin Actions

**Approve Flow:**
```
1. Admin klik [✅ Approve]
2. Bot create record di students table
3. Bot assign roles ke member
4. Bot DM mahasiswa: "✅ Registrasi disetujui! Kamu sekarang terverifikasi."
5. Bot update pending_registrations.status = 'approved'
6. Bot log ke audit_log
```

**Reject Flow:**
```
1. Admin klik [❌ Reject]
2. Bot open modal for rejection reason
3. Admin isi alasan penolakan
4. Bot DM mahasiswa: "❌ Registrasi ditolak. Alasan: [reason]"
5. Bot update pending_registrations.status = 'rejected'
6. Bot log ke audit_log
```

---

### 1.4 Database Tables (Registration)

```sql
-- ============================================
-- TABLE: students
-- ============================================
CREATE TABLE students (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nim VARCHAR(10) UNIQUE NOT NULL,
    nama_lengkap VARCHAR(100) NOT NULL,
    angkatan INTEGER NOT NULL,
    prodi VARCHAR(50) NOT NULL,
    kelas VARCHAR(5) NOT NULL,
    discord_id BIGINT UNIQUE,
    discord_username VARCHAR(100),
    email VARCHAR(100),
    is_verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMPTZ,
    verified_by VARCHAR(50),  -- 'self', 'admin', 'otp'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT chk_nim_format CHECK (nim ~ '^[0-9]{10}$'),
    CONSTRAINT chk_angkatan CHECK (angkatan >= 2020 AND angkatan <= 2030),
    CONSTRAINT chk_prodi CHECK (prodi IN (
        'Teknik Informatika',
        'Sistem Informasi',
        'Teknologi Informasi'
    ))
);

-- Indexes
CREATE INDEX idx_students_nim ON students(nim);
CREATE INDEX idx_students_discord_id ON students(discord_id);
CREATE INDEX idx_students_angkatan ON students(angkatan);
CREATE INDEX idx_students_kelas ON students(kelas);

-- ============================================
-- TABLE: pending_registrations
-- ============================================
CREATE TABLE pending_registrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    discord_id BIGINT NOT NULL,
    discord_username VARCHAR(100) NOT NULL,
    nim VARCHAR(10) NOT NULL,
    nama_lengkap VARCHAR(100) NOT NULL,
    angkatan INTEGER NOT NULL,
    prodi VARCHAR(50) NOT NULL,
    kelas VARCHAR(5) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, approved, rejected, expired
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    reviewed_by VARCHAR(100),
    rejection_reason TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT chk_status CHECK (status IN ('pending', 'approved', 'rejected', 'expired'))
);

-- Indexes
CREATE INDEX idx_pending_reg_discord ON pending_registrations(discord_id);
CREATE INDEX idx_pending_reg_status ON pending_registrations(status);
CREATE INDEX idx_pending_reg_expires ON pending_registrations(expires_at);

-- ============================================
-- TABLE: verification_tokens
-- ============================================
CREATE TABLE verification_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    discord_id BIGINT NOT NULL,
    nim VARCHAR(10) NOT NULL,
    token VARCHAR(6) NOT NULL,
    token_type VARCHAR(20) NOT NULL,  -- 'otp', 'email_verify', 'password_reset'
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT chk_token_type CHECK (token_type IN (
        'otp', 'email_verify', 'password_reset'
    ))
);

-- Indexes
CREATE INDEX idx_verification_discord ON verification_tokens(discord_id);
CREATE INDEX idx_verification_token ON verification_tokens(token);
CREATE INDEX idx_verification_expires ON verification_tokens(expires_at);

-- ============================================
-- TABLE: audit_log
-- ============================================
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(50) NOT NULL,
    discord_id BIGINT,
    actor_id BIGINT,  -- who performed the action
    metadata JSONB,
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_audit_event_type ON audit_log(event_type);
CREATE INDEX idx_audit_discord ON audit_log(discord_id);
CREATE INDEX idx_audit_created ON audit_log(created_at);
```

---

## 2. ABSENSI PERTEMUAN (Full Flow)

### 2.1 Scenario A: Absensi Tatap Muka (Offline)

#### Pre-Class Setup

```
┌─────────────────────────────────────────────────────────────────┐
│ DOSEN SETUP (Sebelum Kuliah)                                    │
├─────────────────────────────────────────────────────────────────┤
│ 1. Dosen ketik: /mulai-kuliah [kelas] [mata_kuliah]            │
│                                                              │
│ 2. Bot validasi:                                              │
│    a. Apakah dosen mengampu mata kuliah ini?                  │
│    b. Apakah ada jadwal kuliah untuk kelas ini hari ini?      │
│    c. Apakah sudah ada session aktif untuk kelas ini?         │
│                                                              │
│ 3. Bot create attendance_session record:                      │
│    - class_id: dari classes table                              │
│    - course_id: dari courses table                             │
│    - session_date: today                                       │
│    - session_type: 'offline'                                   │
│    - opens_at: NOW()                                           │
│    - closes_at: NOW() + 15 minutes (adjustable)               │
│    - status: 'open'                                            │
│    - started_by: dosen.discord_id                              │
│                                                              │
│ 4. Bot kirim embed ke #absensi-[kelas]:                       │
│    "🎓 Kuliah [mata_kuliah] dimulai!"                          │
│    "Klik tombol 'Hadir' dalam 15 menit."                      │
│    [🟢 Hadir] button                                           │
└─────────────────────────────────────────────────────────────────┘
```

#### Attendance Embed Template

```python
ATTENDANCE_EMBED = Embed(
    title="🎓 Kuliah Dimulai!",
    description=f"**{course_name}** — {class_name}",
    color=Color.green(),
    fields=[
        EmbedField(name="Dosen", value= lecturer_name, inline=True),
        EmbedField(name="Waktu", value=format_time(now()), inline=True),
        EmbedField(name="Sisa Waktu", value="15:00", inline=True),
        EmbedField(
            name="Instruksi",
            value="Klik tombol **Hadir** di bawah untuk absen.",
            inline=False
        )
    ],
    footer=Text(text=f"Session ID: {session_id}"),
    timestamp=closes_at
)

# Attendance button
view = View(timeout=900)  # 15 minutes
button = Button(
    label="🟢 Hadir",
    style=ButtonStyle.green,
    custom_id=f"attend_{session_id}"
)
view.add_item(button)

await attendance_channel.send(embed=ATTENDANCE_EMBED, view=view)
```

#### Attendance Check Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ MAHASISWA KLIK "HADIR"                                         │
├─────────────────────────────────────────────────────────────────┤
│ 1. INTERACTION DEFDGuard: time_window, already_absent, valid_code│
│                                                              │
│ Guard Conditions:                                              │
│ ├─► Is session open? (status == 'open')                       │
│ │   └─ NO → "❌ Sesi absensi belum dibuka atau sudah ditutup." │
│ │                                                              │
│ ├─► Is within time window?                                     │
│ │   NOW() BETWEEN opens_at AND closes_at                       │
│ │   └─ NO → "⏰ Waktu absensi sudah habis."                    │
│ │                                                              │
│ ├─► Already checked in?                                        │
│ │   SELECT 1 FROM attendance_records                           │
│ │   WHERE session_id = X AND student_id = Y                    │
│ │   └─ YES → "⚠️ Kamu sudah absen untuk sesi ini."            │
│ │                                                              │
│ ├─► Is student enrolled in this class?                         │
│ │   SELECT 1 FROM enrollments                                  │
│ │   WHERE student_id = Y AND class_id = X                      │
│ │   └─ NO → "❌ Kamu tidak terdaftar di kelas ini."           │
│ │                                                              │
│ └─► All checks passed → Process attendance                    │
├─────────────────────────────────────────────────────────────────┤
│ 2. DETERMINE STATUS                                            │
│    check_time = NOW()                                          │
│    opens_at = session.opens_at                                 │
│    class_start = scheduled_class_time                          │
│                                                              │
│    IF check_time <= class_start:                               │
│        status = 'present'                                      │
│    ELIF check_time <= class_start + 15 minutes:                │
│        status = 'late'                                         │
│    ELSE:                                                       │
│        status = 'late'  # Still within window but late         │
├─────────────────────────────────────────────────────────────────┤
│ 3. CREATE ATTENDANCE RECORD                                    │
│    INSERT INTO attendance_records (                            │
│        id, session_id, student_id, status,                     │
│        check_in_time, check_method, exp_earned                 │
│    ) VALUES (                                                  │
│        uuid_generate_v4(),                                     │
│        session_id,                                             │
│        student_id,                                             │
│        status,  -- 'present' or 'late'                         │
│        NOW(),                                                  │
│        'button',                                               │
│        CASE WHEN status = 'present' THEN 10 ELSE 5 END        │
│    );                                                          │
├─────────────────────────────────────────────────────────────────┤
│ 4. TRIGGER GAMIFICATION                                        │
│    a. Add EXP to student                                       │
│    b. Check level up                                           │
│    c. Check badge eligibility                                  │
│    d. Update attendance_summary                                │
├─────────────────────────────────────────────────────────────────┤
│ 5. RESPOND TO USER                                             │
│    IF status == 'present':                                     │
│        "✅ Absensi berhasil! +10 EXP 🎉"                       │
│    ELIF status == 'late':                                      │
│        "⚠️ Absensi tercatat (terlambat). +5 EXP"              │
│                                                              │
│    Response: ephemeral=True (only visible to user)             │
└─────────────────────────────────────────────────────────────────┘
```

#### End of Class

```
┌─────────────────────────────────────────────────────────────────┐
│ DOSEN TUTUP KULIAH                                             │
├─────────────────────────────────────────────────────────────────┤
│ 1. Dosen ketik: /tutup-kuliah                                  │
│                                                              │
│ 2. Bot validasi:                                              │
│    a. Apakah ada session aktif untuk dosen ini?               │
│    b. Apakah dosen yang start session ini?                    │
│                                                              │
│ 3. Bot update session:                                        │
│    - status = 'closed'                                         │
│    - closes_at = NOW()                                         │
│                                                              │
│ 4. Bot generate rekap:                                        │
│    SELECT                                                      │
│        ar.status,                                              │
│        COUNT(*) as count,                                      │
│        s.nama_lengkap                                          │
│    FROM attendance_records ar                                  │
│    JOIN students s ON ar.student_id = s.id                     │
│    WHERE ar.session_id = $1                                    │
│    GROUP BY ar.status                                          │
│                                                              │
│ 5. Bot kirim rekap ke #absensi-[kelas]:                       │
│    📊 **Rekap Absensi**                                        │
│    🟢 Hadir: 25 mahasiswa                                      │
│    🟡 Terlambat: 3 mahasiswa                                   │
│    🔴 Tidak Hadir: 5 mahasiswa                                 │
│    ❌ Belum Absen: 2 mahasiswa                                  │
│                                                              │
│ 6. Bot DM mahasiswa yang belum absen:                          │
│    "⚠️ Kamu tidak hadir di kuliah [mata_kuliah] hari ini."    │
└─────────────────────────────────────────────────────────────────┘
```

---

### 2.2 Scenario B: Absensi Online (Hybrid)

#### Voice Channel Monitoring

```
┌─────────────────────────────────────────────────────────────────┐
│ VOICE CHANNEL ATTENDANCE                                        │
├─────────────────────────────────────────────────────────────────┤
│ 1. SETUP                                                       │
│    - Dosen tentukan voice channel untuk kelas                  │
│    - Bot monitor voice_state_update events                      │
│    - Minimum time threshold: 30 menit                          │
├─────────────────────────────────────────────────────────────────┤
│ 2. MONITORING LOOP                                             │
│    Event: on_voice_state_update(member, before, after)         │
│                                                              │
│    IF member joins target voice channel:                       │
│        - Log join time                                         │
│        - Start timer                                           │
│        - If timer >= 30 minutes:                               │
│            → Auto-mark as 'present'                            │
│            → Send notification to member                       │
│                                                              │
│    IF member leaves voice channel:                             │
│        - Calculate duration                                    │
│        - If duration < 30 minutes:                             │
│            → Don't count                                       │
│            → Send warning                                      │
│        - If duration >= 30 minutes:                            │
│            → Mark as 'present' (if not already)                │
├─────────────────────────────────────────────────────────────────┤
│ 3. STATE TRACKING                                              │
│    voice_sessions = {                                          │
│        member_id: {                                            │
│            channel_id: channel.id,                             │
│            join_time: datetime,                                │
│            duration: timedelta,                                │
│            counted: bool                                       │
│        }                                                       │
│    }                                                           │
├─────────────────────────────────────────────────────────────────┤
│ 4. MANUAL BACKUP                                               │
│    - Mahasiswa bisa juga klik "Hadir" button                   │
│    - Voice attendance is PRIMARY                               │
│    - Button attendance is BACKUP                               │
│    - No double counting (dedup by session_id + student_id)     │
└─────────────────────────────────────────────────────────────────┘
```

#### Voice Monitoring Implementation

```python
class VoiceMonitor:
    def __init__(self):
        self.active_sessions: dict[int, VoiceSession] = {}
    
    async def on_voice_state_update(
        self, 
        member: Member, 
        before: VoiceState, 
        after: VoiceState
    ):
        # Check if this is a monitored channel
        if after.channel and after.channel.id in MONITORED_CHANNELS:
            await self.handle_join(member, after.channel)
        
        if before.channel and before.channel.id in MONITORED_CHANNELS:
            await self.handle_leave(member, before.channel)
    
    async def handle_join(self, member: Member, channel: VoiceChannel):
        session = VoiceSession(
            member_id=member.id,
            channel_id=channel.id,
            join_time=datetime.now(),
            duration=timedelta(0),
            counted=False
        )
        self.active_sessions[member.id] = session
        
        # Start background task to check duration
        asyncio.create_task(self.check_duration(member.id))
    
    async def check_duration(self, member_id: int):
        await asyncio.sleep(1800)  # 30 minutes
        
        if member_id in self.active_sessions:
            session = self.active_sessions[member_id]
            if not session.counted:
                await self.mark_attendance(member_id, session)
    
    async def mark_attendance(
        self, 
        member_id: int, 
        session: VoiceSession
    ):
        # Get active attendance session for this channel
        attendance_session = await get_active_session(session.channel_id)
        
        if attendance_session:
            # Check if already marked
            existing = await check_existing_attendance(
                attendance_session.id, 
                member_id
            )
            
            if not existing:
                await create_attendance_record(
                    session_id=attendance_session.id,
                    student_id=member_id,
                    status='present',
                    check_method='voice',
                    check_in_time=session.join_time
                )
                session.counted = True
                
                # Notify member
                member = self.bot.get_user(member_id)
                await member.send(
                    "✅ Kehadiranmu tercatat via voice channel! +10 EXP"
                )
```

---

### 2.3 Scenario C: Absensi Online (Fully Remote)

#### Code-Based Attendance

```
┌─────────────────────────────────────────────────────────────────┐
│ CODE-BASED ATTENDANCE                                           │
├─────────────────────────────────────────────────────────────────┤
│ 1. DOSEN GENERATE KODE                                         │
│    /buat-kode-absen [kelas] [mata_kuliah]                      │
│                                                              │
│    Bot generate kode unik:                                     │
│    - Format: 6 karakter alphanumeric                          │
│    - Contoh: "A7B3K9"                                         │
│    - Valid for: 15 minutes                                     │
│    - One code per session                                      │
│                                                              │
│    Bot kirim ke DM dosen:                                      │
│    "🔐 Kode absensi: A7B3K9"                                   │
│    "Berlaku sampai: 10:15 WIB"                                 │
│                                                              │
│ 2. DOSEN BAGIKAN KODE                                          │
│    - Via Google Meet chat                                      │
│    - Via WhatsApp group                                        │
│    - Via other platform                                        │
├─────────────────────────────────────────────────────────────────┤
│ 3. MAHASISWA INPUT KODE                                        │
│    /absen [kode]                                               │
│                                                              │
│    Bot validasi:                                               │
│    a. Format kode valid? (6 alphanumeric)                      │
│    b. Kode exists in database?                                 │
│    c. Kode expired? (check expires_at)                         │
│    d. Mahasiswa already absen for this session?                │
│    e. Mahasiswa enrolled in this class?                        │
├─────────────────────────────────────────────────────────────────┤
│ 4. KODE GENERATION STRATEGY                                    │
│    Option A: Static code per session (simpler)                 │
│    - One code generated at session start                       │
│    - Valid until session closes                                │
│    - Risk: code can be shared                                  │
│                                                              │
│    Option B: Rotating code (more secure)                       │
│    - New code every 5 minutes                                  │
│    - Previous codes still valid                                │
│    - More complex to manage                                    │
│                                                              │
│    Option C: Unique code per student (most secure)             │
│    - Each student gets unique code                             │
│    - Most secure but complex                                   │
│    - Not practical for large classes                           │
│                                                              │
│    RECOMMENDATION: Option A with time window                   │
└─────────────────────────────────────────────────────────────────┘
```

#### Code Validation Flow

```python
async def validate_attendance_code(
    student_id: str, 
    code: str, 
    session_id: str
) -> tuple[bool, str, str]:
    """
    Returns: (is_valid, status, message)
    """
    # 1. Format check
    if not re.match(r'^[A-Z0-9]{6}$', code):
        return False, 'error', 'Format kode tidak valid'
    
    # 2. Query session
    session = await db.fetchrow(
        """
        SELECT * FROM attendance_sessions 
        WHERE id = $1 AND status = 'open'
        """,
        session_id
    )
    
    if not session:
        return False, 'error', 'Sesi absensi tidak ditemukan'
    
    # 3. Check code match
    if session['attendance_code'] != code:
        return False, 'error', 'Kode absensi salah'
    
    # 4. Check time window
    now = datetime.now(timezone.utc)
    if now > session['closes_at']:
        return False, 'error', 'Waktu absensi sudah habis'
    
    # 5. Check if already checked in
    existing = await db.fetchrow(
        """
        SELECT 1 FROM attendance_records 
        WHERE session_id = $1 AND student_id = $2
        """,
        session_id, student_id
    )
    
    if existing:
        return False, 'error', 'Kamu sudah absen untuk sesi ini'
    
    # 6. Check enrollment
    enrolled = await db.fetchrow(
        """
        SELECT 1 FROM enrollments 
        WHERE student_id = $1 AND class_id = $2
        """,
        student_id, session['class_id']
    )
    
    if not enrolled:
        return False, 'error', 'Kamu tidak terdaftar di kelas ini'
    
    # All checks passed
    return True, 'valid', 'Kode valid'
```

---

### 2.4 State Machine Absensi

```
┌─────────────────────────────────────────────────────────────────┐
│                    ATTENDANCE STATE MACHINE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    start_session    ┌──────────┐                  │
│  │          │ ──────────────────► │          │                  │
│  │NOT_START │                     │   OPEN   │                  │
│  │          │ ◄────────────────── │          │                  │
│  └──────────┘    close_session    └────┬─────┘                  │
│                                        │                        │
│                                        │ close_session          │
│                                        ▼                        │
│                                  ┌──────────┐                   │
│                                  │          │                   │
│                                  │ CLOSED   │                   │
│                                  │          │                   │
│                                  └────┬─────┘                   │
│                                       │                         │
│                                       │ calculate_grade         │
│                                       ▼                         │
│                                  ┌──────────┐                   │
│                                  │          │                   │
│                                  │ GRADED   │                   │
│                                  │          │                   │
│                                  └──────────┘                   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ TRANSITIONS:                                                    │
│                                                                 │
│ NOT_STARTED → OPEN                                             │
│   Trigger: /mulai-kuliah command                                │
│   Guard: !session_exists_for_class_today                        │
│   Action: create_session, send_embed, start_timer               │
│                                                                 │
│ OPEN → CLOSED                                                   │
│   Trigger: /tutup-kuliah command OR auto-close timer            │
│   Guard: session.status == 'open'                               │
│   Action: update_status, generate_report, notify_absent         │
│                                                                 │
│ CLOSED → GRADED                                                │
│   Trigger: /hitung-nilai command OR scheduled_job               │
│   Guard: session.status == 'closed'                             │
│   Action: calculate_attendance_score, update_student_record     │
│                                                                 │
│ GRADED → (terminal)                                             │
│   No further transitions                                        │
└─────────────────────────────────────────────────────────────────┘
```

#### State Definitions

```python
class AttendanceState(Enum):
    NOT_STARTED = "not_started"
    OPEN = "open"
    CLOSED = "closed"
    GRADED = "graded"

class AttendanceTransition:
    """Defines valid state transitions"""
    TRANSITIONS = {
        AttendanceState.NOT_STARTED: {
            'start_session': AttendanceState.OPEN
        },
        AttendanceState.OPEN: {
            'close_session': AttendanceState.CLOSED
        },
        AttendanceState.CLOSED: {
            'calculate_grade': AttendanceState.GRADED
        },
        AttendanceState.GRADED: {}
    }
    
    @classmethod
    def can_transition(
        cls, 
        current: AttendanceState, 
        action: str
    ) -> bool:
        return action in cls.TRANSITIONS.get(current, {})
    
    @classmethod
    def get_next_state(
        cls, 
        current: AttendanceState, 
        action: str
    ) -> Optional[AttendanceState]:
        if cls.can_transition(current, action):
            return cls.TRANSITIONS[current][action]
        return None
```

---

### 2.5 Edge Cases & Error Handling

```
┌─────────────────────────────────────────────────────────────────┐
│ EDGE CASE 1: Absen di Kelas yang Salah                          │
├─────────────────────────────────────────────────────────────────┤
│ Scenario: Mahasiswa klik "Hadir" di embed kelas A, tapi dia    │
│           terdaftar di kelas B.                                  │
│                                                              │
│ Detection:                                                    │
│   SELECT 1 FROM enrollments                                   │
│   WHERE student_id = $1 AND class_id = $2                     │
│                                                              │
│ Response:                                                     │
│   "❌ Kamu tidak terdaftar di kelas [Kelas A]."               │
│   "Kamu terdaftar di kelas [Kelas B]."                         │
│                                                              │
│ Action:                                                       │
│   - Log event (suspicious activity)                            │
│   - Do NOT create attendance record                            │
│   - Notify admin if repeated (3x in 1 week)                   │
├─────────────────────────────────────────────────────────────────┤
│ EDGE CASE 2: Absen Tepat Detik Terakhir                        │
├─────────────────────────────────────────────────────────────────┤
│ Scenario: Mahasiswa klik "Hadir" tepat saat window berakhir.   │
│                                                              │
│ Technical Issue:                                               │
│   - Network latency bisa menyebabkan race condition           │
│   - Button click mungkin terkirim sebelum timeout             │
│                                                              │
│ Solution:                                                     │
│   - Use server-side time (not client-side)                    │
│   - Add 1-second buffer:                                       │
│     if NOW() <= closes_at + INTERVAL '1 second':              │
│         accept_attendance()                                    │
│   - Log exact timestamp for audit                              │
│                                                              │
│ Response:                                                     │
│   - If within buffer: "✅ Absensi diterima (tepat waktu)"     │
│   - If outside buffer: "⏰ Waktu absensi sudah berakhir"      │
├─────────────────────────────────────────────────────────────────┤
│ EDGE CASE 3: Discord Down Saat Absensi                         │
├─────────────────────────────────────────────────────────────────┤
│ Scenario: Discord API down, mahasiswa tidak bisa klik button.  │
│                                                              │
│ Detection:                                                     │
│   - Bot monitor its own connectivity                           │
│   - Use health check endpoint                                  │
│   - Track failed interactions                                 │
│                                                              │
│ Mitigation:                                                   │
│   a. Automatic recovery:                                       │
│      - When Discord comes back, extend window by downtime      │
│      - Send notification to all affected                       │
│                                                              │
│   b. Manual override:                                          │
│      - Dosen bisa /manual-absen [mahasiswa] [alasan]          │
│      - Admin bisa bulk override                                │
│                                                              │
│   c. Backup channel:                                           │
│      - Use email/Google Form as fallback                       │
│      - Bot process submissions later                           │
│                                                              │
│   d. Compensation:                                             │
│      - If downtime > 30 minutes, session auto-extended         │
│      - If downtime during critical window, new session created │
├─────────────────────────────────────────────────────────────────┤
│ EDGE CASE 4: Claim Absen Tapi Data Tidak Ada                   │
├─────────────────────────────────────────────────────────────────┤
│ Scenario: Mahasiswa bilang "Sudah absen tapi kok tidak ada?"   │
│                                                              │
│ Investigation Steps:                                           │
│   1. Query attendance_records for session + student            │
│   2. Check audit_log for interaction events                    │
│   3. Check if record was deleted (shouldn't be possible)       │
│   4. Check network logs (did interaction succeed?)             │
│                                                              │
│ Resolution:                                                   │
│   a. If record exists: show proof to mahasiswa                 │
│   b. If record missing but logs show success:                  │
│      - Possible database sync issue                            │
│      - Admin can manually insert with note                     │
│   c. If no evidence of attendance:                             │
│      - Explain to mahasiswa                                    │
│      - Offer manual override if dosen approves                 │
│                                                              │
│ Prevention:                                                   │
│   - Always send confirmation DM after attendance               │
│   - Store interaction_id for every attendance                  │
│   - Keep audit trail for 1 year minimum                        │
├─────────────────────────────────────────────────────────────────┤
│ EDGE CASE 5: Dosen Lupa Buka Session                           │
├─────────────────────────────────────────────────────────────────┤
│ Scenario: Jadwal kuliah sudah lewat, tapi dosen tidak /mulai.  │
│                                                              │
│ Auto-Detection:                                                │
│   - Scheduled task checks every 5 minutes                      │
│   - Compare current time vs class schedule                     │
│   - If class should have started but no session:               │
│     → Notify dosen via DM                                      │
│     → Notify admin                                             │
│                                                              │
│ Notification:                                                  │
│   "⚠️ Kuliah [mata_kuliah] kelas [X] sudah dimulai 15         │
│    menit yang lalu. Gunakan /mulai-kuliah untuk membuka        │
│    sesi absensi."                                               │
│                                                              │
│ Auto-Recovery:                                                 │
│   - If no session after 30 minutes:                            │
│     → Create session automatically with default settings       │
│     → Notify admin for manual adjustment                       │
├─────────────────────────────────────────────────────────────────┤
│ EDGE CASE 6: Double Session                                     │
├─────────────────────────────────────────────────────────────────┤
│ Scenario: Dosen accidentally run /mulai-kuliah 2x.            │
│                                                              │
│ Prevention:                                                    │
│   - Check for existing active session before creating          │
│   - IF EXISTS:                                                 │
│     → "⚠️ Sesi absensi untuk kelas [X] sudah aktif."         │
│     → Show details of existing session                         │
│     → Offer option to close existing and start new             │
│                                                              │
│ If Already Created:                                             │
│   - Only allow one active session per class per day            │
│   - Database constraint: UNIQUE(class_id, session_date,        │
│                                  status='open')                │
├─────────────────────────────────────────────────────────────────┤
│ EDGE CASE 7: Kuliah Pengganti / Jadwal Changed                 │
├─────────────────────────────────────────────────────────────────┤
│ Scenario: Jadwal kuliah dipindah ke hari lain / jam lain.      │
│                                                              │
│ Solution:                                                      │
│   - Dosen bisa create ad-hoc session:                          │
│     /kuliah-pengganti [kelas] [mata_kuliah] [ tanggal_baru ]  │
│   - Bot create session with custom datetime                    │
│   - Normal attendance flow applies                             │
│                                                              │
│ Note:                                                          │
│   - This session counts toward total attendance                │
│   - Attendance rate calculation includes ad-hoc sessions       │
│   - Admin can modify if needed                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 2.6 Database Schema (Attendance)

```sql
-- ============================================
-- TABLE: classes
-- ============================================
CREATE TABLE classes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL,  -- "B1", "A12"
    angkatan INTEGER NOT NULL,
    program_studi VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT UNIQUE_class_per_program UNIQUE (name, angkatan, program_studi)
);

-- ============================================
-- TABLE: courses
-- ============================================
CREATE TABLE courses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(20) UNIQUE NOT NULL,  -- "IF101"
    name VARCHAR(100) NOT NULL,
    credits INTEGER NOT NULL,
    program_studi VARCHAR(50) NOT NULL,
    semester INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- TABLE: enrollments
-- ============================================
CREATE TABLE enrollments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    class_id UUID REFERENCES classes(id) ON DELETE CASCADE,
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    semester VARCHAR(20) NOT NULL,  -- "2024/2025-Ganjil"
    enrolled_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT UNIQUE_enrollment UNIQUE (student_id, course_id, semester)
);

-- Indexes
CREATE INDEX idx_enrollments_student ON enrollments(student_id);
CREATE INDEX idx_enrollments_class ON enrollments(class_id);
CREATE INDEX idx_enrollments_course ON enrollments(course_id);

-- ============================================
-- TABLE: course_schedules
-- ============================================
CREATE TABLE course_schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    class_id UUID REFERENCES classes(id) ON DELETE CASCADE,
    lecturer_id UUID REFERENCES users(id),
    day_of_week INTEGER NOT NULL,  -- 0=Sunday, 1=Monday, ...
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    room VARCHAR(50),
    voice_channel_id BIGINT,  -- Discord voice channel ID
    semester VARCHAR(20) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT chk_day CHECK (day_of_week >= 0 AND day_of_week <= 6),
    CONSTRAINT chk_time CHECK (start_time < end_time)
);

-- ============================================
-- TABLE: attendance_sessions
-- ============================================
CREATE TABLE attendance_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    class_id UUID REFERENCES classes(id) ON DELETE CASCADE,
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    schedule_id UUID REFERENCES course_schedules(id),
    session_date DATE NOT NULL,
    session_type VARCHAR(20) NOT NULL,  -- 'offline', 'online', 'hybrid'
    opens_at TIMESTAMPTZ NOT NULL,
    closes_at TIMESTAMPTZ NOT NULL,
    attendance_code VARCHAR(10),  -- for code-based attendance
    status VARCHAR(20) DEFAULT 'pending',  -- pending, open, closed, graded
    started_by BIGINT REFERENCES users(discord_id),
    total_present INTEGER DEFAULT 0,
    total_late INTEGER DEFAULT 0,
    total_absent INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    
    CONSTRAINT chk_session_status CHECK (status IN (
        'pending', 'open', 'closed', 'graded'
    )),
    CONSTRAINT chk_session_type CHECK (session_type IN (
        'offline', 'online', 'hybrid'
    )),
    CONSTRAINT chk_time_range CHECK (opens_at < closes_at)
);

-- Indexes
CREATE INDEX idx_sessions_class ON attendance_sessions(class_id);
CREATE INDEX idx_sessions_course ON attendance_sessions(course_id);
CREATE INDEX idx_sessions_date ON attendance_sessions(session_date);
CREATE INDEX idx_sessions_status ON attendance_sessions(status);
CREATE INDEX idx_sessions_started_by ON attendance_sessions(started_by);

-- Unique constraint: only one open session per class per day
CREATE UNIQUE INDEX idx_one_open_per_class_per_day 
    ON attendance_sessions(class_id, session_date) 
    WHERE status = 'open';

-- ============================================
-- TABLE: attendance_records
-- ============================================
CREATE TABLE attendance_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES attendance_sessions(id) ON DELETE CASCADE,
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL,  -- 'present', 'late', 'absent', 'excused'
    check_in_time TIMESTAMPTZ,
    check_method VARCHAR(20),  -- 'button', 'voice', 'code', 'manual'
    interaction_id VARCHAR(100),  -- Discord interaction ID for audit
    ip_address INET,
    notes TEXT,
    exp_earned INTEGER DEFAULT 0,
    verified_by BIGINT,  -- for manual overrides
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT chk_record_status CHECK (status IN (
        'present', 'late', 'absent', 'excused'
    )),
    CONSTRAINT chk_check_method CHECK (check_method IN (
        'button', 'voice', 'code', 'manual'
    )),
    CONSTRAINT UNIQUE_session_student UNIQUE (session_id, student_id)
);

-- Indexes
CREATE INDEX idx_records_session ON attendance_records(session_id);
CREATE INDEX idx_records_student ON attendance_records(student_id);
CREATE INDEX idx_records_status ON attendance_records(status);
CREATE INDEX idx_records_check_time ON attendance_records(check_in_time);

-- ============================================
-- TABLE: attendance_summary (Materialized View)
-- ============================================
CREATE TABLE attendance_summary (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    class_id UUID REFERENCES classes(id) ON DELETE CASCADE,
    semester VARCHAR(20) NOT NULL,
    total_sessions INTEGER DEFAULT 0,
    present_count INTEGER DEFAULT 0,
    late_count INTEGER DEFAULT 0,
    absent_count INTEGER DEFAULT 0,
    excused_count INTEGER DEFAULT 0,
    attendance_rate DECIMAL(5,2) DEFAULT 0.00,
    is_below_minimum BOOLEAN DEFAULT FALSE,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT UNIQUE_summary UNIQUE (student_id, course_id, semester),
    CONSTRAINT chk_rate CHECK (attendance_rate >= 0 AND attendance_rate <= 100)
);

-- Indexes
CREATE INDEX idx_summary_student ON attendance_summary(student_id);
CREATE INDEX idx_summary_course ON attendance_summary(course_id);
CREATE INDEX idx_summary_semester ON attendance_summary(semester);
CREATE INDEX idx_summary_below_minimum ON attendance_summary(is_below_minimum) 
    WHERE is_below_minimum = TRUE;

-- ============================================
-- FUNCTION: Update attendance summary
-- ============================================
CREATE OR REPLACE FUNCTION update_attendance_summary()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO attendance_summary (
        student_id, course_id, class_id, semester,
        total_sessions, present_count, late_count,
        absent_count, excused_count, attendance_rate,
        is_below_minimum, last_updated
    )
    SELECT
        NEW.student_id,
        ases.course_id,
        ases.class_id,
        -- Get semester from course_schedules
        (SELECT semester FROM course_schedules 
         WHERE course_id = ases.course_id LIMIT 1),
        COUNT(*) as total_sessions,
        COUNT(*) FILTER (WHERE ar.status = 'present') as present_count,
        COUNT(*) FILTER (WHERE ar.status = 'late') as late_count,
        COUNT(*) FILTER (WHERE ar.status = 'absent') as absent_count,
        COUNT(*) FILTER (WHERE ar.status = 'excused') as excused_count,
        ROUND(
            (COUNT(*) FILTER (WHERE ar.status IN ('present', 'late'))::DECIMAL / 
             NULLIF(COUNT(*), 0)) * 100, 2
        ) as attendance_rate,
        (COUNT(*) FILTER (WHERE ar.status IN ('present', 'late')) < 10) as is_below_minimum,
        NOW()
    FROM attendance_records ar
    JOIN attendance_sessions ases ON ar.session_id = ases.id
    WHERE ar.student_id = NEW.student_id
    GROUP BY NEW.student_id, ases.course_id, ases.class_id
    ON CONFLICT (student_id, course_id, semester) 
    DO UPDATE SET
        total_sessions = EXCLUDED.total_sessions,
        present_count = EXCLUDED.present_count,
        late_count = EXCLUDED.late_count,
        absent_count = EXCLUDED.absent_count,
        excused_count = EXCLUDED.excused_count,
        attendance_rate = EXCLUDED.attendance_rate,
        is_below_minimum = EXCLUDED.is_below_minimum,
        last_updated = NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger
CREATE TRIGGER trg_update_attendance_summary
    AFTER INSERT OR UPDATE ON attendance_records
    FOR EACH ROW
    EXECUTE FUNCTION update_attendance_summary();
```

---

## 3. REKAP ABSENSI & ALERT SYSTEM

### 3.1 Auto-Generate Reports

#### Per Pertemuan (Per Session)

```python
async def generate_session_report(session_id: str) -> Embed:
    """Generate report for single attendance session"""
    
    # Get session details
    session = await db.fetchrow(
        """
        SELECT ases.*, c.name as class_name, co.name as course_name
        FROM attendance_sessions ases
        JOIN classes c ON ases.class_id = c.id
        JOIN courses co ON ases.course_id = co.id
        WHERE ases.id = $1
        """,
        session_id
    )
    
    # Get attendance stats
    stats = await db.fetchrow(
        """
        SELECT
            COUNT(*) as total_enrolled,
            COUNT(ar.id) as total_checked_in,
            COUNT(ar.id) FILTER (WHERE ar.status = 'present') as present,
            COUNT(ar.id) FILTER (WHERE ar.status = 'late') as late,
            COUNT(ar.id) FILTER (WHERE ar.status = 'absent') as absent,
            COUNT(ar.id) FILTER (WHERE ar.status = 'excused') as excused
        FROM enrollments e
        LEFT JOIN attendance_records ar ON 
            e.student_id = ar.student_id AND ar.session_id = $1
        WHERE e.class_id = $2 AND e.course_id = $3
        """,
        session_id, session['class_id'], session['course_id']
    )
    
    # Get list of absent students
    absent_students = await db.fetch(
        """
        SELECT s.nama_lengkap, s.nim
        FROM enrollments e
        JOIN students s ON e.student_id = s.id
        LEFT JOIN attendance_records ar ON 
            e.student_id = ar.student_id AND ar.session_id = $1
        WHERE e.class_id = $2 
        AND ar.id IS NULL
        """,
        session_id, session['class_id']
    )
    
    # Build embed
    embed = Embed(
        title=f"📊 Rekap Absensi — {session['course_name']}",
        description=f"Kelas: {session['class_name']} | {session['session_date']}",
        color=Color.blue()
    )
    
    embed.add_field(
        name="📈 Statistik",
        value=(
            f"Total Terdaftar: {stats['total_enrolled']}\n"
            f"✅ Hadir: {stats['present']}\n"
            f"🟡 Terlambat: {stats['late']}\n"
            f"🔴 Tidak Hadir: {stats['absent']}\n"
            f"⚪ Dispensasi: {stats['excused']}"
        ),
        inline=True
    )
    
    attendance_rate = (
        (stats['present'] + stats['late']) / 
        max(stats['total_enrolled'], 1) * 100
    )
    
    embed.add_field(
        name="🎯 Tingkat Kehadiran",
        value=f"{attendance_rate:.1f}%",
        inline=True
    )
    
    if absent_students:
        absent_list = "\n".join([
            f"• {s['nama_lengkap']} ({s['nim']})"
            for s in absent_students[:10]  # Show max 10
        ])
        embed.add_field(
            name="❌ Belum Absen",
            value=absent_list,
            inline=False
        )
    
    return embed
```

#### Per Minggu (Weekly Summary)

```python
async def generate_weekly_report(
    class_id: str, 
    week_start: date
) -> Embed:
    """Generate weekly attendance summary"""
    
    week_end = week_start + timedelta(days=6)
    
    # Get all sessions this week
    sessions = await db.fetch(
        """
        SELECT ases.*, co.name as course_name
        FROM attendance_sessions ases
        JOIN courses co ON ases.course_id = co.id
        WHERE ases.class_id = $1
        AND ases.session_date BETWEEN $2 AND $3
        AND ases.status = 'graded'
        ORDER BY ases.session_date
        """,
        class_id, week_start, week_end
    )
    
    # Get student attendance for the week
    student_stats = await db.fetch(
        """
        SELECT
            s.id,
            s.nama_lengkap,
            s.nim,
            COUNT(ar.id) as sessions_attended,
            COUNT(*) OVER() as total_sessions,
            SUM(ar.exp_earned) as total_exp
        FROM students s
        JOIN enrollments e ON s.id = e.student_id
        LEFT JOIN attendance_records ar ON 
            s.id = ar.student_id
            AND ar.session_id IN (
                SELECT id FROM attendance_sessions 
                WHERE class_id = $1 
                AND session_date BETWEEN $2 AND $3
            )
        WHERE e.class_id = $1
        GROUP BY s.id, s.nama_lengkap, s.nim
        ORDER BY sessions_attended DESC
        """,
        class_id, week_start, week_end
    )
    
    embed = Embed(
        title=f"📅 Laporan Mingguan — {week_start.strftime('%d %b %Y')}",
        description=f"Sampai dengan {week_end.strftime('%d %b %Y')}",
        color=Color.blue()
    )
    
    # Session count
    embed.add_field(
        name="📚 Total Sesi",
        value=str(len(sessions)),
        inline=True
    )
    
    # Average attendance
    avg_attendance = sum(
        s['sessions_attended'] for s in student_stats
    ) / max(len(student_stats), 1)
    
    embed.add_field(
        name="📊 Rata-rata Kehadiran",
        value=f"{avg_attendance:.1f} sesi",
        inline=True
    )
    
    # Students below minimum
    below_minimum = [
        s for s in student_stats 
        if s['sessions_attended'] < 10
    ]
    
    if below_minimum:
        warning_list = "\n".join([
            f"⚠️ {s['nama_lengkap']} ({s['nim']}): "
            f"{s['sessions_attended']}/{student_stats[0]['total_sessions']} sesi"
            for s in below_minimum[:5]
        ])
        embed.add_field(
            name="⚠️ Di Bawah Minimum (< 10x)",
            value=warning_list,
            inline=False
        )
    
    return embed
```

#### Per Mahasiswa (Student Progress)

```python
async def generate_student_report(
    student_id: str, 
    course_id: str
) -> Embed:
    """Generate individual student attendance report"""
    
    student = await db.fetchrow(
        "SELECT * FROM students WHERE id = $1", student_id
    )
    
    course = await db.fetchrow(
        "SELECT * FROM courses WHERE id = $1", course_id
    )
    
    # Get detailed attendance
    attendance = await db.fetch(
        """
        SELECT 
            ases.session_date,
            ar.status,
            ar.check_in_time,
            ar.check_method,
            ar.exp_earned,
            co.name as course_name
        FROM attendance_records ar
        JOIN attendance_sessions ases ON ar.session_id = ases.id
        JOIN courses co ON ases.course_id = co.id
        WHERE ar.student_id = $1 AND ases.course_id = $2
        ORDER BY ases.session_date
        """,
        student_id, course_id
    )
    
    # Calculate stats
    total = len(attendance)
    present = sum(1 for a in attendance if a['status'] == 'present')
    late = sum(1 for a in attendance if a['status'] == 'late')
    absent = total - present - late
    total_exp = sum(a['exp_earned'] for a in attendance)
    
    embed = Embed(
        title=f"📋 Laporan Kehadiran — {student['nama_lengkap']}",
        description=f"NIM: {student['nim']} | {course['name']}",
        color=Color.green() if total >= 10 else Color.red()
    )
    
    embed.add_field(
        name="📊 Ringkasan",
        value=(
            f"Total Sesi: {total}\n"
            f"✅ Hadir: {present}\n"
            f"🟡 Terlambat: {late}\n"
            f"🔴 Tidak Hadir: {absent}\n"
            f"🎯 Rate: {(present + late) / max(total, 1) * 100:.1f}%"
        ),
        inline=True
    )
    
    embed.add_field(
        name="🎮 Gamifikasi",
        value=f"Total EXP: {total_exp}",
        inline=True
    )
    
    # Status indicator
    if total >= 10:
        embed.add_field(
            name="✅ Status",
            value="Memenuhi minimal kehadiran",
            inline=False
        )
    else:
        remaining = 10 - total
        embed.add_field(
            name="⚠️ Status",
            value=f"Kurang {remaining} sesi lagi untuk memenuhi minimal",
            inline=False
        )
    
    return embed
```

---

### 3.2 Alert System

#### Alert Rules Configuration

```python
ALERT_RULES = {
    "consecutive_present": {
        "threshold": 7,
        "badge": "🏅 Week Warrior",
        "notify_student": True,
        "notify_dosen": False,
        "message": "🎉 Kamu hadir 7x berturut-turut! Badge Week Warrior unlocked!"
    },
    "attendance_below_50": {
        "threshold": 50,  # percentage
        "notify_student": True,
        "notify_dosen_wali": True,
        "message_student": "⚠️ Kehadiranmu di bawah 50%. Segera perbaiki!",
        "message_dosen": "⚠️ Mahasiswa {nama} ({nim}) kehadirannya di bawah 50%."
    },
    "attendance_below_30": {
        "threshold": 30,  # percentage
        "escalate_to_kaprodi": True,
        "message_kaprodi": "🚨 ESCALATION: Mahasiswa {nama} ({nim}) kehadiran < 30%."
    },
    "minimum_reached": {
        "threshold": 10,  # sessions
        "notify_student": True,
        "message": "✅ Minimal kehadiran (10x) terpenuhi! Pertahankan!"
    },
    "consecutive_absent": {
        "threshold": 3,
        "notify_student": True,
        "notify_dosen": True,
        "message_student": "⚠️ Kamu tidak hadir 3x berturut-turut.",
        "message_dosen": "⚠️ Mahasiswa {nama} ({nim}) tidak hadir 3x berturut-turut."
    }
}
```

#### Alert Trigger Implementation

```python
class AlertSystem:
    def __init__(self, db):
        self.db = db
    
    async def check_alerts(self, student_id: str, course_id: str):
        """Check all alert conditions after attendance update"""
        
        # Get student info
        student = await self.db.fetchrow(
            "SELECT * FROM students WHERE id = $1", student_id
        )
        
        # Get attendance summary
        summary = await self.db.fetchrow(
            """
            SELECT * FROM attendance_summary 
            WHERE student_id = $1 AND course_id = $2
            """,
            student_id, course_id
        )
        
        alerts = []
        
        # Check consecutive present
        consecutive_present = await self._get_consecutive_count(
            student_id, course_id, 'present'
        )
        if consecutive_present >= ALERT_RULES['consecutive_present']['threshold']:
            alerts.append({
                'type': 'consecutive_present',
                'badge': ALERT_RULES['consecutive_present']['badge'],
                'message': ALERT_RULES['consecutive_present']['message']
            })
        
        # Check attendance rate
        if summary and summary['attendance_rate'] < 50:
            alerts.append({
                'type': 'below_50',
                'message_student': ALERT_RULES['attendance_below_50']['message_student'],
                'message_dosen': ALERT_RULES['attendance_below_50']['message_dosen'].format(
                    nama=student['nama_lengkap'],
                    nim=student['nim']
                )
            })
        
        if summary and summary['attendance_rate'] < 30:
            alerts.append({
                'type': 'below_30',
                'escalate': True,
                'message': ALERT_RULES['attendance_below_30']['message_kaprodi'].format(
                    nama=student['nama_lengkap'],
                    nim=student['nim']
                )
            })
        
        # Check minimum reached
        if summary and summary['total_sessions'] >= 10 and not summary.get('minimum_notified'):
            alerts.append({
                'type': 'minimum_reached',
                'message': ALERT_RULES['minimum_reached']['message']
            })
            await self._mark_minimum_reached(student_id, course_id)
        
        # Check consecutive absent
        consecutive_absent = await self._get_consecutive_count(
            student_id, course_id, 'absent'
        )
        if consecutive_absent >= ALERT_RULES['consecutive_absent']['threshold']:
            alerts.append({
                'type': 'consecutive_absent',
                'message_student': ALERT_RULES['consecutive_absent']['message_student'],
                'message_dosen': ALERT_RULES['consecutive_absent']['message_dosen'].format(
                    nama=student['nama_lengkap'],
                    nim=student['nim']
                )
            })
        
        # Send all alerts
        for alert in alerts:
            await self._send_alert(alert, student, course_id)
    
    async def _get_consecutive_count(
        self, 
        student_id: str, 
        course_id: str, 
        status: str
    ) -> int:
        """Get consecutive count of a status"""
        records = await self.db.fetch(
            """
            SELECT ar.status
            FROM attendance_records ar
            JOIN attendance_sessions ases ON ar.session_id = ases.id
            WHERE ar.student_id = $1 AND ases.course_id = $2
            ORDER BY ases.session_date DESC
            LIMIT 20
            """,
            student_id, course_id
        )
        
        count = 0
        for record in records:
            if record['status'] == status:
                count += 1
            else:
                break
        
        return count
    
    async def _send_alert(
        self, 
        alert: dict, 
        student: dict, 
        course_id: str
    ):
        """Send alert to appropriate recipients"""
        
        # Get Discord member
        member = await self.bot.fetch_user(student['discord_id'])
        
        if alert['type'] == 'consecutive_present':
            # Send DM to student
            await member.send(alert['message'])
            
            # Award badge
            await self._award_badge(student['id'], alert['badge'])
        
        elif alert['type'] in ['below_50', 'below_30']:
            # Send warning to student
            await member.send(alert['message_student'])
            
            # Notify dosen wali
            dosen_wali = await self._get_dosen_wali(student)
            if dosen_wali:
                await dosen_wali.send(alert['message_dosen'])
            
            # Escalate to kaprodi if needed
            if alert.get('escalate'):
                kaprodi = await self._get_kaprodi(student)
                if kaprodi:
                    await kaprodi.send(alert['message'])
        
        elif alert['type'] == 'minimum_reached':
            await member.send(alert['message'])
        
        elif alert['type'] == 'consecutive_absent':
            await member.send(alert['message_student'])
            
            dosen_wali = await self._get_dosen_wali(student)
            if dosen_wali:
                await dosen_wali.send(alert['message_dosen'])
```

#### Alert Notification Templates

```python
ALERT_TEMPLATES = {
    "weekly_warrior": Embed(
        title="🏅 Badge Unlocked!",
        description="Kamu berhasil hadir 7x berturut-turut!",
        color=Color.gold(),
        fields=[
            EmbedField(name="Badge", value="🏅 Week Warrior", inline=True),
            EmbedField(name="Streak", value="7x berturut-turut", inline=True),
            EmbedField(name="Bonus", value="+50 EXP", inline=True)
        ]
    ),
    
    "minimum_reached": Embed(
        title="✅ Minimal Kehadiran Terpenuhi!",
        description="Kamu sudah memenuhi minimal 10x kehadiran.",
        color=Color.green(),
        fields=[
            EmbedField(name="Status", value="✅ Memenuhi syarat", inline=True),
            EmbedField(name="Total Hadir", value="{total}x", inline=True)
        ]
    ),
    
    "warning_below_50": Embed(
        title="⚠️ Peringatan Kehadiran",
        description="Kehadiranmu di bawah 50%!",
        color=Color.orange(),
        fields=[
            EmbedField(name="Kehadiran", value="{rate}%", inline=True),
            EmbedField(name="Yang Harus Dilakukan", value=(
                "- Hadir di kuliah berikutnya\n"
                "- Jika ada kendala, hubungi dosen"
            ), inline=False)
        ]
    ),
    
    "critical_below_30": Embed(
        title="🚨 Kritis: Kehadiran Sangat Rendah",
        description="Kehadiranmu di bawah 30%! Risiko nilai E.",
        color=Color.red(),
        fields=[
            EmbedField(name="Kehadiran", value="{rate}%", inline=True),
            EmbedField(name="Risiko", value=(
                "- Tidak memenuhi syarat UTS/UAS\n"
                "- Nilai otomatis E"
            ), inline=False)
        ]
    ),
    
    "consecutive_absent_warning": Embed(
        title="⚠️ Tidak Hadir Berturut-turut",
        description="Kamu tidak hadir 3x berturut-turut.",
        color=Color.orange(),
        fields=[
            EmbedField(name="Jumlah", value="3x berturut-turut", inline=True),
            EmbedField(name="Catatan", value=(
                "Pastikan kamu hadir di pertemuan berikutnya.\n"
                "Jika ada masalah, silakan hubungi dosen."
            ), inline=False)
        ]
    )
}
```

---

## 4. FLOW DIAGRAM LENGKAP

### 4.1 Registration Flow (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           REGISTRATION FLOW                                     │
│                         (From Join to Verified)                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────┐
    │  USER JOIN   │
    │   SERVER     │
    └──────┬──────┘
           │
           ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │ on_member_join(event)                                           │
    │                                                                 │
    │ 1. Log to audit_log                                             │
    │ 2. Send DM welcome (embed)                                      │
    │ 3. Notify #admin-logs                                           │
    │ 4. Create pending_verification record                           │
    │ 5. Set verification_deadline = NOW() + 24h                      │
    │ 6. Set kick_deadline = NOW() + 72h                              │
    └─────────────────────────────┬───────────────────────────────────┘
                                  │
           ┌──────────────────────┴──────────────────────┐
           │                                             │
           ▼                                             ▼
    ┌─────────────────┐                         ┌─────────────────┐
    │ Within 24h       │                         │ After 24h        │
    │ User goes to     │                         │ No verification  │
    │ #verifikasi      │                         │                  │
    └────────┬────────┘                         └────────┬────────┘
             │                                           │
             ▼                                           ▼
    ┌─────────────────┐                         ┌─────────────────┐
    │ /verify [NIM]   │                         │ DM Reminder #1  │
    │                  │                         │ (24h warning)   │
    └────────┬────────┘                         └────────┬────────┘
             │                                           │
             ▼                                           │
    ┌─────────────────────────────────┐                  │
    │ Validate NIM Format             │                  │
    │ Pattern: ^[0-9]{10}$           │                  │
    └────────┬────────────────────────┘                  │
             │                                           │
     ┌───────┴───────┐                                   │
     │               │                                   │
     ▼               ▼                                   ▼
┌─────────┐    ┌─────────┐                       ┌─────────────────┐
│ Invalid │    │  Valid   │                       │ After 48h        │
│ Format  │    │  Format  │                       │ No verification  │
└────┬────┘    └────┬────┘                       └────────┬────────┘
     │              │                                     │
     ▼              ▼                                     ▼
┌─────────┐   ┌─────────────────┐               ┌─────────────────┐
│ Error:  │   │ Check Database   │               │ DM Final Warning│
│ "Format │   │ (students table) │               │ + Timeout Info  │
│ NIM     │   └────────┬────────┘               └────────┬────────┘
│ invalid"│            │                                 │
└─────────┘    ┌───────┴───────┐                         │
               │               │                         ▼
               ▼               ▼               ┌─────────────────┐
        ┌─────────┐    ┌─────────┐             │ After 72h        │
        │  NIM    │    │  NIM    │             │ Auto-kick        │
        │  Found  │    │  Not    │             │ from server      │
        │(linked) │    │  Found  │             └─────────────────┘
        └────┬────┘    └────┬────┘
             │              │
             ▼              ▼
    ┌─────────────────┐   ┌─────────────────────────────────┐
    │ Check Link       │   │ Self-Registration Flow           │
    │ Status           │   │                                  │
    └────────┬────────┘   │ 1. Show Registration Modal       │
             │            │ 2. Validate all fields            │
     ┌───────┴───────┐    │ 3. Create pending record          │
     │               │    │ 4. Notify admin                   │
     ▼               ▼    └────────────────┬────────────────┘
┌─────────┐    ┌─────────┐                 │
│ Already │    │ Not     │                 ▼
│ Linked  │    │ Linked  │        ┌─────────────────┐
│ (this   │    │         │        │ Admin Reviews     │
│ Discord)│    │         │        │                   │
└────┬────┘    └────┬────┘        │ ┌───────┐        │
     │              │             │ │Approve│        │
     ▼              ▼             │ └───┬───┘        │
┌─────────┐   ┌──────────┐      │     │             │
│ Show    │   │ Show     │      │ ┌───┴───┐        │
│ "Already│   │Confirm   │      │ │Reject │        │
│ verified│   │Modal     │      │ └───┬───┘        │
│ "       │   └────┬─────┘      │     │             │
└─────────┘        │            └─────┼─────────────┘
           ┌───────┴───────┐          │
           │               │          │
           ▼               ▼          ▼
    ┌─────────┐    ┌─────────┐  ┌─────────┐
    │ Confirm │    │ Wrong   │  │ Create  │
    │ Identity│    │ Person  │  │ Student │
    └────┬────┘    └────┬────┘  │ Record  │
         │              │       └────┬────┘
         ▼              ▼            │
    ┌──────────────────────┐         ▼
    │ LINK DISCORD ID      │  ┌─────────────────┐
    │ + ASSIGN ROLES       │  │ Assign Roles     │
    │                      │  │ - Verified       │
    │ Roles:               │  │ - Angkatan       │
    │ - Mahasiswa Verified │  │ - Prodi          │
    │ - Angkatan XX        │  │ - Kelas          │
    │ - Prodi Name         │  └────────┬────────┘
    │ - Kelas X            │           │
    └──────────────────────┘           ▼
                               ┌─────────────────┐
                               │ DM Confirmation  │
                               │ "Welcome! You're │
                               │  now verified."  │
                               └─────────────────┘
```

---

### 4.2 Attendance Flow — Offline (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    ATTENDANCE FLOW — TATAP MUKA (OFFLINE)                       │
└─────────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────┐
    │ DOSEN: /mulai-kuliah [kelas] [mata_kuliah]                     │
    └─────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │ VALIDATION                                                      │
    │                                                                 │
    │ 1. Is dosen authorized for this course?                         │
    │    → Query course_schedules WHERE course_id = X AND lecturer_id = Y│
    │    → NO: "❌ Anda tidak mengampu mata kuliah ini."              │
    │                                                                 │
    │ 2. Is there a scheduled class today?                            │
    │    → Query WHERE day_of_week = TODAY                            │
    │    → NO: "⚠️ Tidak ada jadwal kuliah untuk kelas ini hari ini."│
    │                                                                 │
    │ 3. Is there already an open session?                            │
    │    → Query WHERE status = 'open' AND class_id = X              │
    │    → YES: "⚠️ Sesi absensi sudah aktif." (show details)        │
    │                                                                 │
    └─────────────────────────────┬───────────────────────────────────┘
                                  │
                          ┌───────┴───────┐
                          │ All checks    │
                          │ passed        │
                          └───────┬───────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │ CREATE SESSION                                                   │
    │                                                                 │
    │ INSERT INTO attendance_sessions:                                │
    │   class_id: $class_id                                          │
    │   course_id: $course_id                                         │
    │   session_date: CURRENT_DATE                                   │
    │   session_type: 'offline'                                       │
    │   opens_at: NOW()                                               │
    │   closes_at: NOW() + INTERVAL '15 minutes'                     │
    │   status: 'open'                                                │
    │   started_by: dosen.discord_id                                  │
    │                                                                 │
    └─────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │ SEND ATTENDANCE EMBED                                           │
    │                                                                 │
    │ Channel: #absensi-[kelas]                                       │
    │                                                                 │
    │ ┌─────────────────────────────────────────────────────────────┐ │
    │ │ 🎓 Kuliah Dimulai!                                          │ │
    │ │                                                             │ │
    │ │ IF201 — Pemrograman Web                                    │ │
    │ │ Kelas: B1 | Dosen: Pak Ahmad                                │ │
    │ │ Waktu: 09:00 WIB | Sisa: 15:00                             │ │
    │ │                                                             │ │
    │ │ [🟢 Hadir]  Button (custom_id: attend_{session_id})         │ │
    │ └─────────────────────────────────────────────────────────────┘ │
    │                                                                 │
    └─────────────────────────────┬───────────────────────────────────┘
                                  │
                                  │  (15 minutes window)
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ MAHASISWA KLIK  │     │ TIME WINDOW     │     │ WINDOW CLOSES   │
│ "HADIR"          │     │ STILL OPEN      │     │                 │
└────────┬────────┘     └─────────────────┘     └────────┬────────┘
         │                                                │
         ▼                                                ▼
┌─────────────────────────────────┐           ┌─────────────────────┐
│ CHECK ATTENDANCE                │           │ AUTO-CLOSE SESSION   │
│                                 │           │                      │
│ Guards:                         │           │ 1. Update status     │
│ ├─ Session open?               │           │    → 'closed'        │
│ │  → If NO: error              │           │ 2. Generate report   │
│ ├─ Within time window?         │           │ 3. Send to channel   │
│ │  → If NO: "Waktu habis"     │           │ 4. Notify absentees  │
│ ├─ Already checked in?         │           └─────────────────────┘
│ │  → If YES: "Sudah absen"    │
│ ├─ Enrolled in class?          │
│ │  → If NO: "Tidak terdaftar" │
│ │                              │
│ └─ ALL PASSED                  │
│    → Continue                  │
└────────┬───────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ DETERMINE STATUS                 │
│                                  │
│ check_time = NOW()              │
│ class_start = scheduled_time    │
│                                  │
│ IF check_time <= class_start:    │
│   status = 'present'             │
│   EXP = 10                       │
│                                  │
│ ELIF check_time <= class_start   │
│   + 15 minutes:                  │
│   status = 'late'                │
│   EXP = 5                        │
│                                  │
└────────┬───────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ CREATE ATTENDANCE RECORD         │
│                                  │
│ INSERT INTO attendance_records:  │
│   session_id: X                  │
│   student_id: Y                  │
│   status: 'present'/'late'      │
│   check_in_time: NOW()           │
│   check_method: 'button'         │
│   exp_earned: 10/5               │
│                                  │
└────────┬───────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ TRIGGER GAMIFICATION             │
│                                  │
│ 1. Add EXP to student            │
│ 2. Check level up                │
│ 3. Check badge eligibility       │
│    → Week Warrior (7x consecutive)│
│    → Minimum Met (10x total)     │
│ 4. Update attendance_summary     │
│ 5. Check alerts                  │
│    → Below 50%: warning          │
│    → Below 30%: escalation       │
│    → 3x absent: notification     │
│                                  │
└────────┬───────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ RESPOND TO USER                  │
│                                  │
│ Ephemeral response (only user):  │
│                                  │
│ IF present:                      │
│   "✅ Absensi berhasil! +10 EXP" │
│                                  │
│ IF late:                         │
│   "⚠️ Absensi terlambat. +5 EXP"│
│                                  │
└─────────────────────────────────┘
```

---

### 4.3 Attendance Flow — Online/Hybrid (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    ATTENDANCE FLOW — ONLINE / HYBRID                            │
└─────────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────┐
    │ DOSEN: /mulai-kuliah [kelas] [mata_kuliah] --type hybrid      │
    └─────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │ CREATE SESSION                                                   │
    │   session_type: 'hybrid'                                        │
    │   voice_channel_id: $voice_channel_id                          │
    │                                                                 │
    └─────────────────────────────┬───────────────────────────────────┘
                                  │
         ┌────────────────────────┴────────────────────────┐
         │                                                 │
         ▼                                                 ▼
┌─────────────────────────┐                   ┌─────────────────────────┐
│ VOICE CHANNEL MONITORING │                   │ MANUAL ATTENDANCE       │
│ (Primary Method)         │                   │ (Backup Method)         │
└────────────┬────────────┘                   └────────────┬────────────┘
             │                                             │
             ▼                                             ▼
┌─────────────────────────┐                   ┌─────────────────────────┐
│ on_voice_state_update    │                   │ /absen [kode]           │
│ event triggered          │                   │ or click button         │
└────────────┬────────────┘                   └────────────┬────────────┘
             │                                             │
             ▼                                             │
┌─────────────────────────┐                                 │
│ CHECK CONDITIONS         │                                 │
│                          │                                 │
│ 1. Is member in target  │                                 │
│    voice channel?       │                                 │
│    → NO: ignore         │                                 │
│    → YES: continue      │                                 │
│                          │                                 │
│ 2. Is session active?   │                                 │
│    → NO: ignore         │                                 │
│    → YES: continue      │                                 │
│                          │                                 │
│ 3. Start timer (30 min) │                                 │
│                          │                                 │
└────────────┬────────────┘                                 │
             │                                             │
             ▼                                             │
┌─────────────────────────┐                                 │
│ TIMER: 30 MINUTES        │                                 │
│                          │                                 │
│ background_task:         │                                 │
│   await sleep(1800)     │                                 │
│   check_if_still_in_vc  │                                 │
│                          │                                 │
└────────────┬────────────┘                                 │
             │                                             │
     ┌───────┴───────┐                                     │
     │               │                                     │
     ▼               ▼                                     ▼
┌─────────┐    ┌─────────┐                     ┌─────────────────────┐
│ LEFT VC │    │ STILL   │                     │ VALIDATE CODE       │
│ BEFORE  │    │ IN VC   │                     │                     │
│ 30 MIN  │    │         │                     │ 1. Format valid?    │
└────┬────┘    └────┬────┘                     │ 2. Code exists?     │
     │              │                          │ 3. Not expired?     │
     │              │                          │ 4. Not duplicate?   │
     │              │                          │ 5. Enrolled?        │
     │              │                          └──────────┬──────────┘
     │              │                                     │
     ▼              ▼                              ┌──────┴──────┐
┌─────────┐  ┌─────────────────┐                   │             │
│ DO NOT  │  │ MARK ATTENDANCE │                   ▼             ▼
│ COUNT   │  │                 │              ┌─────────┐  ┌─────────┐
│         │  │ 1. Create record│              │ Invalid │  │ Valid   │
│ Send    │  │ 2. Add EXP      │              │ Code    │  │ Code    │
│ warning │  │ 3. Update summary│             └────┬────┘  └────┬────┘
│ to      │  │ 4. Notify student│                  │            │
│ student │  │                  │                  ▼            ▼
└─────────┘  └─────────────────┘           ┌─────────┐  ┌─────────────┐
                                            │ Error   │  │ Same as     │
                                            │ message │  │ Voice flow: │
                                            └─────────┘  │ Create      │
                                                         │ record, EXP,│
                                                         │ summary,    │
                                                         │ notify      │
                                                         └─────────────┘
```

---

### 4.4 State Transitions (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         ATTENDANCE STATE MACHINE                                │
└─────────────────────────────────────────────────────────────────────────────────┘

                                    ┌───────────────┐
                                    │  NOT_STARTED  │
                                    │               │
                                    │  Initial state│
                                    │  No session   │
                                    │  created yet  │
                                    └───────┬───────┘
                                            │
                                            │ /mulai-kuliah
                                            │ Guard: no active session
                                            │ Action: create_session
                                            │
                                            ▼
                                    ┌───────────────┐
                                    │     OPEN      │
                                    │               │
                                    │  Session is   │
                                    │  accepting    │
                                    │  attendance   │
                                    │               │
                                    │  Can:         │
                                    │  - check_in   │
                                    │  - close      │
                                    └───┬───────┬───┘
                                        │       │
                    ┌───────────────────┘       └───────────────────┐
                    │                                               │
                    │ /tutup-kuliah                                 │ auto-close timer
                    │ OR                                            │ (15 min after start)
                    │ timeout                                       │
                    │                                               │
                    ▼                                               ▼
            ┌───────────────┐                              ┌───────────────┐
            │    CLOSED     │                              │    CLOSED     │
            │               │                              │               │
            │  Session      │                              │  Session      │
            │  ended,       │                              │  auto-closed  │
            │  waiting for  │                              │  by timer     │
            │  grading      │                              │               │
            └───────┬───────┘                              └───────┬───────┘
                    │                                               │
                    │ /hitung-nilai                                 │
                    │ OR                                            │
                    │ scheduled_job                                  │
                    │                                               │
                    ▼                                               ▼
            ┌───────────────┐                              ┌───────────────┐
            │    GRADED     │                              │    GRADED     │
            │               │                              │               │
            │  Attendance   │                              │  Attendance   │
            │  scores       │                              │  scores       │
            │  calculated   │                              │  calculated   │
            │  and stored   │                              │  and stored   │
            └───────────────┘                              └───────────────┘
                    │                                               │
                    └───────────────────┬───────────────────────────┘
                                        │
                                        │ (terminal state)
                                        │
                                        ▼
                                    ┌───────────────┐
                                    │               │
                                    │   COMPLETED   │
                                    │               │
                                    │  No further   │
                                    │  transitions  │
                                    └───────────────┘


┌─────────────────────────────────────────────────────────────────────────────────┐
│                         STUDENT ATTENDANCE STATES                               │
└─────────────────────────────────────────────────────────────────────────────────┘

        ┌───────────────┐
        │  NOT_CHECKED  │
        │               │
        │  Student has  │
        │  not checked  │
        │  in yet       │
        └───────┬───────┘
                │
                │ check_in (button/voice/code)
                │ Guard: session.open, not duplicate
                │
                ▼
        ┌───────────────┐
        │   CHECKED     │
        │               │
        │  Attendance   │
        │  recorded     │
        │               │
        │  Status:      │
        │  - present    │
        │  - late       │
        │  - excused    │
        └───────────────┘

        ┌───────────────┐
        │   EXCUSED     │  (manual override by dosen/admin)
        │               │
        │  Student is   │
        │  excused for  │
        │  this session │
        └───────────────┘
```

---

### 4.5 Error Recovery Flows (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         ERROR RECOVERY FLOWS                                    │
└─────────────────────────────────────────────────────────────────────────────────┘


╔═════════════════════════════════════════════════════════════════════════════════╗
║ ERROR 1: DISCORD DOWN DURING ATTENDANCE                                         ║
╠═════════════════════════════════════════════════════════════════════════════════╣
║                                                                                 ║
║  ┌─────────────────┐                                                             ║
║  │ Discord API      │                                                             ║
║  │ becomes          │                                                             ║
║  │ unavailable      │                                                             ║
║  └────────┬────────┘                                                             ║
║           │                                                                      ║
║           ▼                                                                      ║
║  ┌─────────────────────────────────────────────────────────────┐                  ║
║  │ Bot detects outage via:                                     │                  ║
║  │ - Failed API calls (httpx.ClientError)                      │                  ║
║  │ - Gateway disconnect events                                 │                  ║
║  │ - Health check failures                                     │                  ║
║  └────────┬────────────────────────────────────────────────────┘                  ║
║           │                                                                      ║
║           ▼                                                                      ║
║  ┌─────────────────────────────────────────────────────────────┐                  ║
║  │ Start recovery timer                                        │                  ║
║  │                                                             │                  ║
║  │ IF outage < 5 minutes:                                      │                  ║
║  │   → Wait, extend window by outage duration                  │                  ║
║  │   → Notify when back                                        │                  ║
║  │                                                             │                  ║
║  │ IF outage 5-30 minutes:                                     │                  ║
║  │   → Log outage event                                        │                  ║
║  │   → Extend window by 2x outage duration                    │                  ║
║  │   → Notify all affected users                               │                  ║
║  │   → Enable manual override                                  │                  ║
║  │                                                             │                  ║
║  │ IF outage > 30 minutes:                                     │                  ║
║  │   → Cancel current session                                  │                  ║
║  │   → Create new session for next hour                        │                  ║
║  │   → Notify admin for manual intervention                    │                  ║
║  └────────┬────────────────────────────────────────────────────┘                  ║
║           │                                                                      ║
║           ▼                                                                      ║
║  ┌─────────────────────────────────────────────────────────────┐                  ║
║  │ Discord comes back online                                   │                  ║
║  │                                                             │                  ║
║  │ 1. Reconnect gateway                                        │                  ║
║  │ 2. Update session extends_at                                │                  ║
║  │ 3. Send notification embed:                                 │                  ║
║  │    "⚠️ Discord sempat down. Waktu absensi diperpanjang."   │                  ║
║  │ 4. Enable button/voice monitoring again                     │                  ║
║  └─────────────────────────────────────────────────────────────┘                  ║
║                                                                                 ║
╚═════════════════════════════════════════════════════════════════════════════════╝


╔═════════════════════════════════════════════════════════════════════════════════╗
║ ERROR 2: STUDENT CLAIMS ATTENDANCE BUT NO RECORD                                ║
╠═════════════════════════════════════════════════════════════════════════════════╣
║                                                                                 ║
║  ┌─────────────────┐                                                             ║
║  │ Student DM:      │                                                             ║
║  │ "Sudah absen     │                                                             ║
║  │  tapi kok tidak  │                                                             ║
║  │  ada?"           │                                                             ║
║  └────────┬────────┘                                                             ║
║           │                                                                      ║
║           ▼                                                                      ║
║  ┌─────────────────────────────────────────────────────────────┐                  ║
║  │ INVESTIGATION (automated)                                   │                  ║
║  │                                                             │                  ║
║  │ 1. Query attendance_records                                 │                  ║
║  │    SELECT * FROM attendance_records                         │                  ║
║  │    WHERE session_id = X AND student_id = Y                  │                  ║
║  │                                                             │                  ║
║  │ 2. Check audit_log for interaction                          │                  ║
║  │    SELECT * FROM audit_log                                  │                  ║
║  │    WHERE event_type = 'attendance_check'                    │                  ║
║  │    AND discord_id = Y                                       │                  ║
║  │    AND metadata->>'session_id' = 'X'                        │                  ║
║  │                                                             │                  ║
║  │ 3. Check interaction_id validity                            │                  ║
║  │    SELECT * FROM interactions                               │                  ║
║  │    WHERE id = interaction_id                                │                  ║
║  │                                                             │                  ║
║  └────────┬────────────────────────────────────────────────────┘                  ║
║           │                                                                      ║
║     ┌─────┴─────┐                                                                ║
║     │           │                                                                ║
║     ▼           ▼                                                                ║
║ ┌────────┐ ┌────────┐                                                             ║
║ │ RECORD │ │ NO     │                                                             ║
║ │ EXISTS │ │ RECORD │                                                             ║
║ └───┬────┘ └───┬────┘                                                             ║
║     │          │                                                                  ║
║     ▼          ▼                                                                  ║
║ ┌────────┐ ┌─────────────────────────────────────────────┐                        ║
║ │ Show   │ │ Check logs for evidence                      │                        ║
║ │ proof  │ │                                               │                        ║
║ │ to     │ │ IF interaction logged with success:           │                        ║
║ │ student│ │   → Database sync issue                       │                        ║
║ │        │ │   → Admin can manually insert                 │                        ║
║ │ "Here  │ │   → With note: "Manual override - verified"  │                        ║
║ │ is     │ │                                               │                        ║
║ │ your   │ │ IF no evidence found:                         │                        ║
║ │ record"│ │   → Explain to student                        │                        ║
║ │        │ │   → Offer manual override if dosen approves   │                        ║
║ └────────┘ │   → Log for future reference                  │                        ║
║            └─────────────────────────────────────────────┘                        ║
║                                                                                 ║
╚═════════════════════════════════════════════════════════════════════════════════╝


╔═════════════════════════════════════════════════════════════════════════════════╗
║ ERROR 3: DOSEN FORGETS TO OPEN SESSION                                           ║
╠═════════════════════════════════════════════════════════════════════════════════╣
║                                                                                 ║
║  ┌─────────────────┐                                                             ║
║  │ Scheduled task   │                                                             ║
║  │ runs every       │                                                             ║
║  │ 5 minutes        │                                                             ║
║  └────────┬────────┘                                                             ║
║           │                                                                      ║
║           ▼                                                                      ║
║  ┌─────────────────────────────────────────────────────────────┐                  ║
║  │ Check: Is there a class scheduled NOW that doesn't have     │                  ║
║  │         an active session?                                   │                  ║
║  │                                                             │                  ║
║  │ SELECT cs.* FROM course_schedules cs                        │                  ║
║  │ LEFT JOIN attendance_sessions ases ON                       │                  ║
║  │   cs.course_id = ases.course_id                             │                  ║
║  │   AND ases.session_date = CURRENT_DATE                      │                  ║
║  │   AND ases.status IN ('open', 'closed')                     │                  ║
║  │ WHERE cs.day_of_week = EXTRACT(DOW FROM NOW())              │                  ║
║  │ AND cs.start_time <= NOW()::TIME                            │                  ║
║  │ AND cs.start_time + INTERVAL '15 minutes' >= NOW()::TIME    │                  ║
║  │ AND ases.id IS NULL                                         │                  ║
║  └────────┬────────────────────────────────────────────────────┘                  ║
║           │                                                                      ║
║     ┌─────┴─────┐                                                                ║
║     │           │                                                                ║
║     ▼           ▼                                                                ║
║ ┌────────┐ ┌────────┐                                                             ║
║ │ NO     │ │ YES    │                                                             ║
║ │ MATCH  │ │ MISSING│                                                             ║
║ └────────┘ │ SESSION│                                                             ║
║            └───┬────┘                                                             ║
║                │                                                                  ║
║                ▼                                                                  ║
║  ┌─────────────────────────────────────────────────────────────┐                  ║
║  │ NOTIFICATION PHASE (15 minutes after scheduled start)       │                  ║
║  │                                                             │                  ║
║  │ 1. DM to dosen:                                             │                  ║
║  │    "⚠️ Kuliah [mata_kuliah] kelas [X] sudah dimulai 15     │                  ║
║  │     menit yang lalu. Gunakan /mulai-kuliah untuk membuka    │                  ║
║  │     sesi absensi."                                           │                  ║
║  │                                                             │                  ║
║  │ 2. Notify #admin-logs:                                      │                  ║
║  │    "⚠️ No session opened for [course] [class] by [dosen]"   │                  ║
║  └────────┬────────────────────────────────────────────────────┘                  ║
║           │                                                                      ║
║           ▼                                                                      ║
║  ┌─────────────────────────────────────────────────────────────┐                  ║
║  │ AUTO-RECOVERY (30 minutes after scheduled start)            │                  ║
║  │                                                             │                  ║
║  │ IF still no session:                                         │                  ║
║  │   1. Create session automatically:                           │                  ║
║  │      - opens_at: scheduled_start_time                       │                  ║
║  │      - closes_at: NOW() + 15 minutes                        │                  ║
║  │      - notes: "Auto-created due to missing session"          │                  ║
║  │   2. Notify admin for manual adjustment                      │                  ║
║  │   3. Send attendance embed to class channel                  │                  ║
║  │   4. Log event for audit                                     │                  ║
║  └─────────────────────────────────────────────────────────────┘                  ║
║                                                                                 ║
╚═════════════════════════════════════════════════════════════════════════════════╝


╔═════════════════════════════════════════════════════════════════════════════════╗
║ ERROR 4: DOUBLE SESSION PREVENTION                                               ║
╠═════════════════════════════════════════════════════════════════════════════════╣
║                                                                                 ║
║  ┌─────────────────┐                                                             ║
║  │ Dosen executes   │                                                             ║
║  │ /mulai-kuliah    │                                                             ║
║  │ (second time)    │                                                             ║
║  └────────┬────────┘                                                             ║
║           │                                                                      ║
║           ▼                                                                      ║
║  ┌─────────────────────────────────────────────────────────────┐                  ║
║  │ CHECK: Is there already an open session for this class?     │                  ║
║  │                                                             │                  ║
║  │ SELECT id, opens_at, total_present                          │                  ║
║  │ FROM attendance_sessions                                    │                  ║
║  │ WHERE class_id = $1                                         │                  ║
║  │ AND session_date = CURRENT_DATE                             │                  ║
║  │ AND status = 'open'                                         │                  ║
║  └────────┬────────────────────────────────────────────────────┘                  ║
║           │                                                                      ║
║     ┌─────┴─────┐                                                                ║
║     │           │                                                                ║
║     ▼           ▼                                                                ║
║ ┌────────┐ ┌────────┐                                                             ║
║ │ NO     │ │ YES    │                                                             ║
║ │ EXIST  │ │ EXIST  │                                                             ║
║ └────────┘ └───┬────┘                                                             ║
║                │                                                                  ║
║                ▼                                                                  ║
║  ┌─────────────────────────────────────────────────────────────┐                  ║
║  │ PREVENTION RESPONSE                                         │                  ║
║  │                                                             │                  ║
║  │ "⚠️ Sesi absensi untuk kelas [X] sudah aktif!"            │                  ║
║  │                                                             │                  ║
║  │ Detail sesi aktif:                                          │                  ║
║  │ - Dibuka: 09:00 WIB                                        │                  ║
║  │ - Sisa waktu: 10:00 menit                                   │                  ║
║  │ - Sudah absen: 15 mahasiswa                                 │                  ║
║  │                                                             │                  ║
║  │ Options:                                                    │                  ║
║  │ [✅ Gunakan Sesi Ini] (default)                             │                  ║
║  │ [❌ Tutup & Buat Baru] (requires confirmation)              │                  ║
║  │                                                             │                  ║
║  │ IF "Tutup & Buat Baru":                                     │                  ║
║  │   1. Close existing session                                  │                  ║
║  │   2. Create new session                                      │                  ║
║  │   3. Carry over existing attendance records                  │                  ║
║  │   4. Notify students of change                               │                  ║
║  └─────────────────────────────────────────────────────────────┘                  ║
║                                                                                 ║
╚═════════════════════════════════════════════════════════════════════════════════╝
```

---

## 5. COMMAND LIST DETAIL

### 5.1 Registration Commands

#### `/verify`

| Attribute | Detail |
|-----------|--------|
| **Syntax** | `/verify <nim:string>` |
| **Permission** | @everyone (all members) |
| **Channel** | #verifikasi only |
| **Cooldown** | 60 seconds per user |
| **Rate Limit** | 5 attempts per hour per user |

**Input Validation:**
```python
{
    "nim": {
        "type": "string",
        "required": True,
        "pattern": r"^[0-9]{10}$",
        "error_invalid": "Format NIM tidak valid. Harus 10 digit angka.",
        "error_empty": "NIM harus diisi."
    }
}
```

**Output Format:**
```
Success (linked):
✅ Verifikasi berhasil!
Nama: Ahmad Fauzi
NIM: 2471110042
Prodi: Teknik Informatika
Kelas: B1
Role: Mahasiswa Verified, Angkatan 24, Teknik Informatika, Kelas B1

Success (needs confirmation):
🔍 NIM ditemukan!
Nama: Ahmad Fauzi
Apakah ini kamu?
[✅ Ya] [❌ Bukan]

Error (not found):
❌ NIM 2471110042 tidak ditemukan di database FIKTI.
Apakah kamu ingin mendaftar secara manual?
[📝 Daftar Manual] [❌ Batal]

Error (already linked):
⚠️ NIM ini sudah terhubung ke akun Discord lain.
Jika ini akun baru, hubungi admin.

Error (cooldown):
⏳ Tunggu {remaining}s sebelum mencoba lagi.
```

**Error Messages:**
- `ERR_NIM_FORMAT`: "Format NIM tidak valid"
- `ERR_NIM_NOT_FOUND`: "NIM tidak ditemukan di database"
- `ERR_NIM_ALREADY_LINKED`: "NIM sudah terhubung ke akun lain"
- `ERR_RATE_LIMIT`: "Terlalu banyak percobaan"
- `ERR_CHANNEL_RESTRICTED`: "Verifikasi hanya bisa dilakukan di #verifikasi"

---

#### `/register`

| Attribute | Detail |
|-----------|--------|
| **Syntax** | `/register` (opens modal) |
| **Permission** | @everyone |
| **Channel** | #verifikasi only |
| **Cooldown** | 300 seconds per user |
| **Rate Limit** | 3 attempts per day per user |

**Modal Fields:**
```python
{
    "nim": {"type": "text", "required": True, "max_length": 10},
    "nama_lengkap": {"type": "text", "required": True, "max_length": 100},
    "angkatan": {"type": "text", "required": True, "max_length": 4},
    "prodi": {"type": "text", "required": True},
    "kelas": {"type": "text", "required": True, "max_length": 5}
}
```

**Output Format:**
```
Success:
📝 Registrasi berhasil dikirim!
NIM: 2471110042
Status: Menunggu persetujuan admin
Kami akan memberitahu kamu melalui DM setelah disetujui.

Error (pending exists):
⚠️ Kamu sudah memiliki registrasi yang pending.
Status: Menunggu persetujuan
ID: REG-2026-001

Error (validation failed):
❌ Validasi gagal:
- NIM: Format tidak valid
- Angkatan: Harus tahun (2020-2030)
```

---

#### `/verify-otp`

| Attribute | Detail |
|-----------|--------|
| **Syntax** | `/verify-otp <kode:string>` |
| **Permission** | @everyone |
| **Channel** | Any |
| **Cooldown** | 30 seconds per user |
| **Rate Limit** | 3 attempts per token |

**Input Validation:**
```python
{
    "kode": {
        "type": "string",
        "required": True,
        "pattern": r"^[0-9]{6}$",
        "error_invalid": "Kode OTP harus 6 digit angka"
    }
}
```

**Output Format:**
```
Success:
✅ Verifikasi email berhasil!

Error (invalid):
❌ Kode OTP tidak valid. Sisa percobaan: 2

Error (expired):
⏰ Kode OTP sudah kedaluwarsa. Minta kode baru.
```

---

### 5.2 Attendance Commands

#### `/mulai-kuliah`

| Attribute | Detail |
|-----------|--------|
| **Syntax** | `/mulai-kuliah <kelas:string> <mata_kuliah:string> [--type offline\|online\|hybrid]` |
| **Permission** | Dosen, Admin |
| **Channel** | #admin, #dosen-channel |
| **Cooldown** | 300 seconds per kelas per hari |
| **Rate Limit** | 1 session per class per day |

**Input Validation:**
```python
{
    "kelas": {
        "type": "string",
        "required": True,
        "error_not_found": "Kelas tidak ditemukan: {value}"
    },
    "mata_kuliah": {
        "type": "string",
        "required": True,
        "error_not_found": "Mata kuliah tidak ditemukan: {value}"
    },
    "--type": {
        "type": "choice",
        "choices": ["offline", "online", "hybrid"],
        "default": "offline"
    }
}
```

**Output Format:**
```
Success:
🎓 Kuliah dimulai!
Kelas: B1
Mata Kuliah: IF201 - Pemrograman Web
Tipe: Offline
Sesi ID: SESSION-2026-001
Waktu tutup: 15 menit dari sekarang

Embed dikirim ke: #absensi-b1

Error (session exists):
⚠️ Sesi absensi untuk kelas B1 sudah aktif!
ID Sesi: SESSION-2026-001
Dibuka: 09:00 WIB
Sisa waktu: 10:00 menit

Error (not authorized):
❌ Anda tidak mengampu mata kuliah IF201.
```

---

#### `/tutup-kuliah`

| Attribute | Detail |
|-----------|--------|
| **Syntax** | `/tutup-kuliah` |
| **Permission** | Dosen (only session starter), Admin |
| **Channel** | Any |
| **Cooldown** | None |
| **Rate Limit** | None |

**Output Format:**
```
Success:
📊 Kuliah ditutup!
Mata Kuliah: IF201 - Pemrograman Web
Kelas: B1
Durasi: 90 menit

Rekap:
✅ Hadir: 25 mahasiswa
🟡 Terlambat: 3 mahasiswa
🔴 Tidak Hadir: 5 mahasiswa
❌ Belum Absen: 2 mahasiswa

Tingkat Kehadiran: 86.2%

Rekap lengkap dikirim ke: #absensi-b1

Error (no active session):
❌ Tidak ada sesi aktif untuk ditutup.
```

---

#### `/absen`

| Attribute | Detail |
|-----------|--------|
| **Syntax** | `/absen <kode:string>` |
| **Permission** | Mahasiswa Verified |
| **Channel** | Any |
| **Cooldown** | 60 seconds per user |
| **Rate Limit** | 3 attempts per session |

**Input Validation:**
```python
{
    "kode": {
        "type": "string",
        "required": True,
        "pattern": r"^[A-Z0-9]{6}$",
        "error_invalid": "Format kode tidak valid. Harus 6 karakter alphanumeric."
    }
}
```

**Output Format:**
```
Success:
✅ Absensi berhasil!
Mata Kuliah: IF201 - Pemrograman Web
Status: Hadir
Waktu: 09:05 WIB
EXP: +10

Error (invalid code):
❌ Kode absensi tidak valid. Sisa percobaan: 2

Error (expired):
⏰ Kode absensi sudah kedaluwarsa.

Error (already checked in):
⚠️ Kamu sudah absen untuk sesi ini.

Error (not enrolled):
❌ Kamu tidak terdaftar di kelas ini.
```

---

#### `/manual-absen`

| Attribute | Detail |
|-----------|--------|
| **Syntax** | `/manual-absen <mahasiswa:user> <status:present\|late\|excused> [alasan:string]` |
| **Permission** | Dosen, Admin |
| **Channel** | Any |
| **Cooldown** | None |
| **Rate Limit** | 10 per hour per user |

**Output Format:**
```
Success:
✅ Absensi manual berhasil!
Mahasiswa: Ahmad Fauzi (2471110042)
Status: Hadir (manual override)
Alasan: Discord down saat sesi berlangsung
Diverifikasi oleh: Pak Ahmad

Error (no active session):
❌ Tidak ada sesi aktif untuk kelas ini.

Error (not authorized):
❌ Anda tidak memiliki izin untuk mengubah absensi kelas ini.
```

---

#### `/buat-kode-absen`

| Attribute | Detail |
|-----------|--------|
| **Syntax** | `/buat-kode-absen <kelas:string> <mata_kuliah:string> [--durasi menit:integer]` |
| **Permission** | Dosen, Admin |
| **Channel** | DM only (for security) |
| **Cooldown** | 300 seconds |
| **Rate Limit** | 1 per 5 minutes |

**Output Format:**
```
Success (DM only):
🔐 Kode Absensi Generated!
Kelas: B1
Mata Kuliah: IF201
Kode: A7B3K9
Berlaku sampai: 10:15 WIB (15 menit)

⚠️ Bagikan kode ini melalui platform lain (Google Meet, WhatsApp, dll.)

Error (session not found):
❌ Tidak ada sesi aktif untuk kelas B1.
```

---

### 5.3 Report Commands

#### `/rekap-hari-ini`

| Attribute | Detail |
|-----------|--------|
| **Syntax** | `/rekap-hari-ini [kelas:string]` |
| **Permission** | Dosen, Admin |
| **Channel** | Any |
| **Cooldown** | 60 seconds |
| **Rate Limit** | 5 per hour |

**Output Format:**
```
📊 Rekap Absensi Hari Ini — {tanggal}

Jika kelas ditentukan:
───────────────────────
Kelas: B1
IF201 - Pemrograman Web
✅ Hadir: 25 | 🟡 Late: 3 | 🔴 Absent: 5
Rate: 86.2%

Jika semua kelas:
───────────────────────
B1: 86.2% (25/30 hadir)
B2: 78.5% (22/28 hadir)
A1: 92.3% (24/26 hadir)
```

---

#### `/rekap-mingguan`

| Attribute | Detail |
|-----------|--------|
| **Syntax** | `/rekap-mingguan <kelas:string> [minggu:integer]` |
| **Permission** | Dosen, Admin |
| **Channel** | Any |
| **Cooldown** | 120 seconds |
| **Rate Limit** | 3 per hour |

**Output Format:**
```
📅 Laporan Mingguan — B1
Minggu ke-{N}: {tanggal_awal} - {tanggal_akhir}

Total Sesi: 5
Rata-rata Kehadiran: 85.3%

Status Mahasiswa:
✅ Memenuhi minimum: 28 orang
⚠️ Di bawah minimum: 4 orang
❌ Kritis (<30%): 1 orang

Top Performers:
🥇 Ahmad Fauzi: 100% (5/5)
🥈 Budi Santoso: 100% (5/5)
🥉 Citra Dewi: 80% (4/5)

Perlu Perhatian:
⚠️ Eko Prasetyo: 40% (2/5)
❌ Dewi Lestari: 20% (1/5)
```

---

#### `/rekap-mahasiswa`

| Attribute | Detail |
|-----------|--------|
| **Syntax** | `/rekap-mahasiswa <mahasiswa:user> [mata_kuliah:string]` |
| **Permission** | Dosen, Admin, Mahasiswa (self only) |
| **Channel** | Any |
| **Cooldown** | 60 seconds |
| **Rate Limit** | 10 per hour |

**Output Format:**
```
📋 Laporan Kehadiran — Ahmad Fauzi
NIM: 2471110042 | Kelas: B1

IF201 - Pemrograman Web:
───────────────────────
Total Sesi: 15
✅ Hadir: 12
🟡 Terlambat: 2
🔴 Tidak Hadir: 1
🎯 Rate: 93.3%
🎮 Total EXP: 130

Status: ✅ Memenuhi minimal kehadiran (10x)

IF102 - Algoritma:
───────────────────────
Total Sesi: 10
✅ Hadir: 8
🟡 Terlambat: 1
🔴 Tidak Hadir: 1
🎯 Rate: 90.0%
🎮 Total EXP: 85

Status: ✅ Memenuhi minimal kehadiran (10x)
```

---

### 5.4 Gamification Commands

#### `/leaderboard`

| Attribute | Detail |
|-----------|--------|
| **Syntax** | `/leaderboard [kelas:string] [--period minggu\|bulan\|semester]` |
| **Permission** | Mahasiswa Verified |
| **Channel** | Any |
| **Cooldown** | 30 seconds |
| **Rate Limit** | 5 per hour |

**Output Format:**
```
🏆 Leaderboard Kehadiran — B1
Periode: Semester 2024/2025-Ganjil

🥇 1. Ahmad Fauzi — 98.5% (197 EXP)
🥈 2. Budi Santoso — 96.2% (192 EXP)
🥉 3. Citra Dewi — 94.1% (188 EXP)
   4. Dewi Lestari — 92.3% (184 EXP)
   5. Eko Prasetyo — 90.0% (180 EXP)
   ...
   15. Anda — 85.3% (170 EXP)

Top Badge Holders:
🏅 Week Warrior: 12 mahasiswa
🏅 Perfect Attendance: 8 mahasiswa
🏅 Streak Master: 5 mahasiswa
```

---

#### `/badges`

| Attribute | Detail |
|-----------|--------|
| **Syntax** | `/badges [mahasiswa:user]` |
| **Permission** | Mahasiswa Verified |
| **Channel** | Any |
| **Cooldown** | 30 seconds |
| **Rate Limit** | 5 per hour |

**Output Format:**
```
🏅 Badge Collection — Ahmad Fauzi

Kehadiran:
✅ Week Warrior — 7x hadir berturut-turut
✅ Perfect Attendance — Tidak absen dalam 1 semester
✅ Minimum Met — Memenuhi minimal 10x kehadiran
⬜ Streak Master — 14x hadir berturut-turut (7/14)
⬜ Attendance Legend — 100% kehadiran 1 semester

Gamifikasi:
✅ Level 15 — Mahasiswa Aktif
✅ First Quest — Menyelesaikan quest pertama
⬜ Quest Master — Menyelesaikan 10 quest

Total EXP: 1,250
Level: 15/50
Progress: ████████████░░░░░░░░ 60%
```

---

### 5.5 Admin Commands

#### `/approve-registration`

| Attribute | Detail |
|-----------|--------|
| **Syntax** | `/approve-registration <registrasi_id:string>` |
| **Permission** | Admin |
| **Channel** | #admin-registrations |
| **Cooldown** | None |
| **Rate Limit** | None |

**Output Format:**
```
✅ Registrasi Disetujui!
ID: REG-2026-001
Mahasiswa: Ahmad Fauzi (2471110042)
Role assigned: Mahasiswa Verified, Angkatan 24, TI, B1

DM notification sent to mahasiswa.
```

---

#### `/reject-registration`

| Attribute | Detail |
|-----------|--------|
| **Syntax** | `/reject-registration <registrasi_id:string> <alasan:string>` |
| **Permission** | Admin |
| **Channel** | #admin-registrations |
| **Cooldown** | None |
| **Rate Limit** | None |

**Output Format:**
```
❌ Registrasi Ditolak
ID: REG-2026-001
Mahasiswa: Ahmad Fauzi (2471110042)
Alasan: NIM tidak valid

DM notification sent to mahasiswa.
```

---

#### `/override-attendance`

| Attribute | Detail |
|-----------|--------|
| **Syntax** | `/override-attendance <session_id:string> <mahasiswa:user> <status:string> [notes:string]` |
| **Permission** | Admin |
| **Channel** | Any |
| **Cooldown** | None |
| **Rate Limit** | None |

**Output Format:**
```
✅ Absensi Di-override
Sesi: SESSION-2026-001
Mahasiswa: Ahmad Fauzi
Status Baru: Hadir
Catatan: "Klaim sudah absen, tidak ada record"
Override oleh: Admin

Audit log recorded.
```

---

### 5.6 Utility Commands

#### `/status-bot`

| Attribute | Detail |
|-----------|--------|
| **Syntax** | `/status-bot` |
| **Permission** | Admin |
| **Channel** | Any |
| **Cooldown** | 60 seconds |
| **Rate Limit** | 5 per hour |

**Output Format:**
```
🤖 Bot Status
───────────────────────
Uptime: 15 hari 3 jam 42 menit
Memory: 256 MB / 512 MB
CPU: 12.5%
Latency: 45ms

Database:
- Connected: ✅
- Pool size: 10/20
- Active queries: 3

Sessions:
- Active attendance: 2
- Pending registrations: 5

Last restart: 2026-06-23 08:00 WIB
```

---

#### `/help-attendance`

| Attribute | Detail |
|-----------|--------|
| **Syntax** | `/help-attendance` |
| **Permission** | @everyone |
| **Channel** | Any |
| **Cooldown** | 30 seconds |
| **Rate Limit** | 5 per hour |

**Output Format:**
```
📖 Panduan Absensi — FIKTI UMSU
───────────────────────────────

Untuk Mahasiswa:
• /verify <NIM> — Verifikasi akun
• /absen <kode> — Absen dengan kode
• /rekap-mahasiswa — Lihat rekap kehadiran
• /leaderboard — Lihat peringkat
• /badges — Lihat koleksi badge

Untuk Dosen:
• /mulai-kuliah <kelas> <mata_kuliah> — Mulai sesi absensi
• /tutup-kuliah — Tutup sesi absensi
• /buat-kode-absen — Generate kode absensi
• /manual-absen — Absensi manual

Untuk Admin:
• /approve-registration — Setujui registrasi
• /reject-registration — Tolak registrasi
• /override-attendance — Override absensi

Info Lebih Lanjut:
• /help-attendance — Panduan lengkap
• /status-bot — Status bot
```

---

## APPENDIX: Database Relationships

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         ENTITY RELATIONSHIP DIAGRAM                             │
└─────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
    │   students   │         │  enrollments  │         │   classes    │
    │──────────────│         │──────────────│         │──────────────│
    │ id (PK)      │◄───┐    │ id (PK)      │    ┌───│ id (PK)      │
    │ nim (UQ)     │    └────│ student_id   │    │   │ name         │
    │ nama_lengkap │         │ class_id     │────┘   │ angkatan     │
    │ angkatan     │         │ course_id    │────┐   │ prodi        │
    │ prodi        │         │ semester     │    │   └──────────────┘
    │ kelas        │         └──────────────┘    │
    │ discord_id   │                             │   ┌──────────────┐
    │ is_verified  │                             │   │   courses    │
    └──────────────┘                             │   │──────────────│
                                                 └───│ id (PK)      │
    ┌──────────────┐         ┌──────────────┐        │ code         │
    │attendance_   │         │  attendance_  │        │ name         │
    │ sessions     │         │  records      │        │ credits      │
    │──────────────│         │──────────────│        │ prodi        │
    │ id (PK)      │◄────────│ session_id   │        │ semester     │
    │ class_id     │────┐    │ student_id   │────┐   └──────────────┘
    │ course_id    │────┘    │ status       │    │
    │ session_date │         │ check_in_time│    │   ┌──────────────┐
    │ session_type │         │ check_method │    │   │   users      │
    │ opens_at     │         │ exp_earned   │    │   │──────────────│
    │ closes_at    │         └──────────────┘    │   │ id (PK)      │
    │ attendance_  │                             │   │ discord_id   │
    │   code       │         ┌──────────────┐    │   │ role         │
    │ status       │         │attendance_   │    │   └──────────────┘
    │ started_by   │────┐    │ summary      │    │
    └──────────────┘    │    │──────────────│    │   ┌──────────────┐
                        │    │ id (PK)      │    │   │course_       │
                        │    │ student_id   │────┘   │ schedules    │
                        └───►│ course_id    │        │──────────────│
                             │ semester     │        │ id (PK)      │
                             │ total_sessions│       │ course_id    │
                             │ present_count│        │ class_id     │
                             │ attendance_  │        │ lecturer_id  │
                             │   rate       │        │ day_of_week  │
                             │ is_below_    │        │ start_time   │
                             │   minimum    │        │ end_time     │
                             └──────────────┘        └──────────────┘
```

---

## APPENDIX: Cron Jobs & Scheduled Tasks

```python
SCHEDULED_TASKS = {
    "check_verification_timeout": {
        "schedule": "every 1 hour",
        "description": "Check for unverified members and send reminders/kick",
        "query": """
            SELECT * FROM audit_log 
            WHERE event_type = 'member_join'
            AND metadata->>'status' = 'pending_verification'
            AND created_at < NOW() - INTERVAL '24 hours'
        """
    },
    "check_pending_registrations": {
        "schedule": "every 30 minutes",
        "description": "Expire old pending registrations",
        "query": """
            UPDATE pending_registrations 
            SET status = 'expired' 
            WHERE status = 'pending' 
            AND expires_at < NOW()
        """
    },
    "cleanup_expired_tokens": {
        "schedule": "every 1 hour",
        "description": "Delete expired verification tokens",
        "query": """
            DELETE FROM verification_tokens 
            WHERE expires_at < NOW()
        """
    },
    "check_missing_sessions": {
        "schedule": "every 5 minutes",
        "description": "Detect classes that should have sessions but don't",
        "query": """
            SELECT cs.* FROM course_schedules cs
            LEFT JOIN attendance_sessions ases ON
                cs.course_id = ases.course_id
                AND ases.session_date = CURRENT_DATE
            WHERE cs.day_of_week = EXTRACT(DOW FROM NOW())
            AND cs.start_time <= NOW()::TIME
            AND ases.id IS NULL
        """
    },
    "update_attendance_summary": {
        "schedule": "after every attendance record insert",
        "description": "Recalculate attendance summary for affected student",
        "trigger": "ON INSERT OR UPDATE ON attendance_records"
    },
    "daily_attendance_report": {
        "schedule": "every day at 23:59",
        "description": "Send daily summary to admin channel",
        "action": "generate_daily_report_and_send"
    },
    "weekly_warning_notifications": {
        "schedule": "every Sunday at 20:00",
        "description": "Send weekly warnings to students below threshold",
        "action": "check_and_send_weekly_warnings"
    }
}
```

---

**Dokumen ini siap untuk implementasi production.**

**Catatan:**
- Semua timestamps menggunakan `TIMESTAMPTZ` untuk timezone handling
- UUID digunakan untuk primary keys (distribusi & keamanan)
- JSONB digunakan untuk metadata yang fleksibel
- Trigger digunakan untuk auto-update summary
- Index dioptimasi untuk query yang sering dijalankan
- Constraint menjaga integritas data di level database
