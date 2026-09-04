import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PremierIQ - Predict. Analyse. Simulate.",
  description: "Premier League analytics, match predictions and season simulations.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
