#!/bin/bash
# ============================================
# Let's Encrypt SSL Certificate Setup
# ============================================
# Usage: ./init-ssl.sh yourdomain.com

set -e

DOMAIN="${1:-yourdomain.com}"
EMAIL="${2:-admin@yourdomain.com}"
NGINX_CONF="/etc/nginx/sites-available/ats-platform"

if [ "$DOMAIN" = "yourdomain.com" ]; then
    echo "⚠️  WARNING: Using placeholder domain 'yourdomain.com'"
    echo "Please provide your actual domain:"
    echo "  ./init-ssl.sh yourdomain.com admin@youremail.com"
    exit 1
fi

echo "🔒 Setting up SSL for: $DOMAIN"
echo "📧 Contact email: $EMAIL"

# ============================================
# Step 1: Install Certbot
# ============================================
echo "📦 Installing Certbot..."
if command -v apt-get &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y certbot python3-certbot-nginx
elif command -v yum &> /dev/null; then
    sudo yum install -y certbot python3-certbot-nginx
elif command -v dnf &> /dev/null; then
    sudo sudo dnf install -y certbot python3-certbot-nginx
else
    echo "❌ Could not detect package manager. Please install Certbot manually."
    exit 1
fi

# ============================================
# Step 2: Create webroot for challenges
# ============================================
echo "📁 Creating webroot directory..."
sudo mkdir -p /var/www/certbot
sudo mkdir -p /var/www/uploads
sudo chown -R www-data:www-data /var/www/uploads
sudo chmod 755 /var/www/uploads

# ============================================
# Step 3: Create temporary nginx config for certbot
# ============================================
echo "⚙️  Creating temporary nginx configuration..."
sudo tee /etc/nginx/sites-available/ats-platform-temp << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 200 "Let's Encrypt verification pending...";
        add_header Content-Type text/plain;
    }
}
EOF

# Enable the temporary config
sudo ln -sf /etc/nginx/sites-available/ats-platform-temp /etc/nginx/sites-enabled/ats-platform
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# ============================================
# Step 4: Obtain certificate
# ============================================
echo "🔐 Obtaining SSL certificate from Let's Encrypt..."
sudo certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --domain="$DOMAIN" \
    --domain="www.$DOMAIN" \
    --agree-tos \
    --email "$EMAIL" \
    --non-interactive \
    --rsa-key-size 4096

if [ $? -ne 0 ]; then
    echo "❌ Failed to obtain SSL certificate"
    exit 1
fi

# ============================================
# Step 5: Deploy full nginx configuration
# ============================================
echo "🚀 Deploying full nginx configuration..."

# Update nginx.conf with actual domain
sed "s/yourdomain.com/$DOMAIN/g" nginx.conf > /tmp/ats-platform-nginx.conf
sudo cp /tmp/ats-platform-nginx.conf "$NGINX_CONF"

# Enable the main config
sudo ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/ats-platform
sudo rm -f /etc/nginx/sites-enabled/ats-platform-temp

# Test and reload nginx
sudo nginx -t
if [ $? -eq 0 ]; then
    sudo systemctl reload nginx
    echo "✅ Nginx configuration reloaded successfully"
else
    echo "❌ Nginx configuration test failed"
    exit 1
fi

# ============================================
# Step 6: Setup auto-renewal
# ============================================
echo "⏰ Setting up auto-renewal..."

# Test renewal
sudo certbot renew --dry-run
if [ $? -eq 0 ]; then
    echo "✅ Certificate renewal test passed"
else
    echo "⚠️  Certificate renewal test failed - check manually"
fi

# Add cron job for auto-renewal
CRON_JOB="0 3 * * * /usr/bin/certbot renew --quiet --deploy-hook 'systemctl reload nginx'"
if ! sudo crontab -l | grep -q "certbot renew"; then
    (sudo crontab -l 2>/dev/null; echo "$CRON_JOB") | sudo crontab -
    echo "✅ Auto-renewal cron job added"
fi

# ============================================
# Step 7: SSL Verification
# ============================================
echo ""
echo "=========================================="
echo "🔒 SSL Setup Complete!"
echo "=========================================="
echo ""
echo "Domain: $DOMAIN"
echo "Certificate: /etc/letsencrypt/live/$DOMAIN/"
echo "Renewal: Daily at 3:00 AM via cron"
echo ""
echo "Test your SSL:"
echo "  https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN"
echo ""
echo "Verify certificate:"
echo "  openssl s_client -connect $DOMAIN:443 -servername $DOMAIN < /dev/null"
echo ""
