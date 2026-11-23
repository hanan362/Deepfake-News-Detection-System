# Build from the project root:  docker build -f deployment/docker/frontend.Dockerfile -t dfnd-frontend .
FROM node:22-alpine AS build
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npx vite build

FROM nginx:1.27-alpine
COPY deployment/nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
