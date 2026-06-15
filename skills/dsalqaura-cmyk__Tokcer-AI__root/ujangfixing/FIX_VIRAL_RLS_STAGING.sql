-- =========================================================================
-- TOKCER AI: FIX ROW LEVEL SECURITY (RLS) FOR VIRAL AUTO-PILOT SYSTEM
-- TARGET: Supabase Staging Database Schema
-- RUN THIS IN: Supabase SQL Editor (Staging Project)
-- =========================================================================

-- 1. Nonaktifkan RLS untuk kedua tabel agar frontend & script autopilot bebas mengaksesnya (Rp 0,-)
ALTER TABLE public.viral_templates DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.upload_queue DISABLE ROW LEVEL SECURITY;

-- 2. Bersihkan dan isi kembali 10 tips harian UMKM premium secara bersih
TRUNCATE TABLE public.viral_templates;

INSERT INTO public.viral_templates (tips_title, tips_content, visual_prompt) VALUES
-- Tips 1: HPP Kalkulator
('Trik Rahasia Hitung HPP', 
 'Sobat Tokcer! Banyak penjual online bangkrut bukan karena gak laku, tapi karena salah hitung HPP. Ingat, HPP itu bukan cuma modal beli barang! Masukkan biaya lakban, dus packing, ongkir inbound, dan admin marketplace. Hitung detail pakai Tokcer AI biar gak boncos!', 
 'An aesthetic close up photo of a modern calculator on an office desk next to online store packaging boxes, warm cinematic lighting'),

-- Tips 2: Diskon Bertingkat
('Jangan Kasih Diskon Flat', 
 'Juragan online, stop kasih diskon lima puluh persen langsung di toko! Itu merusak harga pasar. Coba ganti ke diskon bertingkat: beli satu harga normal, beli dua diskon tiga puluh persen untuk barang kedua. Ini bikin nilai transaksi keranjang pembeli naik dua kali lipat!', 
 'A clean shot of dynamic colorful sale tag banners on a modern product showcase shelf, realistic photography'),

-- Tips 3: Mengatasi COD Gagal
('Toko Boncos Karena COD Gagal?', 
 'Rugi bandar karena paket COD sering ditolak pembeli? Lakukan trik ini: selalu kirim WhatsApp konfirmasi alamat tiga puluh menit sebelum paket dikirim. Pembeli nakal akan ciut nyali dan langsung membatalkan pesanan sebelum kita buang-buang ongkos kirim!', 
 'A realistic shot of parcel delivery boxes stacked in a rustic shipping warehouse with sunset light coming through the window'),

-- Tips 4: Rating Bintang 5
('Trik Rating Bintang Lima', 
 'Mau produk kamu cepat naik di halaman utama Shopee? Selipkan Thank You Card di dalam paket, tapi jangan cuma bilang terima kasih. Berikan kata-kata: Jika juragan puas, tolong bantu doakan toko kami laris manis ya. Sentuhan emosional ini terbukti meningkatkan rating bintang lima secara instan!', 
 'A beautiful macro photo of an elegant floral thank you card lying on top of wrapped wrapping paper package, soft focus'),

-- Tips 5: Bundling Paket Usaha
('Naikkan Omzet dengan Bundling', 
 'Jangan cuma jualan barang eceran! Buatlah paket bundling, misalnya: paket pembersih sepatu lengkap dengan sikat dan handuk microfiber. Menjual solusi lengkap jauh lebih dihargai pembeli dan margin keuntungan kamu bisa naik hingga tiga puluh persen!', 
 'A clean commercial product photography of a modern shoe cleaning kit package organized beautifully on a white studio background'),

-- Tips 6: Jam Emas Posting Konten
('Jam Emas Posting Konten', 
 'Video jualan kamu sepi penonton? Stop posting sembarangan! Waktu emas audiens Indonesia itu ada di jam dua belas siang saat istirahat makan, dan jam tujuh malam saat bersantai di rumah. Posting di luar jam ini cuma bikin kuota internet kamu terbuang sia-sia!', 
 'A minimal aesthetic shot of a modern smartphone showing social media statistics graphs on a glowing screen, dark ambient lighting'),

-- Tips 7: SEO Marketplace
('Trik Nangkring di Halaman Satu', 
 'Mau produk kamu dicari langsung ketemu? Gunakan trik SEO! Jangan cuma kasih judul Kemeja Pria. Ganti dengan judul: Kemeja Pria Lengan Panjang Katun Premium Anti Kusut. Masukkan kata kunci yang paling sering diketik orang di kolom pencarian agar tokomu kebanjiran pembeli!', 
 'A clean shot of a laptop screen showing e-commerce search results page, glowing screen, professional office background'),

-- Tips 8: Psikologi Angka 99
('Misteri Angka Sembilan Puluh Sembilan', 
 'Kenapa produk harga sembilan puluh sembilan ribu jauh lebih laris manis dibanding harga seratus ribu? Secara psikologis, otak manusia membaca digit kiri terlebih dahulu. Penurunan seribu perak memberikan ilusi bahwa barang tersebut jauh lebih murah secara instan!', 
 'A creative shot of a sleek price tag with 99k written on it, hanging from a premium clothing hanger, cinematic studio light'),

-- Tips 9: Jangan Kosongkan Stok
('Bahaya Stok Nol di Shopee', 
 'Sobat UMKM, jangan pernah membiarkan stok produk kamu tertulis nol di Shopee lebih dari dua puluh empat jam! Algoritma pencarian akan langsung menurunkan peringkat tokomu ke dasar klasemen. Jika barang habis, set stok minimal lima dan set sistem pre-order agar tokomu tetap aman!', 
 'A high-quality photo of empty store shelves in a modern boutique with soft golden backlighting, clean commercial style'),

-- Tips 10: Solusi Stok Mati (Dead Stock)
('Cara Bersihkan Stok Mati', 
 'Gudang penuh karena barang tidak laku? Jangan diskon rugi! Jadikan barang tersebut sebagai bonus hadiah cuma-cuma untuk pembelian produk terlaris kamu dengan minimal belanja tertentu. Pembeli senang dapat hadiah gratis, dan gudang kamu langsung bersih seketika!', 
 'A well-organized modern retail warehouse with cardboard boxes neatly arranged on wooden pallets, bright clean industrial photography');

-- 3. Refresh schema cache agar terbaca instan di frontend dashboard
NOTIFY pgrst, 'reload schema';
