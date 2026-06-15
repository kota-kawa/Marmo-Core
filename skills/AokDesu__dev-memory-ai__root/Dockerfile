# memory-dev — CLI container
# Useful for running memory-dev watch or memory-dev mcp as a persistent service.
# Mount your repo at /repo and set DATABASE_URL to a persistent volume.
#
# Example:
#   docker build -t memory-dev .
#   docker run -it --rm \
#     -v /path/to/your/repo:/repo \
#     -v memory-dev-data:/data \
#     -e GOOGLE_API_KEY=your_key \
#     -e DATABASE_URL=file:/data/dev.db \
#     memory-dev mcp

# Stage 1: install dependencies
FROM node:20-alpine AS deps
WORKDIR /app

COPY package.json package-lock.json ./
COPY prisma ./prisma/

RUN npm ci --legacy-peer-deps

# Stage 2: runtime image
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

# Non-root user
RUN addgroup --system --gid 1001 nodejs \
 && adduser  --system --uid 1001 memorydev

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Generate Prisma client
RUN npx prisma generate

# Persistent data directory for SQLite
RUN mkdir -p /data && chown memorydev:nodejs /data

USER memorydev

ENV DATABASE_URL="file:/data/dev.db"

ENTRYPOINT ["node", "cli.js"]
CMD ["--help"]
