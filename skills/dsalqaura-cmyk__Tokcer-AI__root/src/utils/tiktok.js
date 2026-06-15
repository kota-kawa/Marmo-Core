/**
 * Generate TikTok Shop API Signature using native Web Crypto API
 * @param {string} appSecret 
 * @param {string} path 
 * @param {Object} params - Query parameters
 * @param {string} body - JSON string of request body (if any)
 * @returns {Promise<string>}
 */
async function generateTikTokSignature(appSecret, path, params, body = "") {
  // 1. Sort keys alphabetically
  const keys = Object.keys(params).sort();
  
  // 2. Concatenate key-value pairs
  let paramString = "";
  for (const key of keys) {
    if (key !== 'sign' && key !== 'access_token') {
      paramString += key + params[key];
    }
  }

  // 3. Construct base string: secret + path + sorted_params + body + secret
  const baseString = appSecret + path + paramString + body + appSecret;

  // 4. HMAC-SHA256
  const encoder = new TextEncoder();
  const keyData = encoder.encode(appSecret);
  const messageData = encoder.encode(baseString);

  const cryptoKey = await window.crypto.subtle.importKey(
    'raw',
    keyData,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );

  const signature = await window.crypto.subtle.sign(
    'HMAC',
    cryptoKey,
    messageData
  );

  return Array.from(new Uint8Array(signature))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

/**
 * Generate TikTok Authorization URL
 * @param {string} serviceId - Also known as App ID
 * @param {string} state - Random string for security
 * @returns {string}
 */
export const getTikTokAuthUrl = (serviceId, state = "tokcer_secure_state") => {
  const baseUrl = "https://services.tiktokshop.com/open/authorize";
  
  // [TARJO FIX]: Sandikan origin domain ke dalam state agar kita bisa mengalihkan balik dari Staging ke Production
  let encodedState = state;
  try {
    encodedState = btoa(JSON.stringify({
      origin: window.location.origin,
      custom_state: state
    }));
  } catch (err) {
    console.error("Failed to encode state:", err);
  }
  
  return `${baseUrl}?service_id=${serviceId}&state=${encodedState}`;
};
