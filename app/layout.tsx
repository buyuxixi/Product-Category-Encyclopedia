import type { Metadata } from "next";
import { headers } from "next/headers";
import "./globals.css";

const siteTitle = "产品品类百科 | Category Intelligence";
const siteDescription = "从原理、参数到真实使用场景，理解产品背后的选择逻辑。";

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const host = requestHeaders.get("x-forwarded-host") ?? requestHeaders.get("host");
  const protocol = requestHeaders.get("x-forwarded-proto") ?? "https";
  const origin = host ? `${protocol}://${host}` : "https://product-category-encyclopedia.example";

  return {
    title: siteTitle,
    description: siteDescription,
    metadataBase: new URL(origin),
    openGraph: {
      title: siteTitle,
      description: siteDescription,
      url: origin,
      siteName: "产品品类百科",
      locale: "zh_CN",
      type: "website",
      images: [{ url: "/og.png", width: 1200, height: 630, alt: "产品品类百科" }],
    },
    twitter: {
      card: "summary_large_image",
      title: siteTitle,
      description: siteDescription,
      images: ["/og.png"],
    },
  };
}

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
