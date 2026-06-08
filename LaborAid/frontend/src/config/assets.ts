/**
 * 静态资源路径 — 源文件在仓库根目录 resources/
 * 由 Vite 同步至 frontend/public/ 后通过 / 路径访问
 */
export const ASSETS = {
  logo: '/laboraid-logo.png',
  logoWhite: '/laboraid-logo-white.png',
  logoNobg: '/laboraid-logo-nobg.png',
  favicon: '/favicon.png',
} as const;
