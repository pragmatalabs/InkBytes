# InkBytes Reader — Next.js 16 production image
# Multi-stage: build → standalone runtime (minimal image, ~200MB)

FROM node:20-alpine AS builder
WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# next.config.ts must have output:'standalone' for this to work
RUN npm run build

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Next.js standalone output
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static     ./.next/static
COPY --from=builder /app/public           ./public

EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD node -e "const h=require('http');h.get('http://localhost:3000/',r=>{process.exit(r.statusCode<500?0:1)}).on('error',()=>process.exit(1))" || exit 1

CMD ["node", "server.js"]
