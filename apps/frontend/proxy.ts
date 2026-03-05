import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

// proxy.ts always runs on the Node.js runtime (Next.js 16 convention).
// The undici global dispatcher configured in instrumentation.ts ensures
// Clerk's fetch calls are routed through the HTTP proxy on FPT network.
const isProtectedRoute = createRouteMatcher(["/history(.*)"]);

export default clerkMiddleware(async (auth, request) => {
  if (isProtectedRoute(request)) {
    await auth.protect();
  }
});

export const config = {
  matcher: [
    // Skip Next.js internals and all static files
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    // Always run for API routes
    "/(api|trpc)(.*)",
  ],
};
