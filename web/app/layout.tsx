import type { Metadata } from "next";
import Link from "next/link";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Cattail & Rye vendor picks",
  description: "Who to call for each event, and the package that fits the budget",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <header className="border-b border-line bg-surface/90 backdrop-blur">
          <nav className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4 px-4 py-3.5">
            <Link href="/" className="font-semibold tracking-tight">
              Cattail &amp; Rye <span className="font-normal text-muted">vendor picks</span>
            </Link>
            <Link href="/runs" className="text-sm text-muted underline underline-offset-4 hover:text-foreground">
              How this was checked
            </Link>
          </nav>
        </header>
        <div className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">{children}</div>
      </body>
    </html>
  );
}
