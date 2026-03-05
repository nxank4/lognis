/**
 * Next.js instrumentation hook — runs once when the server process starts.
 *
 * When HTTP_PROXY is set (e.g. on FPT network), we configure undici's global
 * dispatcher so that ALL Node.js `fetch()` calls — including Clerk's JWK fetch
 * inside the Node.js-runtime middleware — are routed through the proxy.
 *
 * This has no effect when HTTP_PROXY is unset (Railway / direct internet).
 *
 * Guarded by NEXT_RUNTIME === 'nodejs' so this code never runs (or is
 * evaluated) in the Edge runtime, where dynamic imports via eval are forbidden.
 */
export async function register() {
  if (process.env.NEXT_RUNTIME !== "nodejs") return;

  const proxy = process.env.HTTP_PROXY || process.env.HTTPS_PROXY;
  if (proxy) {
    const { setGlobalDispatcher, ProxyAgent } = await import("undici");
    setGlobalDispatcher(new ProxyAgent(proxy));
    console.info(`[instrumentation] HTTP proxy configured: ${proxy}`);
  }
}
