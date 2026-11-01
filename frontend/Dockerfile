# --- build stage ---
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build

# --- serve stage ---
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template

# BACKEND_HOST はバックエンドコンテナの名前解決先(例: backend.local や backendのIP)。
# 実行時に -e BACKEND_HOST=... で上書きする。
ENV BACKEND_HOST=backend
ENV BACKEND_PORT=8000

EXPOSE 80
