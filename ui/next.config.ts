import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  serverExternalPackages: ["@copilotkit/runtime"],
  // Note: Static export (output: "export") is not compatible with the current
  // architecture because /api/copilotkit is a required API route for CopilotKit
  // protocol translation to AG-UI protocol used by the Python backend.
  // See DEPLOYMENT.md for deployment options.
};

export default nextConfig;
