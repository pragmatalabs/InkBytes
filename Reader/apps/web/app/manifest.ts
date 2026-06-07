import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "InkBytes",
    short_name: "InkBytes",
    description:
      "One elegant page per event. Multi-source, ad-free news — synthesized from dozens of outlets.",
    start_url: "/",
    display: "standalone",
    background_color: "#fafaf9",
    theme_color: "#1a1a2e",
    orientation: "portrait-primary",
    categories: ["news"],
    icons: [
      {
        src: "/icon.svg",
        sizes: "any",
        type: "image/svg+xml",
        purpose: "any",
      },
      {
        src: "/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "maskable",
      },
      {
        src: "/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
    shortcuts: [
      {
        name: "Entities",
        url: "/entities",
        description: "Browse entity co-occurrence graph",
      },
    ],
  };
}
