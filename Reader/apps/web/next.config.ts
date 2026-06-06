import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",   // enables Docker-friendly standalone build
};

export default nextConfig;
