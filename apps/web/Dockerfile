FROM node:24-alpine AS dependencies
WORKDIR /srv/web
COPY package.json package-lock.json ./
RUN npm ci
FROM node:24-alpine AS builder
WORKDIR /srv/web
COPY --from=dependencies /srv/web/node_modules ./node_modules
COPY . .
ARG NEXT_API_ORIGIN=http://api:8000
ENV NEXT_API_ORIGIN=$NEXT_API_ORIGIN
RUN npm run build
FROM node:24-alpine AS runner
WORKDIR /srv/web
ARG NEXT_API_ORIGIN=http://api:8000
ENV NODE_ENV=production NEXT_API_ORIGIN=$NEXT_API_ORIGIN
COPY --from=dependencies /srv/web/node_modules ./node_modules
COPY --from=builder /srv/web/.next ./.next
COPY --from=builder /srv/web/package.json ./package.json
COPY --from=builder /srv/web/next.config.ts ./next.config.ts
USER node
EXPOSE 3000
CMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0"]
