/**
 * Next.js instrumentation hook — runs once when the server process starts.
 *
 * When HTTP_PROXY is set (e.g. on FPT network), we configure undici's global
 * dispatcher so that ALL Node.js `fetch()` calls — including Clerk's JWK fetch
 * inside the Node.js-runtime middleware — are routed through the proxy.
 *
 * This has no effect when HTTP_PROXY is unset (Railway / direct internet).
 *
 * NOTE: `eval('import(...)')` is intentional — it makes the dynamic import
 * opaque to Turbopack/webpack so the bundler does not try to statically resolve
 * 'undici' at compile time (it is a runtime dep, not in the app's bundle).
 */
export async function register() {
  const proxy = process.env.HTTP_PROXY || process.env.HTTPS_PROXY;
  if (proxy) {
    // eslint-disable-next-line no-eval
    const { setGlobalDispatcher, ProxyAgent } = await (eval(
      'import("undici")'
    ) as Promise<typeof import("undici")>);
    setGlobalDispatcher(new ProxyAgent(proxy));
    console.info(`[instrumentation] HTTP proxy configured: ${proxy}`);
  }
}
