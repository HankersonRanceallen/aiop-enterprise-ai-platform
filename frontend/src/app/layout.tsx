import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AIOP — Enterprise AI Platform",
  description: "Cloud-native RAG & agent platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 antialiased">{children}</body>
    </html>
  );
}
