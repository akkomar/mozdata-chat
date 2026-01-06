import type { Metadata } from "next";

import { AuthProvider } from "@/components/AuthProvider";
import "./globals.css";
import "@copilotkit/react-ui/styles.css";

export const metadata: Metadata = {
  title: "Mozdata Assistant",
  description: "Ask questions about Mozilla data documentation, BigQuery datasets, Glean SDK, and more.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={"antialiased"}>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
