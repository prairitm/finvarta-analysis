FROM node:20-alpine AS build

WORKDIR /app/frontend

# Ensure Vite can talk to the backend container by default
ARG VITE_API_URL=http://backend:8000
ENV VITE_API_URL=${VITE_API_URL}

# Install dependencies first for better caching
COPY frontend/package*.json ./
RUN npm ci

# Copy the rest of the source
COPY frontend/. .

RUN npm run build

FROM nginx:1.27-alpine AS runtime

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/frontend/dist /usr/share/nginx/html

EXPOSE 80
