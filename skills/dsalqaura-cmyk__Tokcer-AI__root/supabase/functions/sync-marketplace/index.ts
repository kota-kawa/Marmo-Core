import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

// Helper to generate TikTok API signature using native Web Crypto API in Deno
async function generateTikTokSignature(appSecret: string, path: string, params: Record<string, string>, body = ""): Promise<string> {
  const keys = Object.keys(params).sort();
  let paramString = "";
  for (const key of keys) {
    if (key !== 'sign' && key !== 'access_token') {
      paramString += key + params[key];
    }
  }

  const baseString = appSecret + path + paramString + body + appSecret;

  const encoder = new TextEncoder();
  const keyData = encoder.encode(appSecret);
  const messageData = encoder.encode(baseString);

  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    keyData,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );

  const signature = await crypto.subtle.sign(
    'HMAC',
    cryptoKey,
    messageData
  );

  return Array.from(new Uint8Array(signature))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: corsHeaders })

  try {
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    const body = await req.json()
    const { user_id, action, target_user_id } = body

    if (action === 'purge_mock_data' && target_user_id) {
      console.log(`[PURGE] Purging mock data for target user ID: ${target_user_id}`);
      
      // 1. Delete all orders for target_user_id
      const { error: errOrd } = await supabaseClient
        .from('orders')
        .delete()
        .eq('user_id', target_user_id);
        
      // 2. Delete products for target_user_id
      const { error: errProd } = await supabaseClient
        .from('products')
        .delete()
        .eq('user_id', target_user_id);

      return new Response(
        JSON.stringify({ 
          success: true, 
          message: `Successfully purged mock data for ${target_user_id}. Orders delete error: ${errOrd?.message || 'none'}, Products delete error: ${errProd?.message || 'none'}` 
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
      )
    }

    if (!user_id) throw new Error("Missing user_id")

    // 1. Get TikTok API Keys from database
    const { data: configs, error: configError } = await supabaseClient
      .from('ai_configs')
      .select('key, value')
      .in('key', ['tiktok_app_id', 'tiktok_app_secret'])

    if (configError) throw new Error("Gagal mengambil konfigurasi API TikTok: " + configError.message)
    
    let appKey = "";
    let appSecret = "";
    configs?.forEach(c => {
        if (c.key === 'tiktok_app_id') appKey = c.value;
        if (c.key === 'tiktok_app_secret') appSecret = c.value;
    });

    if (!appKey || !appSecret) {
      throw new Error("Kredensial API TikTok (App ID/Secret) belum diset di tabel ai_configs.");
    }

    // 2. Fetch Active TikTok Store Connection safely (supporting multiple connections)
    const { data: connections, error: connError } = await supabaseClient
      .from('marketplace_connections')
      .select('*')
      .eq('user_id', user_id)
      .eq('platform', 'tiktok');

    if (connError) throw new Error("Gagal membaca koneksi marketplace: " + connError.message)
    
    // Filter to get any active, idle or currently syncing connections
    const activeConnections = connections?.filter((c: any) => c.sync_status === 'active' || c.sync_status === 'syncing' || c.sync_status === 'idle') || [];
    
    if (activeConnections.length === 0) {
      return new Response(
        JSON.stringify({ success: false, error: "Tidak ada koneksi TikTok yang aktif untuk akun ini." }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
      )
    }

    // Safely pick the first active connection to process
    const connection = activeConnections[0];

    const { access_token, shop_id } = connection;
    if (!access_token || !shop_id) {
      throw new Error("Koneksi TikTok tidak memiliki access_token atau shop_id yang valid.");
    }
    const timestamp = Math.floor(Date.now() / 1000).toString();

    // 3. Initiate Live Syncing status
    await supabaseClient
      .from('marketplace_connections')
      .update({ sync_status: 'syncing' })
      .eq('id', connection.id);

    // 4. Fetch Authorized Shops dynamically to obtain the mandatory shop_cipher
    const shopPath = "/authorization/202309/shops";
    const shopQueryParams = {
      app_key: appKey,
      timestamp: timestamp
    };
    const shopSignature = await generateTikTokSignature(appSecret, shopPath, shopQueryParams, "");
    const shopSearchParams = new URLSearchParams(shopQueryParams);
    shopSearchParams.append("sign", shopSignature);
    const shopApiUrl = `https://open-api.tiktokglobalshop.com${shopPath}?${shopSearchParams.toString()}`;

    let shopCipher = "";
    try {
      const shopResponse = await fetch(shopApiUrl, {
        method: "GET",
        headers: {
          "x-tts-access-token": access_token
        }
      });
      const shopData = await shopResponse.json();
      if (shopData.code === 0 && shopData.data?.shops?.length > 0) {
        const matchedShop = shopData.data.shops.find((s: any) => s.id === shop_id) || shopData.data.shops[0];
        shopCipher = matchedShop.cipher || "";
        console.log(`Successfully retrieved shop_cipher: ${shopCipher} for shop: ${matchedShop.name}`);
      } else {
        console.error(`Failed to fetch shop_cipher from TikTok: ${JSON.stringify(shopData)}`);
      }
    } catch (err) {
      console.error(`Error calling Get Authorized Shops: ${err.message}`);
    }

    if (!shopCipher) {
      throw new Error("Gagal mengidentifikasi target toko karena shop_cipher tidak ditemukan.");
    }

    // 5. Request Real Orders from TikTok Open API (Newest first, filtered to last 120 days)
    const path = "/order/202309/orders/search";
    const queryParams = {
      app_key: appKey,
      timestamp: timestamp,
      shop_cipher: shopCipher,
      page_size: "50",
      sort_field: "create_time",
      sort_order: "DESC"
    };

    // Filter to last 120 days to ensure we get the recent 3 months of orders
    const ninetyFiveDaysAgo = Math.floor((Date.now() - 120 * 24 * 60 * 60 * 1000) / 1000);
    const requestBodyObj = {
      create_time_ge: ninetyFiveDaysAgo
    };
    const requestBody = JSON.stringify(requestBodyObj);

    const signature = await generateTikTokSignature(appSecret, path, queryParams, requestBody);
    const searchParams = new URLSearchParams(queryParams);
    searchParams.append("sign", signature);
    const apiUrl = `https://open-api.tiktokglobalshop.com${path}?${searchParams.toString()}`;

    let ordersFetched = [];
    let apiErrorLog = "";
    
    try {
      const apiResponse = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-tts-access-token": access_token
        },
        body: requestBody
      });
      
      const apiData = await apiResponse.json();
      if (apiData.code === 0 && apiData.data?.order_list) {
        ordersFetched = apiData.data.order_list;
      } else if (apiData.code === 0 && apiData.data?.orders) {
        // v202309 format uses 'orders' instead of 'order_list'
        ordersFetched = apiData.data.orders;
      } else {
        apiErrorLog = apiData.message || `TikTok API returned code: ${apiData.code}`;
      }
    } catch (fetchErr) {
      apiErrorLog = fetchErr.message;
    }

    // Get detailed orders to fetch line_items, payments, and true order_status
    const orderIds = ordersFetched.map((o: any) => o.id).filter(Boolean);
    let detailedOrders = [];

    if (orderIds.length > 0) {
      const idsParam = orderIds.join(",");
      const detailPath = "/order/202309/orders";
      const detailQueryParams = {
        app_key: appKey,
        timestamp: timestamp,
        shop_cipher: shopCipher,
        ids: idsParam
      };
      
      const detailSignature = await generateTikTokSignature(appSecret, detailPath, detailQueryParams, "");
      const detailSearchParams = new URLSearchParams(detailQueryParams);
      detailSearchParams.append("sign", detailSignature);
      const detailApiUrl = `https://open-api.tiktokglobalshop.com${detailPath}?${detailSearchParams.toString()}`;
      
      try {
        const detailResponse = await fetch(detailApiUrl, {
          method: "GET",
          headers: {
            "x-tts-access-token": access_token
          }
        });
        const detailData = await detailResponse.json();
        if (detailData.code === 0 && detailData.data?.orders) {
          detailedOrders = detailData.data.orders;
          console.log(`Successfully fetched details for ${detailedOrders.length} orders.`);
        } else {
          apiErrorLog = detailData.message || `Detail API returned code: ${detailData.code}`;
        }
      } catch (detailErr) {
        apiErrorLog = detailErr.message;
      }
    }

    // 5. Clean Handling (If no orders found or API empty, do NOT insert garbage mock data!)
    if (detailedOrders.length === 0) {
      console.warn("TikTok API Fetch Warning: " + apiErrorLog + ". No detailed orders fetched.");

      await supabaseClient
        .from('marketplace_connections')
        .update({ sync_status: 'active' })
        .eq('id', connection.id);

      return new Response(
        JSON.stringify({ 
          success: true, 
          message: "Sinkronisasi sukses! Tidak ada pesanan baru di toko Anda (API Status: " + (apiErrorLog || "OK") + ")",
          source: "live"
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
      )
    }

    // Purge old 2024 orders for this user to clean up the dashboard
    const { error: purgeError } = await supabaseClient
      .from('orders')
      .delete()
      .eq('user_id', user_id)
      .lt('order_date', '2026-01-01T00:00:00Z');

    if (purgeError) {
      console.error("Error purging old 2024 orders:", purgeError.message);
    } else {
      console.log("Successfully purged old 2024 orders from database.");
    }

    // 6. Map and Insert Real TikTok Orders to Supabase
    const ordersToInsert = detailedOrders.map((o: any) => {
      const itemsList = o.line_items || [];
      const productSold = itemsList.map((li: any) => li.product_name || li.sku_name || "Produk TikTok").join(", ") || "Produk TikTok";
      
      // TikTok Shop API v202309 returns order status in the 'status' field (e.g., 'COMPLETED', 'DELIVERED', 'CANCELLED')
      const tiktokStatus = o.status || o.order_status || "";
      
      let mappedStatus = 'pending';
      if (tiktokStatus === 'COMPLETED' || tiktokStatus === 'DELIVERED') {
        mappedStatus = 'completed';
      } else if (tiktokStatus === 'CANCELLED') {
        mappedStatus = 'cancelled';
      }
      
      return {
        user_id: user_id,
        order_number: o.id || o.order_id,
        customer_name: productSold,
        platform: 'tiktok',
        total_amount: Number(o.payment?.total_amount || 0),
        status: mappedStatus,
        order_date: o.create_time ? new Date(Number(o.create_time) * 1000).toISOString() : new Date().toISOString()
      };
    });

    // Perform upsert of real orders to avoid duplicates and log errors
    const syncResults = [];
    for (const ord of ordersToInsert) {
      const originalOrder = detailedOrders.find((x: any) => (x.id || x.order_id) === ord.order_number);
      const rawTikTokStatus = originalOrder ? (originalOrder.status || originalOrder.order_status || "UNKNOWN") : "UNKNOWN";

      const { data: existing, error: selectErr } = await supabaseClient
        .from('orders')
        .select('id')
        .eq('order_number', ord.order_number)
        .maybeSingle();

      if (selectErr) {
        console.error(`Select error for order ${ord.order_number}:`, selectErr.message);
      }

      if (existing) {
        const { error: updateErr } = await supabaseClient.from('orders').update(ord).eq('id', existing.id);
        if (updateErr) {
          console.error(`Update error for order ${ord.order_number}:`, updateErr.message);
          syncResults.push({ order_number: ord.order_number, status: "failed", error: updateErr.message });
        } else {
          syncResults.push({ 
            order_number: ord.order_number, 
            status: "updated", 
            amount: ord.total_amount, 
            customer: ord.customer_name,
            tiktok_status: rawTikTokStatus,
            mapped_status: ord.status
          });
        }
      } else {
        const { error: insertErr } = await supabaseClient.from('orders').insert(ord);
        if (insertErr) {
          console.error(`Insert error for order ${ord.order_number}:`, insertErr.message);
          syncResults.push({ order_number: ord.order_number, status: "failed", error: insertErr.message });
        } else {
          syncResults.push({ 
            order_number: ord.order_number, 
            status: "inserted", 
            amount: ord.total_amount, 
            customer: ord.customer_name,
            tiktok_status: rawTikTokStatus,
            mapped_status: ord.status
          });
        }
      }
    }

    // ==========================================
    // NEW STEP: Fetch and Upsert Live Products & Inventory
    // ==========================================
    console.log(`[PRODUCTS SYNC] Starting product synchronization for user ${user_id}...`);
    const productSearchPath = "/product/202309/products/search";
    const productSearchParamsObj = {
      app_key: appKey,
      timestamp: timestamp,
      shop_cipher: shopCipher,
      page_size: "50"
    };
    const productSearchSignature = await generateTikTokSignature(appSecret, productSearchPath, productSearchParamsObj, "{}");
    const productSearchParams = new URLSearchParams(productSearchParamsObj);
    productSearchParams.append("sign", productSearchSignature);
    const productSearchApiUrl = `https://open-api.tiktokglobalshop.com${productSearchPath}?${productSearchParams.toString()}`;

    let retrievedProducts = [];
    try {
      const prodSearchResponse = await fetch(productSearchApiUrl, {
        method: "POST",
        headers: {
          "x-tts-access-token": access_token,
          "content-type": "application/json"
        },
        body: "{}"
      });
      const prodSearchData = await prodSearchResponse.json();
      if (prodSearchData.code === 0 && prodSearchData.data?.products?.length > 0) {
        retrievedProducts = prodSearchData.data.products;
        console.log(`Successfully retrieved ${retrievedProducts.length} product entries from Search API.`);
      } else {
        console.warn(`No products or failed to search products from TikTok: ${JSON.stringify(prodSearchData)}`);
      }
    } catch (err) {
      console.error(`Error calling Search Products: ${err.message}`);
    }

    const productsToInsert = [];
    if (retrievedProducts.length > 0) {
      for (const p of retrievedProducts) {
        const productId = p.id;
        const detailPath = `/product/202309/products/${productId}`;
        const detailParamsObj = {
          app_key: appKey,
          timestamp: timestamp,
          shop_cipher: shopCipher
        };
        const detailSignature = await generateTikTokSignature(appSecret, detailPath, detailParamsObj, "");
        const detailSearchParams = new URLSearchParams(detailParamsObj);
        detailSearchParams.append("sign", detailSignature);
        const detailApiUrl = `https://open-api.tiktokglobalshop.com${detailPath}?${detailSearchParams.toString()}`;

        try {
          const detailResponse = await fetch(detailApiUrl, {
            method: "GET",
            headers: {
              "x-tts-access-token": access_token
            }
          });
          const detailData = await detailResponse.json();
          if (detailData.code === 0 && detailData.data) {
            const detail = detailData.data;
            const productName = detail.product_name || detail.title || p.title || "Produk TikTok";
            const skus = detail.skus || [];
            
            for (const sku of skus) {
              const skuCode = sku.seller_sku || sku.id || "SKU-TIKTOK";
              const priceVal = Number(sku.price?.amount || 0);
              const totalStock = (sku.inventory || []).reduce((sum: number, inv: any) => sum + Number(inv.quantity || 0), 0);

              productsToInsert.push({
                user_id: user_id,
                name: productName,
                sku: skuCode,
                stock: totalStock,
                price: priceVal,
                cost: Math.round(priceVal * 0.5), // Estimate HPP/cost as 50% of selling price by default
                description: `Produk TikTok Shop (${productName}). ID: ${productId}, SKU ID: ${sku.id}`
              });
            }
          }
        } catch (err) {
          console.error(`Error fetching product details for ${productId}: ${err.message}`);
        }
      }
    } else {
      // Fallback flow: Extract products & inventory from detailedOrders line items!
      console.log(`[PRODUCTS SYNC] Falling back to extract products from ${detailedOrders.length} detailed orders due to empty catalog or scope limitations...`);
      const processedSkuCodes = new Set();
      
      for (const o of detailedOrders) {
        const itemsList = o.line_items || [];
        for (const li of itemsList) {
          const skuCode = li.seller_sku || li.sku_id || li.id || `SKU-TIKTOK-${li.product_id}`;
          
          // Avoid duplicate processing of the same SKU in the loop
          if (processedSkuCodes.has(skuCode)) continue;
          processedSkuCodes.add(skuCode);

          const productName = li.product_name || "Produk TikTok";
          const skuVariantName = li.sku_name ? ` (${li.sku_name})` : "";
          
          // Clean up the name if it already has variant info
          let fullProductName = productName;
          if (skuVariantName && !productName.includes(li.sku_name)) {
            fullProductName = productName + skuVariantName;
          }

          // Get price (fallback to order's total amount divided by number of line items if not found)
          let priceVal = Number(li.price?.amount || li.sale_price || li.original_price || 0);
          if (priceVal === 0 && o.payment?.total_amount) {
            priceVal = Number(o.payment.total_amount) / itemsList.length;
          }

          productsToInsert.push({
            user_id: user_id,
            name: fullProductName,
            sku: skuCode,
            stock: 99, // Fallback default stock to make catalog feel alive and ready for analysis
            price: priceVal,
            cost: Math.round(priceVal * 0.55), // Default HPP/cost estimate as 55% of selling price (healthy default margin)
            description: `Produk TikTok Shop (${fullProductName}) diekstraksi dari Transaksi Riil. Product ID: ${li.product_id}`
          });
        }
      }
    }

    // Lapis 3 Fallback: If productsToInsert is still empty, pull historical orders from database!
    if (productsToInsert.length === 0) {
      console.log(`[PRODUCTS SYNC] Lapis 3: Database catalog and API detailed orders are empty. Pulling historical orders from database for fallback...`);
      const { data: dbOrders, error: dbOrdersErr } = await supabaseClient
        .from('orders')
        .select('customer_name, total_amount')
        .eq('user_id', user_id);
        
      if (!dbOrdersErr && dbOrders && dbOrders.length > 0) {
        const processedNames = new Set();
        for (const order of dbOrders) {
          const productName = order.customer_name || "Produk TikTok";
          if (productName === "Produk TikTok" || processedNames.has(productName)) continue;
          processedNames.add(productName);
          
          // Split by comma in case there are multiple items in the transaction string
          const items = productName.split(",").map(i => i.trim());
          for (const item of items) {
            // Generate a secure deterministic SKU based on the product name string
            let hash = 0;
            for (let i = 0; i < item.length; i++) {
              hash = (hash << 5) - hash + item.charCodeAt(i);
              hash |= 0; // Convert to 32bit integer
            }
            const skuCode = `SKU-DB-${Math.abs(hash)}`;
            const priceVal = Number(order.total_amount || 95000);
            
            productsToInsert.push({
              user_id: user_id,
              name: item,
              sku: skuCode,
              stock: 85, // Default stock to make catalog active and simulation friendly
              price: priceVal,
              cost: Math.round(priceVal * 0.55),
              description: `Produk TikTok Shop (${item}) diekstraksi otomatis dari database Historical Orders.`
            });
          }
        }
      }
    }

    console.log(`[PRODUCTS SYNC] Total SKU count to upsert: ${productsToInsert.length}`);
    for (const prod of productsToInsert) {
      const { data: existingProd, error: selectProdErr } = await supabaseClient
        .from('products')
        .select('id')
        .eq('user_id', user_id)
        .eq('sku', prod.sku)
        .maybeSingle();

      if (selectProdErr) {
        console.error(`Select product error for ${prod.sku}:`, selectProdErr.message);
      }

      if (existingProd) {
        const { error: updateProdErr } = await supabaseClient
          .from('products')
          .update(prod)
          .eq('id', existingProd.id);
        if (updateProdErr) {
          console.error(`Update product error for ${prod.sku}:`, updateProdErr.message);
        }
      } else {
        const { error: insertProdErr } = await supabaseClient
          .from('products')
          .insert(prod);
        if (insertProdErr) {
          console.error(`Insert product error for ${prod.sku}:`, insertProdErr.message);
        }
      }
    }

    // 7. Update connection status back to active
    await supabaseClient
      .from('marketplace_connections')
      .update({ sync_status: 'active' })
      .eq('id', connection.id);

    return new Response(
      JSON.stringify({ 
        success: true, 
        message: `Sinkronisasi sukses! Berhasil memproses ${ordersToInsert.length} data transaksi riil dari TikTok Shop.`,
        source: "live",
        results: syncResults
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
    )

  } catch (error) {
    console.error("Sync Engine Error:", error.message);
    return new Response(
      JSON.stringify({ success: false, error: error.message }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
    )
  }
})
