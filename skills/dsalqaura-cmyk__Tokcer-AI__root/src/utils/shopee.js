/**
 * Generate Shopee API V2 Signature using native Web Crypto API
 * @param {string} partnerKey 
 * @param {string} baseString 
 * @returns {Promise<string>}
 */
async function generateHmacSha256(partnerKey, baseString) {
  const encoder = new TextEncoder();
  const keyData = encoder.encode(partnerKey);
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
 * Generate Shopee Authorization URL
 * @param {string} partnerId 
 * @param {string} partnerKey 
 * @param {string} redirectUrl 
 * @returns {Promise<string>}
 */
export const getShopeeAuthUrl = async (partnerId, partnerKey, redirectUrl) => {
  const path = "/api/v2/shop/auth_partner";
  const timestamp = Math.floor(Date.now() / 1000);
  const baseString = `${partnerId}${path}${timestamp}`;
  
  const sign = await generateHmacSha256(partnerKey, baseString);
  
  const baseUrl = "https://partner.shopeemobile.com";
  return `${baseUrl}${path}?partner_id=${partnerId}&timestamp=${timestamp}&sign=${sign}&redirect=${encodeURIComponent(redirectUrl)}`;
};
