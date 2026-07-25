import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /**
   * REQUIREMENTS.md §12 requires zero visible debug chrome during a dry run,
   * and the demo is driven from `npm run dev`. Next's dev indicator badge sits
   * in the bottom-left corner and would be on the projector, so it is off.
   */
  devIndicators: false,
};

export default nextConfig;
