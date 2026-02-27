# Nginx SSL Configuration

## Tạo Self-Signed Certificate (Development)

```bash
# Tạo thư mục ssl
mkdir -p nginx/ssl

# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem \
  -subj "/C=VN/ST=HCM/L=HoChiMinh/O=Proctor/CN=localhost"
```

## Let's Encrypt (Production)

Sử dụng certbot để generate SSL certificate miễn phí:

```bash
# Install certbot
sudo apt-get install certbot

# Get certificate (thay your-domain.com bằng domain thật)
sudo certbot certonly --webroot \
  -w /var/www/certbot \
  -d your-domain.com \
  -d www.your-domain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/key.pem

# Restart nginx
docker-compose restart nginx
```

## Auto-renewal

```bash
# Add cronjob
sudo crontab -e

# Add line (renew every 2 months)
0 0 1 */2 * certbot renew --quiet && docker-compose restart nginx
```
