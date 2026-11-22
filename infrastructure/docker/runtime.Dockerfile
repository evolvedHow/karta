# Pinned base image and npm dependencies. No floating tags.
FROM node:22.19.0-alpine

ENV NODE_ENV=production
WORKDIR /app

COPY apps/runtime/package.json apps/runtime/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY apps/runtime/tsconfig.json apps/runtime/tsconfig.build.json ./
COPY apps/runtime/src ./src
RUN npm run build && npm prune --omit=dev

EXPOSE 8101
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
  CMD ["node", "-e", "fetch('http://127.0.0.1:8101/health').then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"]

CMD ["node", "dist/index.js"]
