import type { Metadata } from "next";
import { AppAlerts } from "@/components/AppAlerts";
import { PastelBackdrop } from "@/components/pastel";
import "./globals.css";

export const metadata: Metadata = {
  title: "Atelier — AI Career Coach",
  description: "One AI that knows your career. Coaching, resumes, and interviews on a single profile.",
  icons: {
    icon: [{ url: "/icon.svg", type: "image/svg+xml" }],
    apple: [{ url: "/icon.svg" }],
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,650;1,9..144,500&family=Outfit:wght@300;400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="font-sans antialiased">
        <PastelBackdrop>
          {children}
          <AppAlerts />
        </PastelBackdrop>
      </body>
    </html>
  );
}
