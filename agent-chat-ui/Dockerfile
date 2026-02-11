# =========================================
# Stage 1: Dependencies
# =========================================
FROM node:20-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# pnpm 설치
RUN corepack enable && corepack prepare pnpm@latest --activate

# 의존성 파일 복사
COPY package.json pnpm-lock.yaml ./

# 의존성 설치
RUN pnpm install --frozen-lockfile

# =========================================
# Stage 2: Builder
# =========================================
FROM node:20-alpine AS builder
WORKDIR /app

RUN corepack enable && corepack prepare pnpm@latest --activate

# 의존성 복사
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# 환경 변수 설정 (빌드 시) - HuggingFace Spaces backend
ENV NEXT_PUBLIC_API_URL="https://esketch-carbon-ai-chatbot.hf.space"
ENV NEXT_PUBLIC_ASSISTANT_ID="agent"

# Next.js 빌드
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm build

# =========================================
# Stage 3: Runner
# =========================================
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# 보안: non-root 사용자
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# 필요한 파일만 복사
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json

# standalone 출력 설정이 있을 경우
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

# HuggingFace Spaces uses port 7860
EXPOSE 7860

ENV PORT=7860
ENV HOSTNAME="0.0.0.0"

# Backend API URL (HuggingFace Spaces)
ENV NEXT_PUBLIC_API_URL="https://esketch-carbon-ai-chatbot.hf.space"
ENV NEXT_PUBLIC_ASSISTANT_ID="agent"

CMD ["node", "server.js"]
