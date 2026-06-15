import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../lib/supabase.js';
import { callAiEngine } from '../utils/ai.js';
import ProductModal from '../components/modals/ProductModal.jsx';
import logo from '../assets/logo.png';
import Sidebar from '../components/dashboard/Sidebar.jsx';
import Header from '../components/dashboard/Header.jsx';
import OverviewTab from '../components/dashboard/tabs/OverviewTab.jsx';
import RevenueTab from '../components/dashboard/tabs/RevenueTab.jsx';
import InventoryTab from '../components/dashboard/tabs/InventoryTab.jsx';
import AnalyticsTab from '../components/dashboard/tabs/AnalyticsTab.jsx';
import AiGeneratorTab from '../components/dashboard/tabs/AiGeneratorTab.jsx';
import HealthScoreTab from '../components/dashboard/tabs/HealthScoreTab.jsx';
import AccountTab from '../components/dashboard/tabs/AccountTab.jsx';
import BillingTab from '../components/dashboard/tabs/BillingTab.jsx';
import SupportTab from '../components/dashboard/tabs/SupportTab.jsx';
import MarketIntelTab from '../components/dashboard/tabs/MarketIntelTab.jsx';
import MarketplaceSyncTab from '../components/dashboard/tabs/MarketplaceSyncTab.jsx';
import AdminTab from '../components/dashboard/tabs/AdminTab.jsx';
import { dashboardTranslations } from '../locales/dashboardLocales.js';
import { getShopeeAuthUrl } from '../utils/shopee.js';
import { getTikTokAuthUrl } from '../utils/tiktok.js';
import { getRealMarketIntel } from '../services/marketIntelService.js';


const Dashboard = () => {
  const autoConnectingRef = useRef(false);
  const [activeMenu, setActiveMenu] = useState('tab-dash');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [lang, setLang] = useState(localStorage.getItem('tokcer_lang') || 'id');
  const [user, setUser] = useState(() => {
    try {
        const cached = sessionStorage.getItem('tokcer_cached_user');
        return cached ? JSON.parse(cached) : null;
    } catch { return null; }
  });
  const [profile, setProfile] = useState(() => {
    try {
        const cached = sessionStorage.getItem('tokcer_cached_profile');
        return cached ? JSON.parse(cached) : null;
    } catch { return null; }
  });
  const [isSyncingStore, setIsSyncingStore] = useState(false);
  const [aiSubTab, setAiSubTab] = useState('content');
  const [aiPrompt, setAiPrompt] = useState('');
  const [aiFormat, setAiFormat] = useState(() => {
    try {
      const cached = sessionStorage.getItem('tokcer_cached_profile');
      if (cached) {
        const prof = JSON.parse(cached);
        if ((prof?.subscription_plan || 'starter').toLowerCase() === 'starter') {
          return 'Shopee Description';
        }
      }
    } catch {}
    return 'TikTok Video';
  });
  const [isGenerating, setIsGenerating] = useState(false);
  const [aiResult, setAiResult] = useState('');
  const [trendPrompt, setTrendPrompt] = useState('');
  const [isTrendAnalyzing, setIsTrendAnalyzing] = useState(false);
  const [trendResult, setTrendResult] = useState('');
  const [showProductModal, setShowProductModal] = useState(false);
  const [timeFilter, setTimeFilter] = useState('Hari Ini');
  const [showFilterDropdown, setShowFilterDropdown] = useState(false);
  const [platformFilter, setPlatformFilter] = useState('all');
  const [showPlatformDropdown, setShowPlatformDropdown] = useState(false);
  const [omzetTimeFilter, setOmzetTimeFilter] = useState('Hari Ini');
  const [showOmzetTimeDropdown, setShowOmzetTimeDropdown] = useState(false);
  const [healthPlatform, setHealthPlatform] = useState('all');
  const [trendSampleKey, setTrendSampleKey] = useState(null);
  const [trendCustomInput, setTrendCustomInput] = useState('');
  const [trendCustomResult, setTrendCustomResult] = useState(null);
  const [isSearchingTrend, setIsSearchingTrend] = useState(false);
  const [analyticsPlatform, setAnalyticsPlatform] = useState('all');
  const [showAnalyticsPlatformDropdown, setShowAnalyticsPlatformDropdown] = useState(false);

  // Support Center States
  const [supportType, setSupportType] = useState('bug'); // 'bug' or 'feature'
  const [supportTitle, setSupportTitle] = useState('');
  const [supportDesc, setSupportDesc] = useState('');
  const [supportFile, setSupportFile] = useState(null);
  const [supportFilePreview, setSupportFilePreview] = useState(null);
  const [isSubmittingSupport, setIsSubmittingSupport] = useState(false);
  const [supportSubmitted, setSupportSubmitted] = useState(false);
  const [userTickets, setUserTickets] = useState([]);
  const [isFetchingUserTickets, setIsFetchingUserTickets] = useState(false);
  
  // Account Security States
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isUpdatingPassword, setIsUpdatingPassword] = useState(false);
  const [securityMessage, setSecurityMessage] = useState({ type: '', text: '' });

  // Market Intel Dynamic States
  const [viralTopics, setViralTopics] = useState([]);
  const [liveSummary, setLiveSummary] = useState(null);
  const [bestsellerProducts, setBestsellerProducts] = useState([]);
  const [viralVideos, setViralVideos] = useState([]);
  const [liveStreams, setLiveStreams] = useState([]);
  const [isFetchingTrends, setIsFetchingTrends] = useState(false);

  // Operational States (Inventory & Orders)
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [isFetchingOperational, setIsFetchingOperational] = useState(false);

  // Analytics Insight States
  const [analyticsInsight, setAnalyticsInsight] = useState(null);
  const [isAnalyzingAnalytics, setIsAnalyzingAnalytics] = useState(false);

  // Health Insight States
  const [healthInsight, setHealthInsight] = useState(null);
  const [isAnalyzingHealth, setIsAnalyzingHealth] = useState(false);
  const [marketplaceConnections, setMarketplaceConnections] = useState([]);

  // System Briefing States
  const [systemBriefing, setSystemBriefing] = useState(null);
  const [clientData, setClientData] = useState(() => {
    try {
        const cached = sessionStorage.getItem('tokcer_cached_client_data');
        return cached ? JSON.parse(cached) : null;
    } catch { return null; }
  });
  const [isFetchingBriefing, setIsFetchingBriefing] = useState(false);

  const t = (key) => dashboardTranslations[lang][key] || key;
  const navigate = useNavigate();

    const checkStoreLimit = async () => {
        if (!user) return false;
        const plan = (profile?.subscription_plan || 'starter').toLowerCase();
        const limits = { 'starter': 1, 'pro': 3, 'elite': 10, 'ultimate': 30 };
        const limit = limits[plan] || 1;

        const { count, error } = await supabase
            .from('marketplace_connections')
            .select('*', { count: 'exact', head: true })
            .eq('user_id', user.id);

        if (error) {
            console.error("Store count error:", error);
            return false;
        }

        if (count >= limit && plan !== 'ultimate') {
            alert(`⚠️ Batas maksimal toko untuk paket ${plan.toUpperCase()} adalah ${limit} toko. Silakan upgrade paket Anda untuk menambah lebih banyak!`);
            return false;
        }
        return true;
    };

    const autoConnectStores = async (userId, platforms, links) => {
        if (autoConnectingRef.current) return;
        autoConnectingRef.current = true;
        try {
            const { data: existing } = await supabase
                .from('marketplace_connections')
                .select('id')
                .eq('user_id', userId);
            
            if (existing && existing.length > 0) return;

            const plan = (profile?.subscription_plan || 'starter').toLowerCase();
            const limits = { 'starter': 1, 'pro': 3, 'elite': 10, 'ultimate': 30 };
            const limit = limits[plan] || 1;

            // Only take stores up to limit
            const allowedPlatforms = platforms.slice(0, limit);

            const connections = allowedPlatforms.map(plat => ({
                user_id: userId,
                platform: plat.toLowerCase(),
                shop_name: plat + " Store",
                shop_id: links[plat] || 'pending',
                sync_status: 'idle'
            }));

            if (connections.length > 0) {
                await supabase.from('marketplace_connections').insert(connections);
            }
        } catch (err) {
            console.error("AutoConnect Error:", err);
        }
    };

    const handleConnectShopee = async () => {
        const canAdd = await checkStoreLimit();
        if (!canAdd) return;
        try {
            // 1. Fetch Shopee Config from Supabase
            const { data: configs } = await supabase
                .from('ai_configs')
                .select('*')
                .in('key', ['shopee_partner_id', 'shopee_partner_key']);
            
            const configMap = {};
            configs?.forEach(c => configMap[c.key] = c.value);

            if (!configMap.shopee_partner_id || !configMap.shopee_partner_key) {
                alert("⚠️ Konfigurasi API Shopee belum lengkap di Dashboard Internal. Hubungi Admin.");
                return;
            }

            // 2. Build Redirect URL (Current Page)
            const redirectUrl = window.location.origin + window.location.pathname;
            
            // 3. Get Shopee Auth Link
            const authUrl = await getShopeeAuthUrl(
                configMap.shopee_partner_id, 
                configMap.shopee_partner_key, 
                redirectUrl
            );

            // 4. Redirect
            window.location.href = authUrl;
        } catch (err) {
            console.error("Shopee Auth Error:", err);
            alert("Gagal menghubungi server Shopee: " + err.message);
        }
    };

    const handleConnectTikTok = async () => {
        try {
            // 1. Cek Limit (Skip untuk Admin)
            if (user?.email !== 'admin@tokcer-ai.com') {
                const canAdd = await checkStoreLimit();
                if (!canAdd) {
                    alert(`Batas toko untuk paket ${profile?.subscription_plan || 'Starter'} telah tercapai.`);
                    return;
                }
            }

            // 2. Ambil Config TikTok dari Database
            const { data: configs, error: configError } = await supabase
                .from('ai_configs')
                .select('key, value')
                .in('key', ['tiktok_app_id', 'tiktok_service_id']);

            if (configError) {
                console.warn("DB Config Error, using fallback...");
            }

            let appId = import.meta.env.VITE_TIKTOK_APP_ID;
            let serviceId = null;

            if (configs) {
                const appConfig = configs.find(c => c.key === 'tiktok_app_id');
                const serviceConfig = configs.find(c => c.key === 'tiktok_service_id');
                if (appConfig) appId = appConfig.value;
                if (serviceConfig) serviceId = serviceConfig.value;
            }
            
            // TikTok Oauth memerlukan Service ID, bukan App Key. 
            // Jika Service ID tidak ada, kita fallback menggunakan App Key dengan asumsi struktur URL beda
            const finalIdForAuth = serviceId || appId;

            if (!finalIdForAuth) {
                alert("⚠️ App ID atau Service ID TikTok belum dikonfigurasi. Mohon isi di menu Admin.");
                return;
            }

            // 3. Redirect langsung ke Halaman Otorisasi Resmi TikTok Shop (Production-Ready)
            window.location.href = getTikTokAuthUrl(finalIdForAuth);
        } catch (err) {
            console.error("TikTok Auth Error:", err);
            // Jika database error, gunakan fallback dari .env agar tidak mati total
            const fallbackId = import.meta.env.VITE_TIKTOK_APP_ID;
            if (fallbackId) {
                window.location.href = getTikTokAuthUrl(fallbackId);
            } else {
                alert("Gagal menghubungi server: " + err.message);
            }
        }
    };

    const handleSyncStore = async () => {
        if (!user) return;
        setIsSyncingStore(true);
        try {
            const { data, error } = await supabase.functions.invoke('sync-marketplace', {
                body: { user_id: user.id }
            });
            if (error) throw error;
            if (data?.success === false) {
                alert("Gagal Sinkronisasi: " + data.error);
            } else {
                alert(data?.message || "Sinkronisasi berhasil!");
                // Muat ulang data visual pesanan & produk secara real-time
                await fetchOperationalData(user.id, user);
            }
        } catch (err) {
            console.error("Sync Store Error:", err);
            alert("Gagal sinkronisasi: " + err.message);
        } finally {
            setIsSyncingStore(false);
        }
    };

    const fetchMarketplaceConnections = async (userId) => {
        if (!userId) return;
        const { data, error } = await supabase
            .from('marketplace_connections')
            .select('*')
            .eq('user_id', userId);
        if (!error && data) {
            setMarketplaceConnections(data);
        }
    };

    const fetchOperationalData = async (userId, currentUser) => {
        if (!userId) return;
        setIsFetchingOperational(true);
        try {
            let prodQuery = supabase.from('products').select('*').order('created_at', { ascending: false });
            let ordQuery = supabase.from('orders').select('*').order('order_date', { ascending: false });

            const isAdmin = userId === 'admin-bypass';

            if (!isAdmin) {
                prodQuery = prodQuery.eq('user_id', userId);
                ordQuery = ordQuery.eq('user_id', userId);
            }

            const { data: prodData, error: prodError } = await prodQuery;
            if (prodError) {
                console.error("Products Table Error:", prodError.message);
                setProducts([]);
            } else if (prodData) {
                setProducts(prodData);
            }

            const { data: ordData, error: ordError } = await ordQuery;
            if (ordError) {
                console.error("Orders Table Error:", ordError.message);
                setOrders([]);
            } else if (ordData) {
                setOrders(ordData);
            }
            return { products: prodData, orders: ordData };
        } catch (err) {
            console.error("Fetch Operational Error:", err);
            return { products: [], orders: [] };
        } finally {
            setIsFetchingOperational(false);
        }
    };

    const handleImportOrders = async (data) => {
        if (!user || data.length === 0) return;
        setIsFetchingOperational(true);
        try {
            // Helper to find value regardless of header case/spaces
            const getValue = (obj, possibleKeys) => {
                const keys = Object.keys(obj);
                for (const pk of possibleKeys) {
                    const foundKey = keys.find(k => k.toLowerCase().replace(/[\s_]/g, '') === pk.toLowerCase().replace(/[\s_]/g, ''));
                    if (foundKey) return obj[foundKey];
                }
                return null;
            };

            const formattedData = data.map(item => ({
                user_id: user.id === 'admin-bypass' ? null : user.id,
                order_number: getValue(item, ['order_number', 'orderno', 'idpesanan', 'no_pesanan']),
                customer_name: getValue(item, ['customer_name', 'customer', 'namapelanggan']),
                platform: getValue(item, ['platform', 'marketplace', 'sumber']),
                total_amount: Number(getValue(item, ['total_amount', 'total', 'nominal', 'harga']) || 0),
                status: getValue(item, ['status', 'order_status']) || 'completed',
                order_date: getValue(item, ['order_date', 'tanggal', 'date']) || new Date().toISOString()
            }));

            const { error } = await supabase.from('orders').insert(formattedData);
            if (error) throw error;
            
            alert(`✅ Berhasil mengimpor ${data.length} transaksi!`);
            fetchOperationalData(user.id);
        } catch (err) {
            console.error("Import Error:", err);
            alert(`❌ Gagal impor: ${err.message || "Pastikan format CSV sesuai template"}`);
        } finally {
            setIsFetchingOperational(false);
        }
    };

    const handleImportProducts = async (data) => {
        if (!user || data.length === 0) return;
        setIsFetchingOperational(true);
        try {
            const getValue = (obj, possibleKeys) => {
                const keys = Object.keys(obj);
                for (const pk of possibleKeys) {
                    const foundKey = keys.find(k => k.toLowerCase().replace(/[\s_]/g, '') === pk.toLowerCase().replace(/[\s_]/g, ''));
                    if (foundKey) return obj[foundKey];
                }
                return null;
            };

            const formattedData = data.map(item => ({
                user_id: user.id === 'admin-bypass' ? null : user.id,
                name: getValue(item, ['name', 'product_name', 'namaproduk']),
                sku: getValue(item, ['sku', 'kodeproduk']),
                stock: Number(getValue(item, ['stock', 'stok', 'jumlah']) || 0),
                price: Number(getValue(item, ['price', 'harga', 'hargajual']) || 0),
                cost: Number(getValue(item, ['cost', 'modal', 'hargabeli']) || 0),
                description: getValue(item, ['description', 'deskripsi']) || ''
            }));

            const { error } = await supabase.from('products').insert(formattedData);
            if (error) throw error;
            
            alert(`✅ Berhasil mengimpor ${data.length} produk ke katalog!`);
            fetchOperationalData(user.id);
        } catch (err) {
            console.error("Import Error:", err);
            alert(`❌ Gagal impor produk: ${err.message}`);
        } finally {
            setIsFetchingOperational(false);
        }
    };

    const fetchAnalyticsInsight = async () => {
        if (!user || isAnalyzingAnalytics) return;
        
        // Safety check for Plan Permission
        if (!checkPlanPermission('analytics')) return;

        const today = new Date().toISOString().split('T')[0];
        const cacheKey = `tokcer_cache_analytics_${user.id}_${today}`;
        const cachedData = localStorage.getItem(cacheKey);

        if (cachedData) {
            setAnalyticsInsight(JSON.parse(cachedData));
            return;
        }

        // Starter: tampilkan data statis, tidak hit AI
        const plan = (profile?.subscription_plan || 'starter').toLowerCase();
        if (plan === 'starter') {
            const staticInsight = {
                ads_opt: { golden_hours: "19:00 - 21:00", strategy: "Upgrade ke Pro untuk mendapatkan rekomendasi iklan yang dipersonalisasi berdasarkan data toko Anda." },
                bundling: [{ title: "Paket Produk", desc: "Upgrade ke Pro untuk rekomendasi bundling produk berbasis AI sesuai tren pasar." }],
                market_pulse: { hot_idea: "Upgrade ke Pro", hot_desc: "Dapatkan analisis tren pasar real-time yang dipersonalisasi untuk niche toko Anda.", content_tip: "AI Content Tips", content_desc: "Pro plan memberikan saran konten berbasis performa toko Anda." },
                pricing: { potential_profit: "-", tip: "Upgrade ke Pro untuk rekomendasi harga optimal berbasis kompetitor.", margin_increase: "-" }
            };
            setAnalyticsInsight(staticInsight);
            localStorage.setItem(cacheKey, JSON.stringify(staticInsight));
            return;
        }

        setIsAnalyzingAnalytics(true);
        try {
            const bizType = profile?.business_type || 'E-commerce';
            const safeProducts = Array.isArray(products) ? products : [];
            const safeOrders = Array.isArray(orders) ? orders : [];
            const productNames = safeProducts.slice(0, 10).map(p => p.name).join(', ');
            const recentOrdersCount = safeOrders.length;
            const targetLang = lang === 'id' ? 'Bahasa Indonesia' : 'English';
            
            const systemPrompt = `You are a Senior E-commerce Growth Strategist for Tokcer AI. 
            Analyze the user's business (${bizType}) and their products: [${productNames}]. 
            Respond strictly in ${targetLang}.
            STRICTLY focus only on the user's specific niche and products. 
            DO NOT mention irrelevant global news (like fuel prices, politics, or unrelated commodities) unless they directly impact the ${bizType} industry's logistics or costs.
            Provide actionable strategy in JSON format.
            Analyze seasonal trends in Indonesia for this specific niche, competitor behavior, and identify gap opportunities.
            Keys: 
            "ads_opt": { "golden_hours": string, "strategy": string },
            "bundling": [ { "title": string, "desc": string } ],
            "market_pulse": { "hot_idea": string, "hot_desc": string, "content_tip": string, "content_desc": string },
            "pricing": { "potential_profit": string, "tip": string, "margin_increase": string }`;

            const userPrompt = `Generate analytics insight for my shop selling ${bizType}. I have ${recentOrdersCount} recent orders and these products: ${productNames}.`;
            
            const result = await callAiEngine(systemPrompt, userPrompt, 2048, 0.5);
            const cleanJson = result.text.replace(/```json|```/g, '').trim();
            const data = JSON.parse(cleanJson);
            setAnalyticsInsight(data);
            localStorage.setItem(cacheKey, JSON.stringify(data));
            // Log usage
            await supabase.from('ai_usage_logs').insert([{
                user_id: user?.id || null, feature: 'daily_access_analytics',
                input_tokens: result.usage?.prompt_tokens || 0,
                output_tokens: result.usage?.completion_tokens || 0,
                tokens_used: 1
            }]);
        } catch (err) {
            console.error("Analytics Analysis Error:", err);
            // Fallback empty data and STILL CACHE IT to prevent immediate retry loop
            const fallback = {
                ads_opt: { golden_hours: "19:00 - 21:00", strategy: "Gunakan data historis untuk optimasi iklan." },
                bundling: [{ title: "Paket Rekomendasi", desc: "Bundling produk pelengkap." }],
                market_pulse: { hot_idea: "Peningkatan Visual", hot_desc: "Perbaiki foto produk.", content_tip: "Video Review", content_desc: "Gunakan user-generated content." },
                pricing: { potential_profit: "Rp 0", tip: "Pantau harga pasar.", margin_increase: "0%" }
            };
            setAnalyticsInsight(fallback);
            localStorage.setItem(cacheKey, JSON.stringify(fallback));
        } finally {
            setIsAnalyzingAnalytics(false);
        }
    };

    const fetchHealthInsight = async (metrics) => {
        if (!user || isAnalyzingHealth) return;
        
        // Safety check for Plan Permission
        if (!checkPlanPermission('health_check')) return;

        const today = new Date().toISOString().split('T')[0];
        const cacheKey = `tokcer_cache_health_${user.id}_${today}`;
        const cachedData = localStorage.getItem(cacheKey);

        if (cachedData) {
            setHealthInsight(JSON.parse(cachedData));
            return;
        }

        setIsAnalyzingHealth(true);
        try {
            const systemPrompt = `You are an E-commerce Operational Expert. 
            Analyze these shop metrics: Chat Response: ${metrics.chat}, Shipping: ${metrics.ship}, Returns: ${metrics.return}, Rating: ${metrics.rating}. 
            Respond strictly in ${lang === 'id' ? 'Bahasa Indonesia' : 'English'}.
            Provide 2 specific, actionable improvement recommendations in JSON format.
            Keys: "recommendations" (array of strings).`;

            const userPrompt = `Provide health recommendations for my shop based on current metrics.`;
            
            const result = await callAiEngine(systemPrompt, userPrompt, 2048, 0.5);
            const cleanJson = result.text.replace(/```json|```/g, '').trim();
            const data = JSON.parse(cleanJson);
            const recommendations = data.recommendations || [];
            setHealthInsight(recommendations);
            localStorage.setItem(cacheKey, JSON.stringify(recommendations));
            // Log usage
            await supabase.from('ai_usage_logs').insert([{
                user_id: user?.id || null, feature: 'daily_access_health_check',
                input_tokens: result.usage?.prompt_tokens || 0,
                output_tokens: result.usage?.completion_tokens || 0,
                tokens_used: 1
            }]);
        } catch (err) {
            console.error("Health Analysis Error:", err);
            const fallback = [
                lang === 'id' ? "Pertahankan performa chat Anda yang sudah baik." : "Maintain your excellent chat performance.",
                lang === 'id' ? "Coba percepat waktu pengemasan di akhir pekan." : "Try to speed up packing time during weekends."
            ];
            setHealthInsight(fallback);
            localStorage.setItem(cacheKey, JSON.stringify(fallback));
        } finally {
            setIsAnalyzingHealth(false);
        }
    };
    
    const fetchSystemBriefing = async (currentProducts, currentOrders, currentUser) => {
        const prodData = currentProducts || products;
        const ordData = currentOrders || orders;
        const activeUser = currentUser || user;
        
        if (!activeUser || isFetchingBriefing) return;

        // Starter plan: pakai briefing statis, tidak hit AI
        const plan = (profile?.subscription_plan || 'starter').toLowerCase();
        if (!['pro', 'elite', 'ultimate', 'demo'].includes(plan)) {
            setSystemBriefing([
                { title: "Selamat Datang di Tokcer AI", desc: "Upgrade ke Pro untuk mendapatkan AI Briefing harian yang dipersonalisasi untuk toko Anda.", type: "info", time: "Baru saja" },
                { title: "Tips Hari Ini", desc: "Gunakan fitur AI Generator untuk membuat deskripsi produk yang menarik.", type: "success", time: "Baru saja" }
            ]);
            return;
        }

        const today = new Date().toISOString().split('T')[0];
        const cacheKey = `tokcer_cache_briefing_${activeUser.id}_${today}`;

        // Cek cache dulu — kalau sudah ada, langsung pakai tanpa hit AI
        const cachedData = localStorage.getItem(cacheKey);
        if (cachedData) {
            setSystemBriefing(JSON.parse(cachedData));
            return;
        }

        // In-memory lock: cegah double-call dalam sesi yang sama
        const lockKey = `tokcer_briefing_lock_${activeUser.id}`;
        if (sessionStorage.getItem(lockKey) === 'running') return;
        sessionStorage.setItem(lockKey, 'running');

        setIsFetchingBriefing(true);
        try {
            const bizType = profile?.business_type || 'E-commerce';
            const lowStockCount = prodData.filter(p => p.stock < 10).length;
            const highReturnOrders = ordData.filter(o => o.status === 'returned').length;
            
            const systemPrompt = `You are the Tokcer AI System Assistant. Analyze the shop data and provide 3 concise, professional, and actionable notifications in Indonesian.
            Format: JSON array of objects with keys: "title", "desc", "type" (warning, success, info), "time" (e.g. "Baru saja", "1 jam lalu").
            Focus on inventory, store health, or growth opportunities.`;
            
            const userPrompt = `Data: ${bizType} shop, ${lowStockCount} products low stock, ${highReturnOrders} returned orders, ${ordData.length} total orders.`;
            
            const result = await callAiEngine(systemPrompt, userPrompt, 512, 0.5);
            const cleanJson = result.text.replace(/```json|```/g, '').trim();
            const data = JSON.parse(cleanJson);
            
            setSystemBriefing(data);
            localStorage.setItem(cacheKey, JSON.stringify(data));
            // Log usage
            await supabase.from('ai_usage_logs').insert([{
                user_id: activeUser?.id || null, feature: 'daily_access_briefing',
                input_tokens: result.usage?.prompt_tokens || 0,
                output_tokens: result.usage?.completion_tokens || 0,
                tokens_used: 1
            }]);
        } catch (err) {
            console.error("Briefing Error:", err);
            const fallback = [
                { title: "Sistem Optimal", desc: "Seluruh integrasi toko Anda berjalan lancar hari ini.", type: "success", time: "Baru saja" },
                { title: "Tips Pertumbuhan", desc: "Gunakan Market Intel untuk mencari tren produk terbaru.", type: "info", time: "1 jam lalu" }
            ];
            setSystemBriefing(fallback);
            localStorage.setItem(cacheKey, JSON.stringify(fallback));
        } finally {
            setIsFetchingBriefing(false);
            // Release in-memory lock
            sessionStorage.removeItem(`tokcer_briefing_lock_${activeUser.id}`);
        }
    };

    const getUser = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      const isAdmin = localStorage.getItem('tokcer_admin_auth') === 'true';
      
      if (session) {
        setUser(session.user);
        sessionStorage.setItem('tokcer_cached_user', JSON.stringify(session.user));
        
        const { data: prof } = await supabase.from('profiles').select('*').eq('id', session.user.id).maybeSingle();
        const { data: clientData } = await supabase.from('clients').select('*').ilike('email', session.user.email?.toLowerCase().trim()).maybeSingle();
        setClientData(clientData);
        if (clientData) sessionStorage.setItem('tokcer_cached_client_data', JSON.stringify(clientData));
        
        if (session.user.email === 'admin@tokcer-ai.com') {
            localStorage.setItem('tokcer_admin_auth', 'true');
            const adminProfile = {
                id: session.user.id,
                email: session.user.email,
                full_name: 'Administrator',
                subscription_plan: 'ultimate',
                tokens: 9999,
                totalQuota: 3000,
                isUnlimited: true,
                planName: 'Ultimate'
            };
            setProfile(adminProfile);
            sessionStorage.setItem('tokcer_cached_profile', JSON.stringify(adminProfile));
            setTimeFilter('Semua');
            fetchOperationalData(session.user.id, session.user);
            fetchMarketplaceConnections(session.user.id);
            return;
        } else {
            localStorage.removeItem('tokcer_admin_auth');
        }

        if (prof || clientData) {
            const plan = (clientData?.plan || prof?.subscription_plan || 'starter').toLowerCase();
            const quotaMap = { 'demo': 30, 'starter': 50, 'pro': 300, 'elite': 1000, 'ultimate': 3000 };
            const totalQuota = quotaMap[plan] ?? 50;
            const activeTokens = prof?.ai_tokens ?? prof?.tokens ?? 0;
            
            const calculatedProfile = { 
                ...(prof || {}), 
                subscription_plan: plan,
                tokens: activeTokens, 
                totalQuota: totalQuota,
                isUnlimited: plan === 'ultimate',
                planName: plan.charAt(0).toUpperCase() + plan.slice(1)
            };
            setProfile(calculatedProfile);
            sessionStorage.setItem('tokcer_cached_profile', JSON.stringify(calculatedProfile));
        }
        // [TARJO FIX]: Nonaktifkan pembuatan draf toko otomatis agar default-nya bersih kosong tanpa toko
        // const metadata = session.user.user_metadata;
        // if (metadata?.platforms && metadata?.store_links) {
        //     await autoConnectStores(session.user.id, metadata.platforms, metadata.store_links);
        // }
        const { products: pData, orders: oData } = await fetchOperationalData(session.user.id, session.user);
        fetchMarketplaceConnections(session.user.id);
        // fetchSystemBriefing dipindah ke tab-overview trigger, bukan saat login

        // [AUTO-SYNC ON-MOUNT]: Silently sync latest store data in background on dashboard load
        supabase.functions.invoke('sync-marketplace', {
            body: { user_id: session.user.id }
        }).then(({ data }) => {
            if (data?.success) {
                fetchOperationalData(session.user.id, session.user);
                fetchMarketplaceConnections(session.user.id);
            }
        }).catch(err => console.warn("Background auto-sync warn:", err));

        // [C3 FIX]: Realtime listener untuk invalidasi cache saat plan berubah dari admin
        const profileChannel = supabase
          .channel(`profile_plan_watch_${session.user.id}`)
          .on('postgres_changes',
            { event: 'UPDATE', schema: 'public', table: 'profiles', filter: `id=eq.${session.user.id}` },
            (payload) => {
              const newPlan = payload.new?.subscription_plan;
              const cachedProfile = sessionStorage.getItem('tokcer_cached_profile');
              if (cachedProfile) {
                const parsed = JSON.parse(cachedProfile);
                if (parsed.subscription_plan !== newPlan) {
                  sessionStorage.removeItem('tokcer_cached_profile');
                  sessionStorage.removeItem('tokcer_cached_client_data');
                  getUser();
                }
              }
            }
          )
          .subscribe();

        // Cleanup channel saat component unmount
        return () => { supabase.removeChannel(profileChannel); };
      } else if (isAdmin) {
        const adminUser = { email: 'admin@tokcer-ai.com', id: 'admin-bypass' };
        setUser(adminUser);
        setProfile({ 
            id: 'admin-bypass',
            email: 'admin@tokcer-ai.com',
            full_name: 'Administrator', 
            tokens: 9999, 
            role: 'admin',
            subscription_plan: 'ultimate',
            planName: 'Ultimate',
            totalQuota: 3000,
            isUnlimited: true
        });
        setTimeFilter('Semua');
        fetchOperationalData('admin-bypass', adminUser);
        fetchMarketplaceConnections('admin-bypass');
        // fetchSystemBriefing untuk admin juga dipanggil via tab-overview
      }

      const params = new URLSearchParams(window.location.search);
      const code = params.get('code');
      const shopId = params.get('shop_id');
      if (code && shopId) {
          window.history.replaceState({}, document.title, window.location.pathname);
      }
      const tiktokCode = params.get('auth_code');
      if (tiktokCode) {
          window.history.replaceState({}, document.title, window.location.pathname);
      }
    };

    useEffect(() => {
        const { data: { subscription } } = supabase.auth.onAuthStateChange((event) => {
            if (event === 'SIGNED_IN' || event === 'INITIAL_SESSION' || event === 'USER_UPDATED') {
                getUser();
            } else if (event === 'SIGNED_OUT') {
                setUser(null);
                setProfile(null);
                localStorage.removeItem('tokcer_admin_auth');
            }
        });

        getUser();

        return () => {
            subscription?.unsubscribe();
        };
    }, []);

  const chargeDailyCredit = async (feature) => {
    if (!user || localStorage.getItem('tokcer_admin_auth') === 'true') return true;

    // 🏮 PLAN CHECK FIRST (Blueprint Security Constraint)
    // Map internal keys to permission keys
    const permKey = feature === 'market' ? 'market_intel' : feature;
    if (!checkPlanPermission(permKey, true)) {
        return false;
    }

    const today = new Date().toISOString().split('T')[0];
    const storageKey = `tokcer_pay_${feature}_${today}`;
    
    if (localStorage.getItem(storageKey)) return true;

    const currentTokens = profile?.tokens ?? 0;
    if (currentTokens < 1) {
        console.warn("Insufficient tokens for feature:", feature);
        return false;
    }

    try {
        const { data, error } = await supabase.rpc('rpc_deduct_token', {
            p_user_id: user.id,
            p_feature: `daily_access_${feature}`,
            p_amount: 1
        });

        if (error || !data.success) {
            console.warn("Deduction failed:", data?.message);
            return false;
        }

        setProfile(prev => ({ ...prev, tokens: data.new_balance }));
        localStorage.setItem(storageKey, 'paid');
        return true;
    } catch (err) {
        console.error("Charge Daily Error:", err);
        return false;
    }
  };

  // 🔽 CUSTOM WRAPPERS FOR MUTUAL EXCLUSION OF DROPDOWNS 🔽
  const handleSetShowPlatformDropdown = (val) => {
    setShowPlatformDropdown(val);
    if (val) {
      setShowFilterDropdown(false);
      setShowOmzetTimeDropdown(false);
      setShowAnalyticsPlatformDropdown(false);
    }
  };

  const handleSetShowFilterDropdown = (val) => {
    setShowFilterDropdown(val);
    if (val) {
      setShowPlatformDropdown(false);
      setShowOmzetTimeDropdown(false);
      setShowAnalyticsPlatformDropdown(false);
    }
  };

  const handleSetShowOmzetTimeDropdown = (val) => {
    setShowOmzetTimeDropdown(val);
    if (val) {
      setShowPlatformDropdown(false);
      setShowFilterDropdown(false);
      setShowAnalyticsPlatformDropdown(false);
    }
  };

  const handleSetShowAnalyticsPlatformDropdown = (val) => {
    setShowAnalyticsPlatformDropdown(val);
    if (val) {
      setShowPlatformDropdown(false);
      setShowFilterDropdown(false);
      setShowOmzetTimeDropdown(false);
    }
  };

  // 🔽 GLOBAL CLICK LISTENER FOR CLICK-OUTSIDE AUTO CLOSE 🔽
  useEffect(() => {
    const handleGlobalClickOutside = (e) => {
      const relativeContainer = e.target.closest('.relative');
      
      // Every dropdown in Tokcer AI contains an arrow icon or is/contains the absolute menu
      const isDropdownClick = relativeContainer && (
        relativeContainer.querySelector('iconify-icon[icon*="alt-arrow-"]') ||
        relativeContainer.querySelector('.absolute') ||
        e.target.closest('.absolute')
      );
      
      if (!isDropdownClick) {
        setShowPlatformDropdown(false);
        setShowFilterDropdown(false);
        setShowOmzetTimeDropdown(false);
        setShowAnalyticsPlatformDropdown(false);
      }
    };
    
    document.addEventListener('click', handleGlobalClickOutside, true);
    return () => document.removeEventListener('click', handleGlobalClickOutside, true);
  }, []);

  useEffect(() => {
    if (activeMenu === 'tab-overview') {
      // Briefing hanya dipanggil saat tab Overview dibuka, 1x per hari via cache
      if (user && products !== null) {
        fetchSystemBriefing(products, orders, user);
      }
    } else if (activeMenu === 'tab-analytics') {
      const plan = (profile?.subscription_plan || 'starter').toLowerCase();
      if (plan === 'starter') {
        // Starter: langsung fetch data statis tanpa deduct token
        fetchAnalyticsInsight();
      } else {
        chargeDailyCredit('analytics').then(allowed => {
          if (allowed) fetchAnalyticsInsight();
        });
      }
    } else if (activeMenu === 'tab-market') {
        chargeDailyCredit('market').then(allowed => {
            if (allowed) fetchGlobalMarketTrends();
        });
    } else if (activeMenu === 'tab-health') {
        chargeDailyCredit('health_check').then(allowed => {
            if (allowed) {
                const safeOrders = Array.isArray(orders) ? orders : [];
                const total = safeOrders.length || 1;
                const cancelled = safeOrders.filter(o => o.status === 'cancelled' || o.status === 'returned').length;
                const returnRate = ((cancelled / total) * 100).toFixed(1) + '%';
                
                fetchHealthInsight({
                    chat: '98%',
                    ship: '1.2 Days',
                    return: returnRate,
                    rating: '4.9/5.0'
                });
            }
        });
    }
  }, [activeMenu, products, orders, healthPlatform, timeFilter]);

  // Reset insights when filters change to allow re-fetching
  useEffect(() => {
    setHealthInsight(null);
  }, [healthPlatform, timeFilter]);

  useEffect(() => {
    setAnalyticsInsight(null);
  }, [analyticsPlatform]);

  useEffect(() => {
    if (profile) {
      const plan = (profile.subscription_plan || 'starter').toLowerCase();
      if (plan === 'starter' && aiFormat.includes('Video')) {
        setAiFormat('Shopee Description');
      }
    }
  }, [profile, aiFormat]);

  useEffect(() => {
    setViralTopics([]);
    setLiveSummary(null);
    setBestsellerProducts([]);
    setViralVideos([]);
    setLiveStreams([]);
    if (activeMenu === 'tab-market') {
      fetchGlobalMarketTrends();
    }
  }, [platformFilter, activeMenu]);

  const [adminClients, setAdminClients] = useState([]);
  const [isAdminLoading, setIsAdminLoading] = useState(false);

  const fetchAdminClients = async () => {
    setIsAdminLoading(true);
    const { data, error } = await supabase
      .from('clients')
      .select('*, partners(full_name)')
      .order('created_at', { ascending: false });
    
    if (error) {
      console.error("Fetch Admin Clients Error:", error);
      alert("Gagal mengambil data: " + error.message);
    } else {
      setAdminClients(data || []);
    }
    setIsAdminLoading(false);
  };

  useEffect(() => {
    if (activeMenu === 'tab-admin') {
      fetchAdminClients();
    }
  }, [activeMenu]);

  const handleApproveClient = async (clientId, email, shopName) => {
    const confirm = window.confirm(`Approve pendaftaran untuk ${shopName}?`);
    if (!confirm) return;

    setIsAdminLoading(true);
    try {
      // 1. Update status di DB
      const { error } = await supabase
        .from('clients')
        .update({ status: 'active', commission_amount: 100000 }) // Misal komisi flat 100k
        .eq('id', clientId);

      if (error) throw error;

      // 2. Simulasi pengiriman email
      alert(`Berhasil di-approve!\n\nEmail instruksi login telah dikirim ke: ${email}\nAkun untuk toko "${shopName}" sedang disiapkan.`);
      
      fetchAdminClients();
    } catch (err) {
      alert("Error: " + err.message);
    } finally {
      setIsAdminLoading(false);
    }
  };

  const handleLogout = async () => {
    if (window.confirm(t('confirmLogout') || 'Logout?')) {
        await supabase.auth.signOut();
        localStorage.removeItem('tokcer_admin_auth');
        localStorage.removeItem('tokcer_cache_analytics_' + user?.id + '_' + new Date().toISOString().split('T')[0]);
        sessionStorage.clear();
        window.location.href = '/login';
    }
  };




    const checkPlanPermission = (feature, silent = false) => {
        const plan = (profile?.subscription_plan || 'starter').toLowerCase();
        const permissions = {
            'video_gen':            ['pro', 'elite', 'ultimate', 'demo'],
            'health_check':         ['pro', 'elite', 'ultimate'],
            'analytics':            ['starter', 'pro', 'elite', 'ultimate'],   // Semua plan bisa akses tab analytics
            'market_intel':         ['elite', 'ultimate', 'demo'],
            'price_optimizer':      ['elite', 'ultimate', 'demo'],
            'competitor_analysis':  ['ultimate'],
            'ai_briefing':          ['pro', 'elite', 'ultimate'],   // System briefing AI
        };
        
        if (permissions[feature] && !permissions[feature].includes(plan)) {
            if (!silent) {
                const minPlan = permissions[feature][0].toUpperCase();
                alert(`⚠️ Fitur ini hanya tersedia untuk paket ${minPlan} ke atas. Silakan upgrade paket Anda!`);
            }
            return false;
        }
        return true;
    };

    const handleGenerateAI = async () => {
    if (!aiPrompt || !user) return;
    
    // Check Plan Permissions for Video Formats
    if (aiFormat.includes('Video') || aiFormat.includes('Reels')) {
        if (!checkPlanPermission('video_gen')) return;
    }

    const isAdmin = profile?.role === 'admin';
    
    // 1. SECURE TOKEN DEDUCTION (PRE-AI CALL)
    let shouldDeductCredit = false;
    if (!isAdmin) {
        const lastPrompt = (localStorage.getItem('tokcer_last_prompt') || '').trim().toLowerCase();
        const currentPrompt = (aiPrompt || '').trim().toLowerCase();
        const userPlan = (profile?.subscription_plan || 'starter').toLowerCase();
        
        // Cek kesamaan topik
        const isSimilar = lastPrompt && (currentPrompt.includes(lastPrompt) || lastPrompt.includes(currentPrompt));
        shouldDeductCredit = true; // Default bayar untuk topik baru

        if (isSimilar) {
            if (userPlan === 'starter') {
                // Starter: Hanya format deskripsi teks (Shopee & TikTok Shop Description) yang gratis.
                const isTextFormat = aiFormat.includes('Description') || aiFormat.includes('Deskripsi') || aiFormat.includes('Caption');
                if (isTextFormat) {
                    shouldDeductCredit = false; // Gratis!
                }
            } else {
                // Pro, Elite, Ultimate, Demo, dll: Format teks dan video semuanya gratis (share 1 token).
                shouldDeductCredit = false; // Gratis!
            }
        }

        if (shouldDeductCredit) {
            // Pre-check state
            if (!profile || (profile.tokens || 0) < 1) {
                setAiResult("⚠️ Maaf, sisa token AI Anda habis. Silakan hubungi admin untuk top-up.");
                return;
            }

            const { data: deductData, error: deductError } = await supabase.rpc('rpc_deduct_token', {
                p_user_id: user.id,
                p_feature: 'content_generator',
                p_amount: 1
            });

            if (deductError || !deductData.success) {
                setAiResult("⚠️ Maaf, sisa token AI Anda habis atau gagal diverifikasi.");
                return;
            }
            
            // Sync state
            setProfile(prev => ({ ...prev, tokens: deductData.new_balance }));
            localStorage.setItem('tokcer_last_prompt', aiPrompt);
        }
    }

    setIsGenerating(true);
    setAiResult('');

    try {
      // 2. Fetch RAG Config
      const { data: config } = await supabase
        .from('ai_configs')
        .select('*')
        .eq('key', 'system_prompt_generator')
        .maybeSingle();

      const targetLang = lang === 'id' ? 'Bahasa Indonesia' : 'English';
      let platformContext = "";
      if (aiFormat === 'TikTok Video') {
        platformContext = `Buatlah naskah video TikTok durasi 3 menit. Sertakan: Hook viral di 3 detik pertama, Breakdown adegan (Scene by Scene), saran musik latar yang sedang tren, dan narasi yang enerjik.`;
      } else if (aiFormat === 'Instagram Reels') {
        platformContext = `Buatlah naskah Instagram Reels yang estetik. Sertakan: Hook yang menarik perhatian, transisi antar adegan, saran filter/mood, dan caption singkat yang powerful.`;
      } else if (aiFormat === 'Shopee Description') {
        platformContext = `Buatlah deskripsi produk khusus Shopee. Gunakan banyak emoji, highlight promo/voucher, dan gaya bahasa yang persuasif serta "hype" untuk menarik pembeli diskon.`;
      } else if (aiFormat === 'TikTok Shop Description') {
        platformContext = `Buatlah deskripsi produk TikTok Shop. Fokus pada 'USP' produk secara cepat, buat kesan urgensi/kelangkaan, dan arahkan ke keranjang kuning.`;
      }

      if (lang === 'en') {
        platformContext = platformContext
            .replace('Buatlah naskah video TikTok durasi 3 menit', 'Create a 3-minute TikTok video script')
            .replace('Sertakan: Hook viral di 3 detik pertama, Breakdown adegan (Scene by Scene), saran musik latar yang sedang tren, dan narasi yang enerjik.', 'Include: Viral hook in the first 3 seconds, Scene by Scene breakdown, trending background music suggestions, and energetic narration.')
            .replace('Buatlah naskah Instagram Reels yang estetik', 'Create an aesthetic Instagram Reels script')
            .replace('Sertakan: Hook yang menarik perhatian, transisi antar adegan, saran filter/mood, dan caption singkat yang powerful.', 'Include: Attention-grabbing hook, transitions between scenes, filter/mood suggestions, and a powerful short caption.')
            .replace('Buatlah deskripsi produk khusus Shopee', 'Create a specific Shopee product description')
            .replace('Gunakan banyak emoji, highlight promo/voucher, dan gaya bahasa yang persuasif serta "hype" untuk menarik pembeli diskon.', 'Use plenty of emojis, highlight promos/vouchers, and use persuasive "hype" language to attract discount hunters.')
            .replace('Buatlah deskripsi produk TikTok Shop', 'Create a TikTok Shop product description')
            .replace("Fokus pada 'USP' produk secara cepat, buat kesan urgensi/kelangkaan, dan arahkan ke keranjang kuning.", "Focus on the product's USP quickly, create a sense of urgency/scarcity, and direct to the yellow basket.");
      }

      // 3. Tentukan Max Tokens Dinamis (Biar Hemat)
      let computedMaxTokens = 1024; // Standard Video/Reels
      if (aiFormat.includes('Description') || aiFormat.includes('Deskripsi') || aiFormat.includes('Caption')) {
        computedMaxTokens = 500;
      }

      // 4. Tambahkan Instruksi Batasan Token yang Rapi (Biar Kalimat Tidak Terpotong)
      const limitWarning = lang === 'id'
        ? `\n\n⚠️ PERINGATAN PENTING BATAS PANJANG KONTEN: Batas maksimum respon Anda adalah ${computedMaxTokens} token. Anda WAJIB merencanakan dan membagi alur penulisan konten Anda agar SELESAI SECARA UTUH, TUNTAS, DAN RAPI di bawah batas ${computedMaxTokens} token ini. JANGAN MENULIS kalimat yang terlalu bertele-tele atau panjang yang dapat terpotong di tengah jalan. Pastikan paragraf atau poin penutup diselesaikan dengan tuntas (tidak ada kata atau kalimat yang menggantung di akhir).`
        : `\n\n⚠️ CRITICAL LIMITATION WARNING: Your maximum allowed response length is ${computedMaxTokens} tokens. You MUST plan and structure your response carefully so that it is COMPLETELY FINISHED, WHOLE, AND TUNTAS within this ${computedMaxTokens} tokens limit. DO NOT write excessively long or wordy paragraphs that will get brutally cut off. Ensure that all closing sentences, lists, or paragraphs are fully completed and neat (no half-finished words or dangling sentences at the end).`;

      const fullSystemPrompt = `${config?.value || ''}\n\nATURAN KHUSUS: Respon WAJIB dalam ${targetLang}. ${platformContext}${limitWarning}`;
      const userMessage = `Buat konten untuk produk berikut:\n\n${aiPrompt}\n\nPastikan konten berbeda dari sebelumnya (variatif) dan sangat spesifik untuk format ${aiFormat}.`;

      // 5. CALL AI ENGINE
      const { text: result, usage } = await callAiEngine(fullSystemPrompt, userMessage, computedMaxTokens, 0.8);
      
      setAiResult(result);

      // Log Usage — sertakan token aktual dari DeepSeek response
      await supabase.from('ai_usage_logs').insert([{
          user_id: user?.id || null,
          feature: 'content_generator',
          prompt: userMessage,
          response: result,
          input_tokens: usage?.prompt_tokens || 0,
          output_tokens: usage?.completion_tokens || 0,
          tokens_used: shouldDeductCredit ? 1 : 0
      }]);

    } catch (e) {
      console.error("AI Generation Error:", e);

      // ── Rollback credit jika AI gagal ──────────────────────────────────────
      if (shouldDeductCredit && !isAdmin) {
        try {
          await supabase.rpc('rpc_refund_token', {
            p_user_id: user.id,
            p_feature: 'content_generator',
            p_amount: 1
          });
          setProfile(prev => ({ ...prev, tokens: (prev?.tokens || 0) + 1 }));
        } catch (refundErr) {
          console.warn("Refund credit gagal:", refundErr);
        }
      }

      // Pesan error yang lebih informatif
      const errMsg = e.message || '';
      if (errMsg.includes('non-2xx') || errMsg.includes('Edge Function')) {
        setAiResult('❌ Server AI sedang tidak tersedia. Credit Anda telah dikembalikan. Silakan coba beberapa saat lagi.');
      } else if (errMsg.includes('Insufficient Balance') || errMsg.includes('402')) {
        setAiResult('❌ Layanan AI sedang dalam pemeliharaan. Credit Anda telah dikembalikan. Mohon hubungi admin.');
      } else {
        setAiResult(`❌ Terjadi kesalahan: ${errMsg}`);
      }
    } finally {
      setIsGenerating(false);
    }
  };

    const handleAnalyzeTrend = async () => {
        if (!trendPrompt) return;
        
        if (!checkPlanPermission('market_intel')) return;

        setIsTrendAnalyzing(true);
        setTrendResult('');

    try {
      // 1. Hardened Token Deduction (RPC Daily Tax Enabled)
      const isAdmin = localStorage.getItem('tokcer_admin_auth') === 'true';
      if (!isAdmin) {
          const { data: deductData, error: deductError } = await supabase.rpc('rpc_deduct_token', {
              p_user_id: user.id,
              p_feature: 'daily_access_market_intel_analysis',
              p_amount: 1
          });

          if (deductError || !deductData.success) {
              setTrendResult(deductData?.message || "⚠️ Maaf, sisa token AI Anda habis.");
              setIsTrendAnalyzing(false);
              return;
          }
          setProfile(prev => ({ ...prev, tokens: deductData.new_balance }));
      }

      // 2. Fetch RAG Config for Analyst
      const { data: config } = await supabase
        .from('ai_configs')
        .select('*')
        .eq('key', 'system_prompt_market_analyst')
        .maybeSingle();

      const bizType = profile?.business_type || 'General E-commerce';
      
      const systemPrompt = config?.value || `You are an elite Market Research Analyst for the Indonesian e-commerce market. Provide a deep, structured analysis covering niche definition, market demand & trends, competitive landscape, business viability & strategy, and a final verdict.`;
      
      const targetLang = lang === 'id' ? 'Bahasa Indonesia' : 'English';
      const computedMaxTokens = 1024;
      const limitWarning = lang === 'id'
        ? `\n\n⚠️ PERINGATAN PENTING BATAS PANJANG KONTEN: Batas maksimum respon Anda adalah ${computedMaxTokens} token. Anda WAJIB merencanakan dan membagi alur analisis pasar Anda agar SELESAI SECARA UTUH, TUNTAS, DAN RAPI di bawah batas ${computedMaxTokens} token ini. JANGAN MENULIS kalimat yang terlalu bertele-tele atau analisis yang terpotong di tengah jalan. Pastikan kesimpulan akhir atau closing paragraph diselesaikan dengan tuntas (tidak ada kata atau kalimat yang menggantung di akhir).`
        : `\n\n⚠️ CRITICAL LIMITATION WARNING: Your maximum allowed response length is ${computedMaxTokens} tokens. You MUST plan and structure your market analysis carefully so that it is COMPLETELY FINISHED, WHOLE, AND TUNTAS within this ${computedMaxTokens} tokens limit. DO NOT write excessively long paragraphs that will get cut off. Ensure that the final verdict or closing paragraph is fully completed and neat (no half-finished words or dangling sentences at the end).`;

      const fullSystemPrompt = `${systemPrompt}\n\nATURAN KHUSUS: Respon WAJIB dalam ${targetLang}.${limitWarning}`;
      
      // 3. Call Intelligence Engine (using master API key from .env automatically)
      const userQuery = `Analyze this niche/product: "${trendPrompt}" within my business category: ${bizType}`;
      const { text: result, usage } = await callAiEngine(fullSystemPrompt, userQuery, computedMaxTokens, 0.5);
      setTrendResult(result);

      // Log Usage — sertakan token aktual dari DeepSeek response
      await supabase.from('ai_usage_logs').insert([{
          user_id: user?.id || null,
          feature: 'market_intel_analysis_complete',
          prompt: userQuery,
          response: result,
          input_tokens: usage?.prompt_tokens || 0,
          output_tokens: usage?.completion_tokens || 0,
          tokens_used: 1
      }]);

      // Token usage already logged and deducted by RPC above
    } catch (e) {
      console.error(e);
      setTrendResult("Maaf, terjadi kesalahan saat menganalisa tren.");
    } finally {
      setIsTrendAnalyzing(false);
    }
  };

  const fetchGlobalMarketTrends = async () => {
    if (isFetchingTrends) return;

    setIsFetchingTrends(true);

    try {
      const bizType = profile?.business_type || 'General E-commerce';

      // Panggil modul servis terisolasi dengan zero-budget database cache
      const data = await getRealMarketIntel({
        platformFilter,
        bizType,
        userId: user?.id,
        callAiEngine
      });

      if (data.topics) setViralTopics(data.topics);
      if (data.products) setBestsellerProducts(data.products);
      if (data.videos) setViralVideos(data.videos);
      if (data.lives) setLiveStreams(data.lives);
      if (data.summary) setLiveSummary(data.summary);

    } catch (err) {
      console.error("Error fetching market trends:", err);
    } finally {
      setIsFetchingTrends(false);
    }
  };

  const handleUpdatePassword = async (e) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setSecurityMessage({ type: 'error', text: lang === 'id' ? 'Password tidak cocok!' : 'Passwords do not match!' });
      return;
    }
    if (newPassword.length < 6) {
      setSecurityMessage({ type: 'error', text: lang === 'id' ? 'Minimal 6 karakter!' : 'At least 6 characters!' });
      return;
    }
    setIsUpdatingPassword(true);
    setSecurityMessage({ type: '', text: '' });
    try {
      const { error } = await supabase.auth.updateUser({ password: newPassword });
      if (error) throw error;
      setSecurityMessage({ type: 'success', text: lang === 'id' ? 'Password berhasil diperbarui!' : 'Password updated successfully!' });
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      setSecurityMessage({ type: 'error', text: err.message });
    } finally {
      setIsUpdatingPassword(false);
    }
  };

  const handleDownloadReport = () => {
    if (orders.length === 0) {
      alert("Belum ada data untuk diunduh.");
      return;
    }

    // Generate CSV from real orders data
    const csvRows = [
      ['Order ID', 'Produk Terjual', 'Platform', 'Nominal (Rp)', 'Status', 'Tanggal'],
      ...orders.map(o => [
        o.order_number || o.id,
        o.customer_name || 'Customer',
        o.platform || 'N/A',
        o.total_amount || 0,
        o.status || 'N/A',
        o.order_date || 'N/A'
      ])
    ];

    const csvContent = "data:text/csv;charset=utf-8," 
      + csvRows.map(e => e.join(",")).join("\n");
    
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `Laporan_Omzet_TokcerAI_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const fetchUserTickets = async () => {
    if (!user) return;
    setIsFetchingUserTickets(true);
    try {
      const { data, error } = await supabase
        .from('support_tickets')
        .select('*')
        .eq('user_id', user.id)
        .order('created_at', { ascending: false });
        
      if (error) throw error;
      setUserTickets(data || []);
    } catch (err) {
      console.error("Error fetching user tickets:", err);
    } finally {
      setIsFetchingUserTickets(false);
    }
  };

  useEffect(() => {
    if (activeMenu === 'tab-support' && user) {
      fetchUserTickets();
    }
  }, [activeMenu, user]);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSupportFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setSupportFilePreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSupportSubmit = async (e) => {
    e.preventDefault();
    if (!user) return;
    setIsSubmittingSupport(true);
    
    try {
      let attachmentUrl = null;

      // 1. Upload File if exists (only applicable for bug reports)
      if (supportType === 'bug' && supportFile) {
        try {
          const fileExt = supportFile.name.split('.').pop();
          const fileName = `${user.id}-${Date.now()}.${fileExt}`;
          const filePath = `support-attachments/${fileName}`;

          const { error: uploadError } = await supabase.storage
            .from('support-files')
            .upload(filePath, supportFile);

          if (uploadError) throw uploadError;

          const { data: { publicUrl } } = supabase.storage
            .from('support-files')
            .getPublicUrl(filePath);
          
          attachmentUrl = publicUrl;
        } catch (uploadError) {
          console.warn("Supabase Storage bucket upload failed, using secure Base64 fallback:", uploadError);
          
          // Secure Base64 Fallback (stores base64 string directly in attachment_url TEXT column)
          attachmentUrl = await new Promise((resolve) => {
            const reader = new FileReader();
            reader.onloadend = () => resolve(reader.result);
            reader.readAsDataURL(supportFile);
          });
        }
      }

      // 2. Insert Ticket to DB
      const { error: insertError } = await supabase
        .from('support_tickets')
        .insert([{
          user_id: user.id === 'admin-bypass' ? null : user.id,
          type: supportType,
          title: supportTitle,
          description: supportDesc,
          attachment_url: attachmentUrl,
          status: 'open'
        }]);

      if (insertError) throw insertError;

      setSupportSubmitted(true);
      
      // Reset form
      setSupportTitle('');
      setSupportDesc('');
      setSupportFile(null);
      setSupportFilePreview(null);
      
      fetchUserTickets();
    } catch (err) {
      console.error("Support Submission Error:", err);
      alert("❌ Gagal mengirim laporan: " + err.message);
    } finally {
      setIsSubmittingSupport(false);
    }
  };


  const renderContent = () => {
    switch (activeMenu) {
      case 'tab-admin':
        return (
          <AdminTab 
            adminClients={adminClients}
            isAdminLoading={isAdminLoading}
            handleApproveClient={handleApproveClient}
          />
        );
      case 'tab-dash':
        return (
          <OverviewTab 
            t={t} 
            orders={orders} 
            products={products} 
            timeFilter={timeFilter}
            setTimeFilter={setTimeFilter}
            showFilterDropdown={showFilterDropdown}
            setShowFilterDropdown={handleSetShowFilterDropdown}
            platformFilter={platformFilter}
            setPlatformFilter={setPlatformFilter}
            showPlatformDropdown={showPlatformDropdown}
            setShowPlatformDropdown={handleSetShowPlatformDropdown}
            profile={profile}
            lang={lang}
            setActiveMenu={setActiveMenu}
            systemBriefing={systemBriefing}
            isFetchingBriefing={isFetchingBriefing}
            orders={orders}
            products={products}
          />
        );
      case 'tab-omzet':
        return (
          <RevenueTab 
            t={t}
            orders={orders}
            platformFilter={platformFilter}
            setPlatformFilter={setPlatformFilter}
            showPlatformDropdown={showPlatformDropdown}
            setShowPlatformDropdown={handleSetShowPlatformDropdown}
            omzetTimeFilter={omzetTimeFilter}
            setOmzetTimeFilter={setOmzetTimeFilter}
            showOmzetTimeDropdown={showOmzetTimeDropdown}
            setShowOmzetTimeDropdown={handleSetShowOmzetTimeDropdown}
            handleDownloadReport={handleDownloadReport}
            handleImportOrders={handleImportOrders}
          />
        );
      case 'tab-inventory':
        return (
          <InventoryTab 
            t={t}
            products={products}
            setShowProductModal={setShowProductModal}
            handleImportProducts={handleImportProducts}
          />
        );

      case 'tab-billing':
        return (
          <BillingTab 
            user={user} 
            profile={profile} 
            clientData={clientData}
            supabase={supabase} 
            t={t}
          />
        );
      case 'tab-analytics':
        return (
          <AnalyticsTab 
            t={t}
            profile={profile}
            timeFilter={timeFilter}
            setTimeFilter={setTimeFilter}
            showFilterDropdown={showFilterDropdown}
            setShowFilterDropdown={handleSetShowFilterDropdown}
            analyticsPlatform={analyticsPlatform}
            setAnalyticsPlatform={setAnalyticsPlatform}
            showAnalyticsPlatformDropdown={showAnalyticsPlatformDropdown}
            setShowAnalyticsPlatformDropdown={handleSetShowAnalyticsPlatformDropdown}
            lang={lang}
            orders={orders}
            products={products}
            analyticsInsight={analyticsInsight}
            isAnalyzingAnalytics={isAnalyzingAnalytics}
          />
        );
      case 'tab-health':
        return (
          <HealthScoreTab 
            t={t}
            profile={profile}
            lang={lang}
            healthPlatform={healthPlatform}
            setHealthPlatform={setHealthPlatform}
            timeFilter={timeFilter}
            setTimeFilter={setTimeFilter}
            showFilterDropdown={showFilterDropdown}
            setShowFilterDropdown={handleSetShowFilterDropdown}
            orders={orders}
            healthInsight={healthInsight}
            isAnalyzingHealth={isAnalyzingHealth}
          />
        );
      case 'tab-ai':
        return (
          <AiGeneratorTab 
            t={t}
            aiSubTab={aiSubTab}
            setAiSubTab={setAiSubTab}
            aiPrompt={aiPrompt}
            setAiPrompt={setAiPrompt}
            aiFormat={aiFormat}
            setAiFormat={setAiFormat}
            aiResult={aiResult}
            setAiResult={setAiResult}
            isGenerating={isGenerating}
            handleGenerateAI={handleGenerateAI}
            profile={profile}
          />
        );
      case 'tab-market':
        return (
          <MarketIntelTab 
            t={t}
            profile={profile}
            lang={lang}
            platformFilter={platformFilter}
            setPlatformFilter={setPlatformFilter}
            showPlatformDropdown={showPlatformDropdown}
            setShowPlatformDropdown={handleSetShowPlatformDropdown}
            viralTopics={viralTopics}
            bestsellerProducts={bestsellerProducts}
            viralVideos={viralVideos}
            liveStreams={liveStreams}
            trendCustomInput={trendCustomInput}
            setTrendCustomInput={setTrendCustomInput}
            isSearchingTrend={isSearchingTrend}
            isTrendAnalyzing={isTrendAnalyzing}
            trendPrompt={trendPrompt}
            setTrendPrompt={setTrendPrompt}
            handleAnalyzeTrend={handleAnalyzeTrend}
            trendSampleKey={trendSampleKey}
            setTrendSampleKey={setTrendSampleKey}
            trendResult={trendResult}
            liveSummary={liveSummary}
            fetchGlobalMarketTrends={fetchGlobalMarketTrends}
          />
        );
      case 'tab-support':
        return (
          <SupportTab 
            t={t}
            lang={lang}
            profile={profile}
            supportSubmitted={supportSubmitted}
            setSupportSubmitted={setSupportSubmitted}
            setActiveMenu={setActiveMenu}
            supportType={supportType}
            setSupportType={setSupportType}
            handleSupportSubmit={handleSupportSubmit}
            supportTitle={supportTitle}
            setSupportTitle={setSupportTitle}
            supportDesc={supportDesc}
            setSupportDesc={setSupportDesc}
            supportFile={supportFile}
            handleFileChange={handleFileChange}
            supportFilePreview={supportFilePreview}
            setSupportFile={setSupportFile}
            setSupportFilePreview={setSupportFilePreview}
            isSubmittingSupport={isSubmittingSupport}
            userTickets={userTickets}
            isFetchingUserTickets={isFetchingUserTickets}
          />
        );
      case 'tab-account':
        return (
          <AccountTab 
            t={t}
            lang={lang}
            securityMessage={securityMessage}
            newPassword={newPassword}
            setNewPassword={setNewPassword}
            confirmPassword={confirmPassword}
            setConfirmPassword={setConfirmPassword}
            isUpdatingPassword={isUpdatingPassword}
            handleUpdatePassword={handleUpdatePassword}
            profile={profile}
            user={user}
            clientData={clientData}
          />
        );
      case 'tab-connections':
        return (
          <MarketplaceSyncTab 
            t={t}
            lang={lang}
            onConnectShopee={handleConnectShopee}
            onConnectTikTok={handleConnectTikTok}
            connectedStores={marketplaceConnections}
            onSyncStore={handleSyncStore}
            isSyncingStore={isSyncingStore}
          />
        );
      default:
        return null;
    }
  };

  const isDemoExpired = useMemo(() => {
    if (!profile) return false;
    const plan = (profile.subscription_plan || 'starter').toLowerCase();
    if (plan === 'demo' && profile.created_at) {
      const createdAt = new Date(profile.created_at);
      const now = new Date();
      const diffTime = Math.abs(now - createdAt);
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)); 
      return diffDays > 14;
    }
    return false;
  }, [profile]);

  if (isDemoExpired) {
    return (
        <div className="flex h-screen bg-[#050505] text-white font-['Inter',sans-serif] items-center justify-center p-4">
            <div className="bg-zinc-900 border border-zinc-800 p-8 rounded-2xl max-w-md text-center shadow-2xl relative z-50">
                <div className="w-16 h-16 bg-red-500/10 border border-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                    <iconify-icon icon="solar:clock-circle-bold-duotone" className="text-3xl text-red-500"></iconify-icon>
                </div>
                <h2 className="text-xl font-bold text-white mb-2">Masa Percobaan Berakhir</h2>
                <p className="text-zinc-400 text-sm mb-6">Masa aktif 14 hari akun Demo Anda telah berakhir. Terima kasih telah mencoba Tokcer AI! Silakan hubungi tim kami untuk konsultasi dan upgrade paket.</p>
                <button onClick={handleLogout} className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-3 rounded-xl font-bold transition-all text-sm w-full uppercase tracking-widest">Keluar Sistem</button>
            </div>
        </div>
    );
  }

  return (
    <div className="flex h-screen bg-black text-white font-['Inter',sans-serif] overflow-hidden">
      <Sidebar 
        t={t}
        activeMenu={activeMenu}
        setActiveMenu={setActiveMenu}
        isSidebarOpen={isSidebarOpen}
        setIsSidebarOpen={setIsSidebarOpen}
        lang={lang}
        setLang={setLang}
        profile={profile}
        user={user}
        handleLogout={handleLogout}
        clientData={clientData}
      />


      {/* Main Content */}
      <main className="flex-1 min-w-0 bg-zinc-900 overflow-y-auto overflow-x-hidden custom-scrollbar relative">
        {/* Mobile Dashboard Header */}
        <Header setIsSidebarOpen={setIsSidebarOpen} />

        {/* Content Spacer for Fixed Header on Mobile */}
        <div className="h-16 lg:hidden"></div>

        <div className="max-w-6xl mx-auto p-4 md:p-8 relative">
          {clientData?.status === 'expired' && activeMenu !== 'tab-billing' && (
            <div className="absolute inset-0 z-50 bg-zinc-900/90 backdrop-blur-md flex flex-col items-center justify-center p-6 text-center rounded-3xl border border-red-500/20 m-4 md:m-8">
                <div className="w-20 h-20 bg-red-500/10 rounded-full flex items-center justify-center mb-4">
                    <iconify-icon icon="solar:danger-triangle-bold" className="text-4xl text-red-500"></iconify-icon>
                </div>
                <h2 className="text-2xl font-bold text-white mb-2">Masa Langganan Habis</h2>
                <p className="text-zinc-400 mb-6 max-w-md">Akun Anda telah melewati batas waktu kedaluwarsa. Silakan masuk ke menu Billing untuk melakukan perpanjangan paket agar sistem dapat digunakan kembali.</p>
                <button onClick={() => setActiveMenu('tab-billing')} className="px-6 py-3 bg-orange-500 hover:bg-orange-600 text-white font-bold rounded-xl shadow-lg shadow-orange-500/20 transition-all flex items-center gap-2">
                    <iconify-icon icon="solar:wallet-bold"></iconify-icon>
                    Buka Menu Pembayaran
                </button>
            </div>
          )}
          <div className={`relative ${clientData?.status === 'expired' && activeMenu !== 'tab-billing' ? 'opacity-20 pointer-events-none blur-sm transition-all h-[70vh] overflow-hidden' : ''}`}>
            {/* === DEMO CONTENT LOCK OVERLAY === */}
            {(() => {
              const currentPlan = (profile?.subscription_plan || 'starter').toLowerCase();
              const isAdmin = user?.email === 'admin@tokcer-ai.com' || localStorage.getItem('tokcer_admin_auth') === 'true';
              const allowedDemoTabs = ['tab-ai', 'tab-market', 'tab-support', 'tab-billing', 'tab-account'];
              const isDemoLocked = currentPlan === 'demo' && !isAdmin && !allowedDemoTabs.includes(activeMenu);

              if (!isDemoLocked) return null;

              return (
                <div className="absolute inset-0 z-30 flex flex-col items-center justify-center rounded-2xl overflow-hidden" style={{backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)', background: 'rgba(0,0,0,0.65)'}}>
                  <div className="flex flex-col items-center text-center px-8 max-w-md animate-in fade-in zoom-in duration-500">
                    <div className="w-16 h-16 rounded-2xl bg-zinc-900 border border-zinc-700 flex items-center justify-center mb-5 shadow-xl">
                      <iconify-icon icon="solar:lock-password-bold-duotone" className="text-4xl text-zinc-500"></iconify-icon>
                    </div>
                    <h3 className="text-lg font-bold text-white mb-2">Fitur Tidak Tersedia di Akun Demo</h3>
                    <p className="text-sm text-zinc-400 leading-relaxed mb-6">
                      Halaman ini hanya bisa diakses setelah upgrade ke paket berbayar. Akun Demo Anda memberikan akses ke <span className="text-orange-400 font-medium">AI Generator</span>, <span className="text-orange-400 font-medium">Market Intel</span>, <span className="text-orange-400 font-medium">Pusat Bantuan</span>, dan <span className="text-orange-400 font-medium">Billing</span>.
                    </p>
                    <button
                      onClick={() => setActiveMenu('tab-billing')}
                      className="px-6 py-2.5 bg-orange-600 hover:bg-orange-500 text-white text-sm font-bold rounded-xl transition-all shadow-lg shadow-orange-500/20 flex items-center gap-2"
                    >
                      <iconify-icon icon="solar:rocket-bold"></iconify-icon>
                      Lihat Paket & Harga
                    </button>
                  </div>
                </div>
              );
            })()}
            {/* === END DEMO CONTENT LOCK OVERLAY === */}
            {renderContent()}
          </div>
        </div>
      </main>

      <ProductModal isOpen={showProductModal} onClose={() => setShowProductModal(false)} t={t} onSave={async (product) => {
        const { error } = await supabase.from('products').insert([{
          user_id: user?.id === 'admin-bypass' ? null : user?.id,
          name: product.name,
          sku: product.sku,
          stock: product.stock,
          price: product.price,
          platform: product.platform,
        }]);
        if (error) throw error;
        fetchOperationalData(user?.id);
      }} />
    </div>
  );
};

export default Dashboard;
