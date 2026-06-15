import React from 'react';
import Navbar from '../components/Navbar.jsx';
import Footer from '../components/Footer.jsx';

const LegalLayout = ({ title, children }) => (
  <div className="bg-black min-h-screen text-white font-['Inter',sans-serif]">
    <Navbar onOpenPartner={() => {}} onOpenWaitlist={() => {}} />
    <main className="max-w-4xl mx-auto px-6 py-32">
      <h1 className="text-4xl font-black uppercase tracking-tighter mb-12 text-orange-500 border-b border-zinc-800 pb-6">{title}</h1>
      <div className="prose prose-invert prose-orange max-w-none space-y-8 text-zinc-400 leading-relaxed">
        {children}
      </div>
    </main>
    <Footer />
  </div>
);

export const TermsPage = () => (
  <LegalLayout title="Terms & Conditions">
    <section>
      <h2 className="text-xl font-bold text-white mb-4 uppercase tracking-widest">1. Ketentuan Penggunaan</h2>
      <p>Dengan mengakses dan menggunakan Tokcer AI, Anda setuju untuk terikat oleh Syarat dan Ketentuan ini. Layanan kami disediakan untuk membantu optimasi e-commerce melalui teknologi AI.</p>
    </section>
    <section>
      <h2 className="text-xl font-bold text-white mb-4 uppercase tracking-widest">2. Akun Pengguna</h2>
      <p>Anda bertanggung jawab untuk menjaga kerahasiaan akun dan kata sandi Anda. Segala aktivitas yang terjadi di bawah akun Anda adalah tanggung jawab Anda sepenuhnya.</p>
    </section>
    <section>
      <h2 className="text-xl font-bold text-white mb-4 uppercase tracking-widest">3. Batasan Tanggung Jawab</h2>
      <p>Tokcer AI tidak bertanggung jawab atas kerugian bisnis, penurunan penjualan, atau kesalahan teknis yang disebabkan oleh pihak ketiga (seperti marketplace Shopee/TikTok).</p>
    </section>
  </LegalLayout>
);

export const PrivacyPage = () => (
  <LegalLayout title="Privacy Policy">
    <section>
      <h2 className="text-xl font-bold text-white mb-4 uppercase tracking-widest">1. Pengumpulan Data</h2>
      <p>Kami mengumpulkan informasi yang Anda berikan saat pendaftaran dan data yang dihasilkan dari integrasi marketplace untuk keperluan analisis optimasi.</p>
    </section>
    <section>
      <h2 className="text-xl font-bold text-white mb-4 uppercase tracking-widest">2. Keamanan Data</h2>
      <p>Data Anda dienkripsi dan disimpan dengan standar keamanan tinggi. Kami tidak akan pernah menjual data Anda kepada pihak ketiga manapun.</p>
    </section>
  </LegalLayout>
);

export const RefundPage = () => (
  <LegalLayout title="Refund Policy">
    <section className="bg-orange-500/10 border border-orange-500/20 p-8 rounded-3xl">
      <h2 className="text-xl font-bold text-orange-500 mb-4 uppercase tracking-widest">Kebijakan Pengembalian Dana</h2>
      <p className="text-white font-medium text-lg leading-relaxed italic">
        "Seluruh transaksi pembayaran untuk paket langganan (Pro, Elite, Ultimate) di Tokcer AI bersifat final dan <strong>Non-Refundable (Tidak dapat dikembalikan)</strong> dengan alasan apapun."
      </p>
      <p className="mt-6 text-zinc-400">
        Kami menyarankan pengguna untuk menggunakan paket Starter (Gratis) terlebih dahulu untuk mencoba fitur kami sebelum memutuskan untuk berlangganan paket berbayar.
      </p>
    </section>
    <section>
      <h2 className="text-xl font-bold text-white mb-4 uppercase tracking-widest">Pembatalan Langganan</h2>
      <p>Anda dapat membatalkan langganan Anda kapan saja untuk mencegah penagihan di periode berikutnya, namun dana yang sudah dibayarkan untuk periode berjalan tidak dapat dikembalikan.</p>
    </section>
  </LegalLayout>
);
