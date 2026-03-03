import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "@tabler/core/dist/css/tabler.min.css";
import "./globals.css";
import TablerInit from "@/components/TablerInit";
import { AppProvider } from "@/context/AppContext";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({ 
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Agent Nexus Dashboard",
  description: "Built with Next.js and Tabler",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`} data-bs-theme="dark">
        <TablerInit />
        <AppProvider>
          {children}
        </AppProvider>
      </body>
    </html>
  );
}
