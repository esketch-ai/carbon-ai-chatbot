/** @type {import('next').NextConfig} */
const nextConfig = {
  // Docker 배포를 위한 standalone 출력
  output: 'standalone',

  experimental: {
    serverActions: {
      bodySizeLimit: "10mb",
    },
  },

  // 이미지 최적화 설정
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
  },
};

export default nextConfig;
