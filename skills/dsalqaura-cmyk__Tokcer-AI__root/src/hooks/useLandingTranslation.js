import { useState, useEffect } from 'react';

const translations = {
  id: {
    // Navbar
    navProblem: "Masalah Utama",
    navEcosystem: "Ekosistem",
    navExplore: "Eksplorasi",
    navAbout: "Tentang Kami",
    navPricing: "Pricing",
    navLogin: "Member Area",
    navPartner: "Become a Partner",
    navWaitlist: "Daftar Sekarang",
    navContact: "Contact Us",
    navDashboard: "Dashboard",
    navStores: "Toko",

    // Hero
    heroBadge: "Cara Baru Kelola Toko Online",
    heroTitle1: "Urusan Toko Beres.",
    heroTitle2: "Cuan Maksimal.",
    heroDesc: "Pantau omzet, hitung cuan bersih, dan urus semua marketplace dari satu layar. Tinggalkan cara lama, waktunya scale-up!",

    // Problem
    probTitle1: "Kenapa Toko ",
    probTitle2: "Gitu-Gitu Aja?",
    prob1Title: "Capek Rekap Manual",
    prob1Desc: "Waktu abis cuma buat download dan nyamain data Excel dari banyak marketplace. Padahal harusnya bisa mikirin strategi promo.",
    prob2Title: "Profit Bocor Alus",
    prob2Desc: "Berhenti nebak-nebak cuan. Kelihatannya omzet gede, tapi pas dipotong biaya admin platform, nyatanya malah boncos.",

    // Solution
    solSubtitle: "Solusi All-in-One",
    solTitle1: "Pegang Kendali.",
    solTitle2: "Fokus Gedein Toko.",
    solDesc: "Tokcer AI beresin semua urusan data otomatis di belakang layar. Waktumu balik lagi buat fokus naikin konversi dan inovasi produk.",
    solStat1: "Lebih Cepat",
    solStat2: "Akurasi Cuan",

    // Ecosystem
    ecoTitle1: "Ekosistem ",
    ecoTitle2: "Kami",
    ecoDesc: "Semua tools andalan ngumpul di satu tempat biar kerjamu makin sat-set.",

    // Testimonial
    testiTitle: "Kata Temen-temen Seller",
    testiDesc: "Udah banyak yang ngerasain bedanya setelah pakai Tokcer AI.",
    testi1Quote: "\"Gila sih, ngurus 3 toko marketplace jadi gampang banget. Tim admin bisa hemat belasan jam tiap minggu.\"",
    testi1Author: "Andi R.",
    testi1Role: "Top Seller Fashion",
    testi2Quote: "\"Fitur AI-nya ngebantu banget pas mentok bikin caption. Sejak pake Tokcer, CTR produk naik lumayan kerasa.\"",
    testi2Author: "Denny K.",
    testi2Role: "Owner TechStore",
    testi3Quote: "\"Dulu paling males kalau stok di satu toko abis tapi di toko lain belum di-update. Sekarang udah sinkron semua.\"",
    testi3Author: "Citra W.",
    testi3Role: "Distributor Kosmetik",
    testi4Quote: "\"Akhirnya tau margin pasti tiap produk. Kelihatan banget mana barang yang emang ngasih cuan, mana yang cuma numpang lewat.\"",
    testi4Author: "Budi S.",
    testi4Role: "Seller Elektronik",

    // About Us
    aboutHeroBadge: "Tokcer AI",
    aboutHeroTitle1: "Dari ",
    aboutHeroTitle2: "Prompt",
    aboutHeroTitle3: " Jadi Cuan.",
    aboutHeroDesc: "Kita bikin sistem jualan AI yang beneran bisa dipake seller lokal — nggak ribet, nggak butuh skill coding.",
    aboutStoryTag: "Kenapa Tokcer AI Lahir",
    aboutStoryDesc1: "Jutaan seller kerja keras tiap hari—tapi kalah saing karena ",
    aboutStoryDesc2: "nggak pake senjata yang pas",
    aboutStoryDesc3: ". Caption ngetik sendiri. Profit ngawang. Algoritma ganti-ganti. Tokcer AI hadir buat nutup celah itu—pakai sistem yang ",
    aboutStoryDesc4: "paham konteks tokomu dan tren algoritma terbaru.",
    aboutVisionTag: "Visi Kita",
    aboutVisionDesc: "Jadi tulang punggung pertumbuhan buat semua seller UMKM — dari yang baru merintis sampai yang omzetnya udah nembus ratusan juta.",
    aboutMissionTag: "Misi",
    aboutMission1: "Bikin AI yang ngerti bahasanya seller lokal, bukan bahasa robot Silicon Valley.",
    aboutMission2: "Otomatisasi kerjaan berulang biar kamu bisa fokus jualan.",
    aboutMission3: "Kasih data market yang biasanya cuma dipegang brand gede, khusus buat seller kecil.",
    aboutMission4: "Bangun sistem yang bakal terus ngebantu seiring makin gedenya tokomu.",
    aboutTeamTag: "Orang di Balik Layar",
    aboutTeamFounderRole: "Pencetus ide dan penentu arah Tokcer AI—yang paling tahu masalah seller di lapangan dan bagian 'request' fitur biar sesuai kebutuhan pasar.",
    aboutTeamCTORole: "Arsitek utama yang bener-bener ngetik kode dan ngebangun seluruh sistem Tokcer AI dari nol sampai jalan mulus 24/7 tanpa ngelag.",
    aboutPartnersTag: "Kemitraan Strategis",
    aboutFooterDesc1: "Tokcer AI itu bukan cuma software. Ini ",
    aboutFooterDesc2: "partner kerjamu",
    aboutFooterDesc3: " yang jalan diem-diem di belakang layar—biar cuan ngalir terus pas kamu lagi tidur.",

    // Waitlist CTA
    ctaTitle: "Yuk, Scale Up Sekarang!",
    ctaDesc: "Masuk ke waitlist kita buat dapetin akses duluan. Slot buat Beta testing terbatas banget ya!",
    ctaBtn: "Daftar Sekarang",

    // Footer
    footerCopyright: "© 2026. Elevate Your E-commerce.",
    footerPrivacy: "Privasi",
    footerTerms: "Syarat",
    footerContact: "Hubungi Kami",

    // Pricing
    pricingComingSoonTitle: "Pricing",
    pricingComingSoonDesc: "Kami sedang menyiapkan paket harga terbaik untuk kamu. Segera hadir!",
    pricingComingSoonBadge: "Segera Hadir",

    // Waitlist Modal
    wlBadge: "Akses Prioritas",
    wlTitle: "Daftar Sekarang",
    wlDesc: "Jadilah yang pertama pakai Tokcer AI. Slot Beta terbatas buat kamu yang mau curi start di market.",
    wlFullName: "Nama Lengkap",
    wlEmail: "Email Aktif",
    wlPhone: "No. Telp / WhatsApp",
    wlAffId: "ID Affiliator",
    wlOptional: "(Opsional)",
    wlBusinessType: "Jenis Usaha",
    wlBusinessPlaceholder: "Cth: Fashion, Kosmetik, dll",
    wlPlatformLabel: "Platform Jualan Saat Ini",
    wlPlatformOtherPlaceholder: "Sebutkan platform/toko offline...",
    wlSubmitLoading: "Mengirim Data...",
    wlSubmitBtn: "Daftar Sekarang",
    wlPassword: "Buat Kata Sandi",
    wlConfirmPassword: "Konfirmasi Kata Sandi",
    wlErrPassword: "Password minimal 6 karakter!",
    wlErrMatch: "Konfirmasi password tidak cocok!",
    wlSuccessTitle: "Berhasil Mendaftar!",
    wlSuccessDesc: "Terima kasih telah bergabung! Kami akan segera menghubungi Anda melalui email/WhatsApp.",
    wlErrDuplicate: "Email sudah terdaftar di waitlist!",
    wlErrEmail: "Format email tidak valid!",
    wlErrGeneral: "Terjadi kesalahan, silakan coba lagi."
  },
  en: {
    // Navbar
    navProblem: "Core Problem",
    navEcosystem: "Ecosystem",
    navExplore: "Explore",
    navAbout: "About Us",
    navPricing: "Pricing",
    navLogin: "Member Area",
    navPartner: "Become a Partner",
    navWaitlist: "Register",
    navContact: "Contact Us",
    navDashboard: "Dashboard",
    navStores: "Stores",

    // Hero
    heroBadge: "New Way to Manage Online Stores",
    heroTitle1: "Store Managed.",
    heroTitle2: "Maximized Profit.",
    heroDesc: "Monitor revenue, calculate net profit, and manage all marketplaces from one screen. Leave the old ways behind, it's time to scale up!",

    // Problem
    probTitle1: "Why is your store ",
    probTitle2: "Stuck?",
    prob1Title: "Tired of Manual Recaps",
    prob1Desc: "Wasting time just to download and match Excel data from multiple marketplaces. You should be thinking about promo strategies.",
    prob2Title: "Hidden Profit Leaks",
    prob2Desc: "Stop guessing your profit. Revenue looks huge, but after platform admin fees, you're actually losing money.",

    // Solution
    solSubtitle: "All-in-One Solution",
    solTitle1: "Take Control.",
    solTitle2: "Focus on Growth.",
    solDesc: "Tokcer AI automatically handles all data behind the scenes. Your time is returned to focus on increasing conversions and product innovation.",
    solStat1: "Faster",
    solStat2: "Profit Accuracy",

    // Ecosystem
    ecoTitle1: "Our ",
    ecoTitle2: "Ecosystem",
    ecoDesc: "Tokcer AI integrates directly with your favorite e-commerce platforms and payment gateways in Indonesia.",

    // Testimonial
    testiTitle: "What Other Sellers Say",
    testiDesc: "Many have felt the difference after using Tokcer AI.",
    testi1Quote: "\"It's crazy, managing 3 marketplaces is so easy now. Admin team can save dozens of hours every week.\"",
    testi1Author: "Andi R.",
    testi1Role: "Top Fashion Seller",
    testi2Quote: "\"The AI feature really helps when stuck making captions. Since using Tokcer, product CTR has noticeably increased.\"",
    testi2Author: "Denny K.",
    testi2Role: "TechStore Owner",
    testi3Quote: "\"Used to be so lazy when stock in one store ran out but another store wasn't updated yet. Now they are all in sync.\"",
    testi3Author: "Citra W.",
    testi3Role: "Cosmetics Distributor",
    testi4Quote: "\"Finally know the exact margin of each product. Very clear which items actually give profit and which just pass through.\"",
    testi4Author: "Budi S.",
    testi4Role: "Electronics Seller",

    // About Us
    aboutHeroBadge: "Tokcer AI",
    aboutHeroTitle1: "From ",
    aboutHeroTitle2: "Prompt",
    aboutHeroTitle3: " To Profit.",
    aboutHeroDesc: "We built an AI selling system that local sellers can actually use — no hassle, no coding skills needed.",
    aboutStoryTag: "Why Tokcer AI Was Born",
    aboutStoryDesc1: "Millions of sellers work hard every day—but lose out because ",
    aboutStoryDesc2: "they don't use the right weapons",
    aboutStoryDesc3: ". Typing captions manually. Guessing profits. Algorithms changing constantly. Tokcer AI is here to bridge that gap—using a system that ",
    aboutStoryDesc4: "understands your store context and the latest algorithmic trends.",
    aboutVisionTag: "Our Vision",
    aboutVisionDesc: "To be the backbone of growth for all SME sellers — from those just starting out to those with hundreds of millions in revenue.",
    aboutMissionTag: "Mission",
    aboutMission1: "Build AI that understands the local seller's language, not Silicon Valley robot speak.",
    aboutMission2: "Automate repetitive tasks so you can focus on selling.",
    aboutMission3: "Provide market data usually only held by big brands, specifically for small sellers.",
    aboutMission4: "Build a system that will continue to help as your store grows bigger.",
    aboutTeamTag: "People Behind the Scenes",
    aboutTeamFounderRole: "The idea initiator and direction setter for Tokcer AI—who knows the seller's problems in the field best and requests features to match market needs.",
    aboutTeamCTORole: "The main architect who actually writes the code and built the entire Tokcer AI system from scratch to run smoothly 24/7 without lag.",
    aboutPartnersTag: "Strategic Partners",
    aboutFooterDesc1: "Tokcer AI is not just software. It's your ",
    aboutFooterDesc2: "working partner",
    aboutFooterDesc3: " that runs quietly behind the scenes—so profit keeps flowing while you sleep.",

    // Waitlist CTA
    ctaTitle: "Let's Scale Up Now!",
    ctaDesc: "Join our waitlist to get early access. Slots for Beta testing are extremely limited!",
    ctaBtn: "Register",

    // Footer
    footerCopyright: "© 2026. Elevate Your E-commerce.",
    footerPrivacy: "Privacy",
    footerTerms: "Terms",
    footerContact: "Contact Us",

    // Pricing
    pricingComingSoonTitle: "Pricing",
    pricingComingSoonDesc: "We're preparing the best pricing plans for you. Coming soon!",
    pricingComingSoonBadge: "Coming Soon",

    // Waitlist Modal
    wlBadge: "Priority Access",
    wlTitle: "Register",
    wlDesc: "Be the first to leverage Tokcer AI. Beta slots are limited for those who want to get a head start in the market.",
    wlFullName: "Full Name",
    wlEmail: "Active Email",
    wlPhone: "Phone / WhatsApp",
    wlAffId: "Affiliate ID",
    wlOptional: "(Optional)",
    wlBusinessType: "Business Type",
    wlBusinessPlaceholder: "e.g. Fashion, Cosmetics, etc.",
    wlPlatformLabel: "Current Selling Platforms",
    wlPlatformOtherPlaceholder: "Mention your platform/offline store...",
    wlSubmitLoading: "Sending Data...",
    wlSubmitBtn: "Register Now",
    wlPassword: "Create Password",
    wlConfirmPassword: "Confirm Password",
    wlErrPassword: "Password must be at least 6 characters!",
    wlErrMatch: "Passwords do not match!",
    wlSuccessTitle: "Successfully Registered!",
    wlSuccessDesc: "Thank you for joining! We will contact you soon via email/WhatsApp.",
    wlErrDuplicate: "Email already registered in the waitlist!",
    wlErrEmail: "Invalid email format!",
    wlErrGeneral: "An error occurred, please try again."
  }
};

export const useLandingTranslation = () => {
  const [lang, setLang] = useState(localStorage.getItem('tokcer_lang') || 'id');

  useEffect(() => {
    const handleStorageChange = () => {
      setLang(localStorage.getItem('tokcer_lang') || 'id');
    };
    window.addEventListener('storage', handleStorageChange);
    window.addEventListener('lang-change', handleStorageChange);
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('lang-change', handleStorageChange);
    };
  }, []);

  const toggleLang = (newLang) => {
    localStorage.setItem('tokcer_lang', newLang);
    setLang(newLang);
    window.dispatchEvent(new Event('lang-change'));
  };

  const t = (key) => translations[lang][key] || key;

  return { lang, toggleLang, t };
};
