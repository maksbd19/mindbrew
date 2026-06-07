FROM node:20-alpine AS builder

WORKDIR /app

ARG API_URL=http://api:8000
ENV API_URL=$API_URL

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production \
    API_URL=http://api:8000 \
    NEXT_PUBLIC_API_URL=/api

COPY --from=builder /app/package.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next

EXPOSE 3000

CMD ["npm", "start", "--", "-H", "0.0.0.0", "-p", "3000"]
