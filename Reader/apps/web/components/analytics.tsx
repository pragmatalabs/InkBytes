import Script from "next/script";

/**
 * Self-hosted Umami analytics loader (privacy-first, cookieless — no consent
 * banner needed). Server component: reads the config from runtime env, so the
 * website-id can be set in the Reader's container env AFTER Umami's first-run
 * (create the website in the dashboard → copy its UUID) with no image rebuild.
 *
 *   UMAMI_SRC         = https://analytics.inkbytes.org/script.js
 *   UMAMI_WEBSITE_ID  = <website UUID from the Umami dashboard>
 *
 * Renders nothing until BOTH are set — so it's inert before Umami is configured.
 */
export default function Analytics() {
  const src = process.env.UMAMI_SRC;
  const websiteId = process.env.UMAMI_WEBSITE_ID;
  if (!src || !websiteId) return null;
  return (
    <Script
      src={src}
      data-website-id={websiteId}
      strategy="afterInteractive"
      defer
    />
  );
}
