import type { Metadata } from "next";
import {
  Fraunces,
  Geist,
  JetBrains_Mono,
  Noto_Sans_Devanagari,
  Tiro_Devanagari_Hindi,
} from "next/font/google";

import { Providers } from "./providers";
import "./globals.css";

/* Three fonts, three jobs (DESIGN.md §3):
   story = narrative · ui = chrome · data = proof.
   The two Devanagari faces are fallbacks only — Fraunces, Geist and
   JetBrains Mono have no Devanagari glyphs, and the seed story is Hindi-first. */
const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  display: "swap",
});

const geist = Geist({
  variable: "--font-geist",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin"],
  display: "swap",
});

const tiroDevanagari = Tiro_Devanagari_Hindi({
  variable: "--font-tiro-devanagari",
  subsets: ["devanagari", "latin"],
  weight: "400",
  display: "swap",
});

const notoDevanagari = Noto_Sans_Devanagari({
  variable: "--font-noto-devanagari",
  subsets: ["devanagari", "latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "CANON · a playable branch",
  description:
    "Pick a character, play forward through choices sourced from fan-fiction — every character remembers only what they actually learned.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${fraunces.variable} ${geist.variable} ${jetbrainsMono.variable} ${tiroDevanagari.variable} ${notoDevanagari.variable} h-full`}
    >
      <body className="min-h-full">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
