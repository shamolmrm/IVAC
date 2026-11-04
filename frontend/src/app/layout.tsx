import type { Metadata, Viewport } from "next";
import { Inter, Noto_Sans_Bengali } from "next/font/google";
import "./globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });
const bengali = Noto_Sans_Bengali({ variable: "--font-bengali", subsets: ["bengali"] });

export const metadata: Metadata = {
  metadataBase: new URL("https://ivac.supersoftltd.com"),
  title: { default: "Visa Assistant", template: "%s · Visa Assistant" },
  description:
    "Document management, data verification and application preparation for Indian visa applicants in Bangladesh.",
  // Not public yet: keep out of search engines until launch.
  robots: { index: false, follow: false },
};

export const viewport: Viewport = { width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="bn">
      <body className={`${inter.variable} ${bengali.variable} min-h-screen font-sans antialiased`}>
        {children}
      </body>
    </html>
  );
}
