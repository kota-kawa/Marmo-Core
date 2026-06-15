# ITSM-Open Tickets Agile - Scrum Board
**Project Status**: Sprint 3 Completed / Finalizing Project

---

## 🏃 Sprints
| Sprint Name | Status | Goal |
| :--- | :--- | :--- |
| **Sprint 1: Foundation & Public Access** | ✅ DONE | Laravel 13 Setup, Supabase, & UI Mahasiswa Dasar. |
| **Sprint 2: Multi-Role Support & Ops** | ✅ DONE | Smart Form (MHS/DSN/STF), Dashboard IT, & Status Tracking. |
| **Sprint 3: Executive Insights** | ✅ DONE | Dashboard Kepala IT, Analitik Chart, & Monitoring Pekerjaan Staff. |

---

## 📝 Tasks

### 🟢 Done (Sudah Selesai)
| Task ID | Task Name | Category | Priority |
| :--- | :--- | :--- | :--- |
| **TASK-01** | Laravel 13 Initial Setup (Laragon) | Architecture | High |
| **TASK-02** | Supabase Connection & Driver Config (SSL Fixed) | Database | High |
| **TASK-03** | DB Migration & User Management (UUID Support) | Database | High |
| **TASK-04** | DB Migration: Categories, Tickets, Replies | Database | High |
| **TASK-05** | Database Seeder: ITSM Categories & Admin Acct | Database | Medium |
| **TASK-06** | Setup Livewire Layout & Components | UI/UX | Medium |
| **TASK-07** | Implementing Clean White/Blue Theme | UI/UX | High |
| **TASK-08** | Logo Branding Integration | UI/UX | Low |
| **TASK-09** | **REVISED**: Smart Multi-user Form (No-Login Path) | Features | High |
| **TASK-10** | Role Middleware & Authentication for Staff | Auth | High |
| **TASK-11** | Custom Staff Sidebar & Layout | UI/UX | Medium |
| **TASK-12** | WhatsApp Hub Logic (wa.me formatter) | Integration | High |
| **TASK-13** | Real-time Status Quick-Update System | Features | High |
| **TASK-14** | Table Performance (Eager Loading Relationship) | Backend | Medium |
| **TASK-16** | Executive Analytics Charts (ApexCharts) | Features | Medium |
| **TASK-18** | **NEW**: Halaman Detail Pekerjaan Staff (Read-only Tracker) | Features | High |
| **TASK-19** | **NEW**: Fix Session Trap Logout & DB Enum Override (Kepala IT) | Backend | High |

### 🟡 In Progress (Sedang Dikerjakan)
| Task ID | Task Name | Category | Priority |
| :--- | :--- | :--- | :--- |
| **TASK-15** | Final Verification: Multi-device Responsive Test | Testing | Medium |

### 🔴 To Do (Daftar Antrean)
| Task ID | Task Name | Category | Priority |
| :--- | :--- | :--- | :--- |
| **TASK-17** | Ticket Reply System (Thread Management) | Features | High |

---

## 🏛️ Stories & Epics

### Epic 1: Sistem Pengaduan Terintegrasi (Omni-User)
- **User Story**: Sebagai Mahasiswa/Dosen/Staff, saya ingin mengirim kendala IT secara instan tanpa login agar proses pelaporan tidak terhambat masalah kredensial.
- **Progress**: 100% (Completed - Multi-user Smart Form Support)

### Epic 2: Operasional Dukungan IT (Staff)
- **User Story**: Sebagai Staff IT, saya ingin melihat antrean lengkap dengan deskripsi dan bisa mengganti status secara langsung untuk koordinasi tim.
- **Progress**: 100% (Completed - Dashboard with Description & Inline Status Update)

### Epic 3: Monitoring Strategis (Kepala IT)
- **User Story**: Sebagai Kepala IT, saya ingin melihat statistik kendala IT melalui grafik secara visual dan memantau detail historis pekerjaan staff di lapangan.
- **Progress**: 100% (Completed - Executive Analytics Dashboard & Staff Work Detail Table)
