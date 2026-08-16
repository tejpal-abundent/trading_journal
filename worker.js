/**
 * Cloudflare Worker for tradingjournal.pages.dev.
 *
 * Serves two SPAs from the same origin:
 *   /tej-capital/*  →  frontend/dist/tej-capital/*   (fallback: /tej-capital/index.html)
 *   everything else →  frontend/dist/*               (fallback: /index.html)
 *
 * Real static files are served by the assets binding directly (Worker never runs).
 * The Worker only fires on 404s and picks the right SPA index to hand back.
 */
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    // Try the exact request first. If a matching asset exists, this is the response.
    const primary = await env.ASSETS.fetch(request);
    if (primary.status !== 404) return primary;

    // 404 → SPA fallback based on which app owns the URL.
    const fallbackPath = path.startsWith("/tej-capital/")
      ? "/tej-capital/index.html"
      : "/index.html";
    return env.ASSETS.fetch(new Request(new URL(fallbackPath, url.origin), request));
  },
};
