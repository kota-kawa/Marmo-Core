import React, { useState } from 'react';
import { useLandingTranslation } from '../../hooks/useLandingTranslation.js';

const Faq = () => {
  const { lang } = useLandingTranslation();
  const [activeCategory, setActiveCategory] = useState(0);
  const [openIndex, setOpenIndex] = useState(null);

  const categories = [
    { id: 'integrasi', name: '🔌 Integrasi & Setup', nameEn: '🔌 Integration & Setup' },
    { id: 'data', name: '📊 Data & Dashboard', nameEn: '📊 Data & Dashboard' },
    { id: 'keamanan', name: '🔐 Keamanan & Privasi', nameEn: '🔐 Security & Privacy' },
    { id: 'pembayaran', name: '💳 Pembayaran & Langganan', nameEn: '💳 Payment & Subscription' },
    { id: 'fitur', name: '🤖 Fitur & Penggunaan', nameEn: '🤖 Features & Usage' },
    { id: 'tentang', name: '🚀 Tentang Tokcer AI', nameEn: '🚀 About Tokcer AI' }
  ];

  const faqData = {
    integrasi: [
      {
        q: 'Gimana cara connect toko online ku ke Tokcer AI?',
        qEn: 'How do I connect my online shop to Tokcer AI?',
        a: 'Gampang banget! Masuk ke tab Integrasi, pilih online shop lo, terus ikutin proses login oAuth-nya. Setelah connect, ada proses sinkronisasi awal dulu — biasanya butuh beberapa menit tergantung jumlah data toko lo. Begitu selesai, semua udah siap dipake!',
        aEn: 'Super easy! Go to the Integration tab, select your online shop, and follow the OAuth login process. Once connected, there will be an initial synchronization process — usually takes a few minutes depending on your shop\'s data size. Once done, everything is ready to use!'
      },
      {
        q: 'Platform apa aja yang bisa diintegrasiin ke Tokcer AI?',
        qEn: 'What platforms can be integrated into Tokcer AI?',
        a: 'Saat ini kita support TikTok Shop dan Shopee. Integrasi platform lain lagi on the way — stay tuned di update bulletin kita ya!',
        aEn: 'Currently, we support TikTok Shop and Shopee. Other platform integrations are on the way — stay tuned to our update bulletin!'
      }
    ],
    data: [
      {
        q: 'Kapan data omzet-ku diupdate?',
        qEn: 'When is my revenue data updated?',
        a: 'Real-time, bro! Setiap ada transaksi masuk dari platform, dashboard langsung reflect angkanya. Gak perlu refresh manual atau nunggu akhir hari.',
        aEn: 'Real-time, bro! Every time a transaction comes in from the platform, the dashboard reflects the numbers immediately. No need to manual refresh or wait until the end of the day.'
      },
      {
        q: 'Data saya hilang kalau ada masalah teknis gimana?',
        qEn: 'What if my data is lost due to technical issues?',
        a: 'Kita bedain dua kondisi ya:\n\n• Server down: Akses sementara terganggu, tapi begitu server balik normal, semua data lo tetap ada. Durasi downtime tergantung kondisi hosting — kita selalu update status-nya.\n• Data hilang: Tenang, kita punya sistem backup yang jalan rutin. Jadi data transaksi dan konten lo gak bakal ilang permanen.',
        aEn: 'Let\'s distinguish between two scenarios:\n\n• Server down: Temporary access disruption, but once the server is back to normal, all your data remains intact. Downtime duration depends on hosting conditions — we always update its status.\n• Data loss: Don\'t worry, we have a regular backup system. So your transaction data and content won\'t be permanently lost.'
      }
    ],
    keamanan: [
      {
        q: 'Aman gak sih data toko gue di Tokcer AI?',
        qEn: 'Is my shop\'s data safe with Tokcer AI?',
        a: 'Aman 100%. Kita pakai enkripsi high-level dan yang paling penting: password toko lo gak pernah kita simpan. Login pakai oAuth, jadi credentials lo tetap di tangan lo sendiri.',
        aEn: '100% safe. We use high-level encryption and most importantly: we never store your shop\'s password. Login uses OAuth, so your credentials remain entirely in your own hands.'
      },
      {
        q: 'Apakah data gue dibagi ke pihak ketiga?',
        qEn: 'Is my data shared with third parties?',
        a: 'Nope. Data lo strictly private — kita gak jual, gak share, gak ngapa-ngapain. Lo punya data lo sendiri, kita cuma bantu bacanya buat kepentingan bisnis lo.',
        aEn: 'Nope. Your data is strictly private — we don\'t sell, share, or do anything with it. You own your data, we just help you read it for your business interests.'
      }
    ],
    pembayaran: [
      {
        q: 'Metode pembayaran apa yang tersedia?',
        qEn: 'What payment methods are available?',
        a: 'Kita support:\n• Virtual Account: BSI, CIMB Niaga, BNI, BRI, Mandiri, Permata\n• QRIS: Gopay\n\nBayar dari mana aja, sesuka lo. Asal jangan ngutang dari pinjol yak.',
        aEn: 'We support:\n• Virtual Account: BSI, CIMB Niaga, BNI, BRI, Mandiri, Permata\n• QRIS: Gopay\n\nPay from anywhere you like. Just don\'t borrow from online loan sharks.'
      },
      {
        q: 'Gimana kalau mau upgrade plan?',
        qEn: 'How do I upgrade my plan?',
        a: 'Tinggal masuk ke Settings > Langganan, pilih plan yang lo mau, tinggal bayar aja. Akses baru langsung aktif begitu pembayaran confirmed.',
        aEn: 'Just go to Settings > Subscription, select the plan you want, and proceed with payment. The new access is activated immediately once the payment is confirmed.'
      },
      {
        q: 'Ada refund kalau gue gak cocok?',
        qEn: 'Is there a refund if it doesn\'t suit me?',
        a: 'Karena ini produk digital yang langsung aktif, tidak bisa refund.',
        aEn: 'Since this is a digital product that activates instantly, refunds are not available.'
      }
    ],
    fitur: [
      {
        q: 'Harus jago IT dulu buat pakai Tokcer AI?',
        qEn: 'Do I need to be tech-savvy to use Tokcer AI?',
        a: 'Sama sekali gak perlu! Tokcer AI didesain khusus buat seller yang gak mau ribet coding. Semua berbasis no-code — tinggal klik, isi, dan jalanin.',
        aEn: 'Not at all! Tokcer AI is specifically designed for sellers who don\'t want to deal with coding. Everything is no-code based — just click, fill, and run.'
      },
      {
        q: 'Kalau ada kendala teknis, bisa minta bantuan ke mana?',
        qEn: 'If there\'s a technical issue, where can I ask for help?',
        a: 'Klik Pusat Bantuan, scroll ke bawah sampe ketemu Bug Report. Nah lo ketik dah disitu mulai dari judul masalah, detail masalah, upload screenshot masalah (opsional), trus klik Kirim Laporan.',
        aEn: 'Click Help Center, scroll down to Bug Report. Type in your issue title, details, upload a screenshot (optional), and click Send Report.'
      },
      {
        q: 'Kalau ada inputan atau saran, bisa info kemana?',
        qEn: 'If I have feedback or suggestions, where do I send them?',
        a: 'Lo udah klik Pusat Bantuan? Nah kalo udah, scroll sampe Bawah trus tengok kanan ada tulisan Masukkan Fitur kan? Input disitu yak, jangan lupa klik Kirim Laporan.',
        aEn: 'Have you clicked the Help Center? If so, scroll to the bottom and look at the bottom right for "Feature Request". Input it there, and don\'t forget to click Send Report.'
      },
      {
        q: 'Satu akun bisa dipake bareng tim gak?',
        qEn: 'Can one account be shared with a team?',
        a: 'Untuk sekarang, satu akun = satu pengguna. Sharing akun bisa ganggu performa sistem karena Tokcer AI nyesuain output berdasarkan pola toko lo.',
        aEn: 'For now, one account = one user. Account sharing can affect system performance because Tokcer AI tailors output based on your specific shop\'s patterns.'
      }
    ],
    tentang: [
      {
        q: 'Bedanya Tokcer AI sama tools AI biasa apa?',
        qEn: 'What is the difference between Tokcer AI and regular AI tools?',
        a: 'Tools AI biasa kasih jawaban generic. Tokcer AI dirancang spesifik buat seller online Indonesia — dari generate caption produk, konsultasi strategi toko, sampai automasi laporan omzet. Dari Prompt ke Profit, bukan dari prompt ke bingung.',
        aEn: 'Regular AI tools give generic answers. Tokcer AI is designed specifically for Indonesian online sellers — from generating product captions, shop strategy consulting, to revenue report automation. From Prompt to Profit, not from prompt to confusion.'
      },
      {
        q: 'Tokcer AI cocok buat seller skala apa?',
        qEn: 'What seller scale is Tokcer AI suitable for?',
        a: 'Dari yang baru mulai jualan online sampai yang udah punya tim.',
        aEn: 'From those just starting to sell online to those who already have a team.'
      }
    ]
  };

  const handleToggle = (index) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  const currentCategoryKey = categories[activeCategory].id;
  const currentFaqs = faqData[currentCategoryKey] || [];

  // Reset opened accordion on category change
  const handleCategoryChange = (index) => {
    setActiveCategory(index);
    setOpenIndex(null);
  };

  const isEn = lang === 'en';

  return (
    <section id="faq" className="max-w-7xl mx-auto px-6 py-16 md:py-24 relative">
      <div className="text-center mb-12 md:mb-16">
        <h2 className="text-3xl md:text-4xl font-semibold text-white tracking-tighter">
          {isEn ? 'Frequently Asked Questions' : 'Pertanyaan yang Sering Diajukan'}
        </h2>
        <p className="text-zinc-400 mt-4 text-base font-normal">
          {isEn ? 'Find answers to all your questions about Tokcer AI here.' : 'Temukan jawaban lengkap tentang fitur, integrasi, keamanan, dan kuota Tokcer AI.'}
        </p>
      </div>

      <div className="flex flex-col md:flex-row gap-8 items-start">
        {/* Left Column: Category Navigation Pills */}
        <div className="w-full md:w-1/3 flex md:flex-col gap-2 overflow-x-auto md:overflow-x-visible pb-4 md:pb-0 scrollbar-none shrink-0">
          {categories.map((cat, idx) => (
            <button
              key={cat.id}
              onClick={() => handleCategoryChange(idx)}
              className={`px-4 py-3 rounded-xl text-sm font-medium transition-all duration-300 text-left whitespace-nowrap border shrink-0 ${
                activeCategory === idx
                  ? 'bg-orange-500/10 border-orange-500 text-orange-400 shadow-md shadow-orange-500/5'
                  : 'bg-zinc-950/40 border-zinc-800/80 text-zinc-400 hover:text-white hover:border-zinc-700'
              }`}
            >
              {isEn ? cat.nameEn : cat.name}
            </button>
          ))}
        </div>

        {/* Right Column: Accordions for Current Category */}
        <div className="w-full md:w-2/3 flex flex-col gap-3">
          {currentFaqs.map((faq, idx) => {
            const isOpen = openIndex === idx;
            return (
              <div
                key={idx}
                className={`bg-zinc-900/50 border rounded-2xl overflow-hidden transition-all duration-300 ${
                  isOpen ? 'border-orange-500/40 shadow-sm shadow-orange-500/5 bg-zinc-900/80' : 'border-zinc-800/80 hover:border-zinc-700/80'
                }`}
              >
                {/* Accordion Header / Button */}
                <button
                  onClick={() => handleToggle(idx)}
                  className="w-full flex justify-between items-center px-6 py-5 text-left transition-colors duration-200"
                >
                  <span className="text-base font-medium text-white pr-4">
                    {isEn ? faq.qEn : faq.q}
                  </span>
                  <span
                    className={`text-xl font-light shrink-0 transition-transform duration-300 text-zinc-400 flex items-center justify-center w-6 h-6 rounded-full border border-zinc-800 ${
                      isOpen ? 'rotate-45 text-orange-400 border-orange-500/30 bg-orange-500/5' : ''
                    }`}
                  >
                    ＋
                  </span>
                </button>

                {/* Accordion Body */}
                <div
                  className={`transition-all duration-300 ease-in-out ${
                    isOpen ? 'max-h-[500px] border-t border-zinc-800/60 opacity-100' : 'max-h-0 opacity-0 pointer-events-none'
                  }`}
                >
                  <p className="px-6 py-5 text-sm text-zinc-400 leading-relaxed whitespace-pre-line">
                    {isEn ? faq.aEn : faq.a}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default Faq;
