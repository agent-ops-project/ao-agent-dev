# Frontend Dockerfile

FROM node:18-slim AS build
ARG VITE_APP_WS_URL
ENV VITE_APP_WS_URL=$VITE_APP_WS_URL
ARG VITE_API_BASE
ENV VITE_API_BASE=$VITE_API_BASE
WORKDIR /app
COPY src/user_interfaces/ /app/
WORKDIR /app/web_app/client
RUN npm install && npm run build

FROM nginx:alpine

# Install certbot for SSL certificates
RUN apk add --no-cache certbot

# Copy built frontend
COPY --from=build /app/web_app/client/dist /usr/share/nginx/html

# Copy nginx SSL configuration
COPY docker/nginx.conf /docker-entrypoint.d/nginx-ssl.conf

# Copy startup script
COPY docker/start-nginx.sh /start-nginx.sh
RUN chmod +x /start-nginx.sh

# Create necessary directories
RUN mkdir -p /var/www/certbot /etc/letsencrypt

EXPOSE 80 443

CMD ["/start-nginx.sh"]
