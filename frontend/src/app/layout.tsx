import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Travel Booking Optimizer",
  description: "Optimize live travel bookings across cash, points, transfers, and offers.",
  icons: {
    icon: "/brand/travel-booking-optimizer-mark.svg",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
