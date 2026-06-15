# 📐 TOKCER AI DATABASE ERD & SCHEMA BLUEPRINT (FASE 1 - MEI 2026)
**Panduan Struktur Relasi Tabel Database Supabase Produksi & Staging Tokcer AI**

---

## 📊 1. VISUALISASI INTEGRITAS ENTITAS (ERD MERMAID)

```mermaid
erDiagram
    auth_users ||--|| PROFILES : "id"
    PROFILES ||--o| PARTNERS : "partner profile"
    PROFILES ||--o{ CLIENTS : "partner_id"
    PROFILES ||--o{ ORDERS : "user_id"
    PROFILES ||--o{ PRODUCTS : "user_id"
    PROFILES ||--o{ MARKETPLACE_CONNECTIONS : "user_id"
    PROFILES ||--o{ SUPPORT_TICKETS : "user_id"
    PROFILES ||--o{ PARTNER_IDEAS : "partner_id"
    PROFILES ||--o{ PAYOUTS : "partner_id"
    PROFILES ||--o{ AI_USAGE_LOGS : "user_id"
    PROFILES ||--o{ SKU_CALCULATIONS : "user_id"
    auth_users ||--o{ TRANSACTIONS : "user_id"

    VIRAL_TEMPLATES ||--o{ UPLOAD_QUEUE : "referenced via video_path ID"
    PRICING_PLANS ||--o{ CLIENTS : "plan"
    PLATFORM_FEES ||--o{ SKU_CALCULATIONS : "platform category preset"
    AI_CONFIGS ||--o{ AI_CONFIGS_HISTORY : "config_key"

    PROFILES {
        uuid id PK "FK auth_users.id"
        text email UK
        text full_name
        text role "admin | partner | user"
        text subscription_plan "starter | pro | elite | ultimate"
        integer ai_tokens "Kredit Koin AI"
        text avatar_url
        timestamptz created_at
        timestamptz updated_at
    }

    PARTNERS {
        uuid id PK_FK "FK profiles.id"
        text email UK
        text full_name
        text whatsapp
        text bank_name
        text bank_account
        text ref_code UK "Kode Unik TKC-xxx"
        text tier "bronze | silver | gold | platinum"
        bigint total_omzet "Akumulasi Komisi"
        text status "active | suspended"
        timestamptz created_at
        timestamptz updated_at
    }

    CLIENTS {
        uuid id PK "FK profiles.id / application_id"
        uuid partner_id FK "profiles.id"
        text shop_name
        text email UK
        text whatsapp
        text plan "starter | pro | elite | ultimate"
        text billing_cycle "Monthly | Yearly"
        text business_type
        jsonb platforms
        text ref "Referral code / partner name"
        text status "active | pending"
        text payment_method
        text payment_proof_url
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
    }

    ORDERS {
        uuid id PK
        uuid user_id FK "profiles.id"
        text order_id UK
        timestamptz order_date
        text product_name
        integer quantity
        numeric total_amount
        text platform "shopee | tiktok"
        text store_name
        text status
        timestamptz created_at
    }

    PRODUCTS {
        uuid id PK
        uuid user_id FK "profiles.id"
        text product_name
        text sku
        numeric price
        integer stock
        text category
        text platform "shopee | tiktok"
        text store_name
        text image_url
        text status
        timestamptz created_at
    }

    MARKETPLACE_CONNECTIONS {
        uuid id PK
        uuid user_id FK "profiles.id"
        text platform "shopee | tiktok"
        text shop_name
        text shop_id
        text access_token
        text refresh_token
        text status
        timestamptz connected_at
        timestamptz expires_at
        timestamptz token_expiry
        text sync_status
    }

    SUPPORT_TICKETS {
        uuid id PK
        uuid user_id FK "profiles.id"
        text type
        text description
        text screenshot_url
        text status "open | resolved"
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
    }

    PARTNER_IDEAS {
        uuid id PK
        uuid partner_id FK "profiles.id"
        text title
        text content
        text status "pending | reviewed | ignored"
        timestamptz created_at
    }

    PAYOUTS {
        uuid id PK
        uuid partner_id FK "profiles.id"
        bigint amount
        text period
        text status "pending | paid"
        text bank_name
        text bank_account
        text notes
        timestamptz created_at
    }

    AI_CONFIGS {
        uuid id PK
        text key UK
        text value
        text description
        boolean is_active
        uuid updated_by
        timestamptz created_at
        timestamptz updated_at
    }

    AI_CONFIGS_HISTORY {
        uuid id PK
        text config_key "FK ai_configs.key"
        text old_value
        text new_value
        uuid changed_by
        timestamptz changed_at
    }

    AI_USAGE_LOGS {
        uuid id PK
        uuid user_id FK "profiles.id"
        text feature
        text prompt
        text response
        integer tokens_used
        timestamptz created_at
    }

    PRICING_PLANS {
        text id PK
        text name
        numeric price_monthly
        numeric price_yearly
        jsonb features
        boolean is_active
        timestamptz created_at
    }

    PLATFORM_FEES {
        uuid id PK
        text platform_name "shopee | tiktok"
        text category_name
        numeric commission_percent
        numeric logistics_fixed_fee
        boolean is_active
        timestamptz updated_at
    }

    SKU_CALCULATIONS {
        uuid id PK
        uuid user_id FK "profiles.id"
        text sku_name
        numeric modal_beli
        numeric biaya_packaging
        numeric biaya_lain_lain
        numeric biaya_ongkir_inbound
        numeric total_hpp
        text platform
        text category
        numeric komisi_persen
        numeric logistik_flat
        numeric ads_persen
        numeric affiliator_persen
        numeric admin_fee_flat
        numeric target_margin_persen
        numeric harga_jual_aktual
        numeric diskon_voucher
        integer estimasi_order_per_bulan
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
    }

    TRANSACTIONS {
        uuid id PK
        uuid user_id FK "auth_users.id"
        text order_id UK "Midtrans Order ID"
        text plan_name
        decimal amount
        integer tokens_to_add
        text status "pending | settlement | capture | expire | deny"
        text payment_type
        text snap_token
        jsonb raw_notification
        timestamptz created_at
        timestamptz updated_at
    }

    VIRAL_TEMPLATES {
        uuid id PK
        text tips_title
        text tips_content "Naskah voiceover"
        text visual_prompt "Prompt latar gambar"
        boolean used "default false"
        timestamptz created_at
        timestamptz updated_at
    }

    UPLOAD_QUEUE {
        uuid id PK
        text video_path "Path file video hasil render"
        text caption "Caption postingan + tagar"
        text account_platform "default tiktok"
        text account_username
        text status "pending | processing | posted | failed"
        date scheduled_date
        integer preferred_hour "Jam prime time (12, 17, 19)"
        timestamptz actual_post_time
        timestamptz created_at
        timestamptz updated_at
    }
```

---

## 🔒 2. ATURAN INTEGRITAS RELASI DATA

1. **Pusat Komando Profil (`profiles`):**  
   Seluruh tabel operasional (`orders`, `products`, `sku_calculations`, `support_tickets`) wajib menggunakan foreign key `user_id` yang merujuk langsung ke `profiles.id` (bukan langsung ke auth table) guna mempermudah join data di tingkat aplikasi.
2. **Mitra (`partners`):**  
   Tabel partner menggunakan `id` yang diikat 1:1 ke `profiles.id`. Kode referral disimpan di kolom `ref_code` (misalnya `TKC-xxx`) dan divalidasi silang ke kolom `ref` di tabel `clients`.
3. **Akuntansi Ledger Instan (`transactions`):**  
   Bekerja sebagai tabel audit sinkronisasi Midtrans Payment Gateway untuk penambahan plan akun dan koin token AI pengguna secara instan.
4. **Siklus Autopilot Konten (`viral_templates` -> `upload_queue`):**  
   * Draf konten dibuat di `viral_templates`. Setelah disetujui atau dikirim ke sistem, baris antrean baru akan dimasukkan ke `upload_queue`.
   * Kolom `video_path` mengikat nama berkas video ke ID `viral_templates` spesifik (`video_render_<template_id>.mp4`) untuk sinkronisasi rendering dinamis pada saat posting otomatis berjalan.

---
*Dokumen ERD ini resmi disahkan sebagai acuan utama kerja Fase 1 Tokcer AI.*
