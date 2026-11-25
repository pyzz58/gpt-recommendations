import type { Metadata } from "next";

import { OfflineBanner } from "@/components/offline-banner";

import "./globals.css";

export const metadata: Metadata = {
  title: "医疗一人项目｜本地工作台",
  description: "一人医药公司、AI 岗位团队与现实外包协作的本地研发工作台。",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>
        <OfflineBanner />
        {children}
      </body>
    </html>
  );
}
