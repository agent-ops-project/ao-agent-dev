#!/bin/bash
set -e

# Install certbot if not present
if ! command -v certbot &> /dev/null; then
    apk add --no-cache certbot
fi

# Function to obtain SSL certificate
obtain_cert() {
    echo "Obtaining SSL certificate for agops-project.com..."
    
    # Start nginx with HTTP-only config for certificate verification
    cat > /etc/nginx/conf.d/default.conf << 'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name agops-project.com www.agops-project.com;

    root /usr/share/nginx/html;
    index index.html index.htm;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
EOF

    # Create certbot webroot directory
    mkdir -p /var/www/certbot

    # Start nginx for certificate verification
    nginx -g "daemon off;" &
    NGINX_PID=$!
    sleep 2

    # Obtain certificate
    certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email admin@agops-project.com \
        --agree-tos \
        --no-eff-email \
        --non-interactive \
        -d agops-project.com \
        -d www.agops-project.com

    # Stop temporary nginx
    kill $NGINX_PID
    wait $NGINX_PID 2>/dev/null || true
}

# Check if certificates exist
if [ ! -f "/etc/letsencrypt/live/agops-project.com/fullchain.pem" ]; then
    echo "SSL certificates not found. Obtaining new certificates..."
    obtain_cert
else
    echo "SSL certificates found."
fi

# Copy the SSL-enabled nginx config
cp /docker-entrypoint.d/nginx-ssl.conf /etc/nginx/conf.d/default.conf

# Start nginx with SSL configuration
exec nginx -g "daemon off;"