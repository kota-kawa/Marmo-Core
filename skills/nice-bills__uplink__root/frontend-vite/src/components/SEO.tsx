/**
 * SEO - Sets document title and meta tags
 * Using react-helmet-async for proper SSR support
 */

import { useEffect } from 'react';

interface SEOProps {
    title?: string;
    description?: string;
    image?: string;
    url?: string;
    type?: 'website' | 'article';
}

const DEFAULT_TITLE = 'Genesis | Agent Fundraising Platform';
const DEFAULT_DESCRIPTION = 'Launch and fund AI agent campaigns. The decentralized platform for the next generation of autonomous agents.';
const DEFAULT_IMAGE = '/og-image.png';

export function SEO({
    title,
    description = DEFAULT_DESCRIPTION,
    image = DEFAULT_IMAGE,
    url,
    type = 'website',
}: SEOProps) {
    const pageTitle = title ? `${title} | Genesis` : DEFAULT_TITLE;
    const pageUrl = url || (typeof window !== 'undefined' ? window.location.href : '');
    const pageImage = image.startsWith('http') ? image : `${pageUrl}${image}`;

    useEffect(() => {
        // Set document title
        document.title = pageTitle;

        // Helper to update meta tags
        const updateMeta = (name: string, content: string, isProperty = false) => {
            const selector = isProperty ? `meta[property="${name}"]` : `meta[name="${name}"]`;
            let meta = document.querySelector(selector) as HTMLMetaElement | null;

            if (!meta) {
                meta = document.createElement('meta');
                if (isProperty) {
                    meta.setAttribute('property', name);
                } else {
                    meta.setAttribute('name', name);
                }
                document.head.appendChild(meta);
            }
            meta.content = content;
        };

        // Standard meta tags
        updateMeta('description', description);

        // Open Graph tags
        updateMeta('og:title', pageTitle, true);
        updateMeta('og:description', description, true);
        updateMeta('og:image', pageImage, true);
        updateMeta('og:url', pageUrl, true);
        updateMeta('og:type', type, true);

        // Twitter Card tags
        updateMeta('twitter:card', 'summary_large_image');
        updateMeta('twitter:title', pageTitle);
        updateMeta('twitter:description', description);
        updateMeta('twitter:image', pageImage);
    }, [pageTitle, description, pageImage, pageUrl, type]);

    // This component doesn't render anything visible
    return null;
}
