# 🎓 Teaching Assistant Bot — FIKTI UMSU

Bot Discord untuk Teaching Assistant berbasis OBE (Outcome-Based Education) di FIKTI UMSU.

## ✨ Fitur Utama

### 🎯 **Interface Berbasis Dropdown**
- **Tidak perlu mengetik manual** — Semua command menggunakan dropdown
- **Database-driven** — Opsi diambil dari database secara real-time
- **User-friendly** — Cukup klik dan pilih

### 📚 **Manajemen Kelas**
- Channel per kelas (otomatis dibuat)
- Isolasi data antar kelas
- Relator (PIC) per kelas

### 👥 **Registrasi Mahasiswa**
- Form registrasi via modal
- Approval system untuk admin
- Auto-assign ke channel kelas

### 📊 **Sistem Penilaian OBE**
- Tatap Muka (30%)
- Tugas Terstruktur (30%)
- Tugas Mandiri (30%)
- Attitude (10%)

### 🎮 **Gamifikasi**
- Sistem EXP dan Level
- Badge dan achievements
- Leaderboard per kelas

## 🚀 Commands

### Admin Commands

| Command | Fungsi | Interface |
|---------|--------|-----------|
| `/setup-server` | Initialize server | Button |
| `/set-relator` | Assign PIC kelas | **Dropdown** |
| `/approve` | Setujui registrasi | **Dropdown** |
| `/reject` | Tolak registrasi | **Dropdown** |
| `/list-pending` | Lihat pending | Embed |
| `/list-classes` | Lihat semua kelas | Embed |
| `/class-info` | Info kelas | **Dropdown** |

### Student Commands

| Command | Fungsi | Interface |
|---------|--------|-----------|
| `/register` | Registrasi mahasiswa | Modal Form |

## 🎨 Interface Examples

### Set Relator (Dropdown)
```
┌─────────────────────────────────────────────┐
│  📝 Set Relator (PIC Kelas)                │
│                                             │
│  Pilih kelas dan dosen dari dropdown:       │
│                                             │
│  🎓 Pilih Kelas...                    ▼    │
│  ┌─────────────────────────────────────┐   │
│  │ Alpro - A1 (TI)                    │   │
│  │ Alpro - B1 (TI)                    │   │
│  │ Pweb - A1 (SI)                     │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  👨‍🏫 Pilih Dosen...                   ▼    │
│  ┌─────────────────────────────────────┐   │
│  │ Pak Budi                           │   │
│  │ Pak Ahmad                          │   │
│  │ Bu Sarah                           │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  [✅ Konfirmasi]  [❌ Batal]              │
│                                             │
└─────────────────────────────────────────────┘
```

### Approve Student (Dropdown)
```
┌─────────────────────────────────────────────┐
│  ✅ Approve Mahasiswa                       │
│                                             │
│  Pilih mahasiswa dari dropdown:             │
│                                             │
│  👤 Pilih Mahasiswa...                 ▼    │
│  ┌─────────────────────────────────────┐   │
│  │ Budi Santoso                       │   │
│  │ NIM: 2471110042 | TI A1           │   │
│  │                                   │   │
│  │ Ahmad Hidayat                      │   │
│  │ NIM: 2471110043 | SI B1           │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  [✅ Approve]  [❌ Reject]                 │
│                                             │
└─────────────────────────────────────────────┘
```

## 📁 File Structure

```
teaching-assistant-obe/
├── src/
│   ├── main.py                    # Entry point
│   ├── config.py                  # Configuration
│   ├── database/
│   │   ├── engine.py              # DB engine (singleton)
│   │   └── models.py              # All models
│   └── bot/
│       ├── events.py              # Event handlers
│       ├── commands/
│       │   ├── registration.py    # Registration commands
│       │   └── admin.py           # Admin commands (with dropdowns)
│       └── views/
│           ├── __init__.py
│           ├── modals.py          # Modal forms
│           ├── buttons.py         # Button components
│           ├── selects.py         # Database-driven dropdowns
│           └── select_views.py    # Combined views
├── Dockerfile                     # Railway deployment
├── railway.json                   # Railway config
├── .env.example                   # Environment template
└── pyproject.toml                 # Dependencies
```

## 🔧 Setup

### 1. Clone & Install
```bash
git clone https://github.com/halimaulana84/teaching-assistant-obe.git
cd teaching-assistant-obe
pip install -e .
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your values
```

### 3. Discord Bot Setup
1. Buat bot di [Discord Developer Portal](https://discord.com/developers/applications)
2. Copy **Token** dan **Application ID**
3. Invite bot ke server dengan permissions:
   - Manage Channels
   - Manage Roles
   - Send Messages
   - Embed Links
   - Attach Files

### 4. Deploy to Railway
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/halimaulana84/teaching-assistant-obe.git
git push -u origin main
```

### 5. Initialize Server
1. Jalankan `/setup-server` di Discord
2. Assign role Admin ke diri sendiri
3. Assign role Dosen ke dosen-dosen
4. Gunakan `/set-relator` untuk assign PIC kelas

## 📊 Database Schema

```sql
-- Mahasiswa
CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    discord_id VARCHAR(20) UNIQUE NOT NULL,
    nim VARCHAR(10) UNIQUE NOT NULL,
    nama_lengkap VARCHAR(100) NOT NULL,
    prodi VARCHAR(10) NOT NULL,
    angkatan INT NOT NULL,
    kelas VARCHAR(10) NOT NULL,
    no_wa VARCHAR(20),
    is_verified BOOLEAN DEFAULT FALSE,
    exp INT DEFAULT 0,
    level INT DEFAULT 1
);

-- Kelas
CREATE TABLE class_channels (
    id SERIAL PRIMARY KEY,
    nama_kelas VARCHAR(50) UNIQUE NOT NULL,
    mata_kuliah VARCHAR(100),
    prodi VARCHAR(10) NOT NULL,
    angkatan INT NOT NULL,
    kelas_code VARCHAR(10) NOT NULL,
    channel_id VARCHAR(20),
    role_id VARCHAR(20)
);

-- Relator
CREATE TABLE relators (
    id SERIAL PRIMARY KEY,
    dosen_discord_id VARCHAR(20) UNIQUE NOT NULL,
    dosen_nama VARCHAR(100) NOT NULL,
    class_channel_id INT REFERENCES class_channels(id)
);

-- Registrasi Pending
CREATE TABLE pending_registrations (
    id SERIAL PRIMARY KEY,
    discord_id VARCHAR(20) UNIQUE NOT NULL,
    nim VARCHAR(10) NOT NULL,
    nama_lengkap VARCHAR(100) NOT NULL,
    prodi VARCHAR(10) NOT NULL,
    angkatan INT NOT NULL,
    kelas VARCHAR(10) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending'
);
```

## 🎯 Flow Sistem

```
┌─────────────────────────────────────────────────────────────┐
│  1. MAHASISWA JOIN SERVER                                   │
│     ↓                                                       │
│  2. BOT SEND WELCOME KE #registrasi + DM                    │
│     ↓                                                       │
│  3. MAHASISWA KETIK: /register                              │
│     ↓                                                       │
│  4. MODAL FORM MUNCUL:                                      │
│     - NIM (10 digit)                                        │
│     - Nama Lengkap                                          │
│     - Prodi (TI/SI/SD)                                      │
│     - Kelas (A1, B2, C1)                                    │
│     - No WA (opsional)                                      │
│     ↓                                                       │
│  5. BOT VALIDASI + SIMPAN KE pending_registrations          │
│     ↓                                                       │
│  6. BOT KIRIM NOTIFIKASI KE #admin                          │
│     ↓                                                       │
│  7. ADMIN KETIK: /approve                                   │
│     ↓                                                       │
│  8. DROPDOWN MUNCUL:                                        │
│     - Pilih mahasiswa dari dropdown                         │
│     - Klik Approve                                          │
│     ↓                                                       │
│  9. BOT:                                                    │
│     ✓ Create channel #kelas-a1-si (if not exist)            │
│     ✓ Create role @Kelas-A1-SI                              │
│     ✓ Add role ke mahasiswa                                 │
│     ✓ Set permissions                                       │
│     ↓                                                       │
│ 10. MAHASISWA SEKARANG LIHAT:                               │
│     ✓ #umum                                                 │
│     ✓ #pengumuman                                           │
│     ✓ #kelas-a1-si (kelasnya)                               │
│     ❌ #kelas-b1-si (TIDAK terlihat)                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 📝 License

MIT License - Halim Maulana

## 🤝 Contributing

Contributions welcome! Please open an issue or PR.
