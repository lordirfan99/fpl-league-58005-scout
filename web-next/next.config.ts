import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "resources.premierleague.com" },
      { protocol: "https", hostname: "fantasy.premierleague.com" },
    ],
  },
};

export default nextConfig;
