# Docker Deployment Guide

## 📦 Yêu cầu

- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB RAM (tối thiểu), 8GB RAM (khuyến nghị)
- 10GB disk space (cho images và data)

## 🚀 Quick Start

### 1. Cấu hình Environment Variables

```bash
# Copy file .env mẫu
cp .env.example .env

# Chỉnh sửa các biến môi trường
nano .env
```

Nội dung `.env`:
```env
# Database
MYSQL_ROOT_PASSWORD=your-secure-root-password
DB_USER=proctoruser
DB_PASSWORD=your-secure-db-password
DB_NAME=proctor

# Flask
SECRET_KEY=your-very-long-and-random-secret-key-here
FLASK_ENV=production
```

### 2. Build và chạy containers

**Production mode:**
```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Xem logs
docker-compose logs -f app
```

**Development mode (với hot reload):**
```bash
# Chạy với file dev
docker-compose -f docker-compose.dev.yml up -d

# Logs
docker-compose -f docker-compose.dev.yml logs -f
```

### 3. Truy cập ứng dụng

- **Application**: http://localhost:8080
- **MySQL**: localhost:3306 (hoặc 3307 trong dev mode)
- **Redis**: localhost:6379

### 4. Khởi tạo database (nếu cần)

Database sẽ tự động được import từ `database/proctor.sql`. Nếu cần import thủ công:

```bash
# Exec vào MySQL container
docker exec -it proctor-mysql bash

# Trong container
mysql -u root -p proctor < /docker-entrypoint-initdb.d/init.sql
```

## 🔧 Quản lý Containers

### Xem status
```bash
docker-compose ps
```

### Restart services
```bash
# Restart tất cả
docker-compose restart

# Restart app only
docker-compose restart app
```

### Xem logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f app
docker-compose logs -f mysql
```

### Stop containers
```bash
# Stop nhưng keep data
docker-compose stop

# Stop và remove containers (data vẫn giữ trong volumes)
docker-compose down

# Remove containers VÀ volumes (XÓA DATA)
docker-compose down -v
```

## 🗄️ Backup & Restore

### Backup Database
```bash
# Backup database
docker exec proctor-mysql mysqldump -u root -p proctor > backup_$(date +%Y%m%d).sql

# Backup với docker-compose
docker-compose exec mysql mysqldump -u root -p${MYSQL_ROOT_PASSWORD} proctor > backup.sql
```

### Restore Database
```bash
# Restore from backup
docker exec -i proctor-mysql mysql -u root -p proctor < backup.sql
```

### Backup Volumes
```bash
# Backup MySQL data volume
docker run --rm -v proctor_mysql_data:/data -v $(pwd):/backup ubuntu tar czf /backup/mysql_backup.tar.gz /data

# Backup violation screenshots
tar czf screenshots_backup.tar.gz violation_screenshots/
```

## 🔍 Troubleshooting

### Container không start được
```bash
# Check logs
docker-compose logs app

# Check MySQL connection
docker-compose exec app ping mysql
```

### Database connection issues
```bash
# Verify MySQL is ready
docker-compose exec mysql mysqladmin -u root -p ping

# Check database exists
docker-compose exec mysql mysql -u root -p -e "SHOW DATABASES;"
```

### Port conflicts
Nếu port 8080 hoặc 3306 đã được dùng:
```yaml
# Sửa trong docker-compose.yml
services:
  app:
    ports:
      - "8081:8080"  # Đổi port ngoài
  mysql:
    ports:
      - "3307:3306"
```

### App crash do AI libraries
```bash
# Check memory
docker stats

# Increase memory limit
docker-compose.yml:
  app:
    deploy:
      resources:
        limits:
          memory: 4G
```

### Rebuild image sau khi thay đổi code
```bash
# Rebuild without cache
docker-compose build --no-cache app

# Hoặc rebuild và restart
docker-compose up -d --build
```

## 🚀 Production Deployment

### 1. Cấu hình Nginx reverse proxy

```nginx
# /etc/nginx/sites-available/proctor
server {
    listen 80;
    server_name proctor.example.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /var/www/proctor/static;
        expires 30d;
    }
}
```

### 2. SSL với Let's Encrypt
```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d proctor.example.com
```

### 3. Auto-restart on boot
```bash
# Docker containers tự động restart
docker-compose.yml:
  services:
    app:
      restart: unless-stopped
```

### 4. Monitoring
```bash
# Add Prometheus + Grafana
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

## 📊 Performance Tuning

### MySQL Optimization
```yaml
mysql:
  command: 
    - --max_connections=1000
    - --innodb_buffer_pool_size=2G
    - --query_cache_size=0
```

### App Optimization
```yaml
app:
  deploy:
    replicas: 3  # Scale to 3 instances
    resources:
      limits:
        cpus: '2'
        memory: 4G
```

### Redis Caching
Uncomment Redis service và cấu hình Flask để dùng Redis:
```python
# config.py
CACHE_TYPE = "redis"
CACHE_REDIS_URL = "redis://redis:6379/0"
```

## 🐳 Docker Commands Cheat Sheet

```bash
# List containers
docker ps

# Stop all containers
docker stop $(docker ps -aq)

# Remove all containers
docker rm $(docker ps -aq)

# Remove all images
docker rmi $(docker images -q)

# Clean up system
docker system prune -a --volumes

# View logs last 100 lines
docker-compose logs --tail=100 app

# Execute command in container
docker-compose exec app bash

# View container resource usage
docker stats

# Inspect network
docker network inspect proctor_proctor-network
```

## 🔐 Security Best Practices

1. **Đổi passwords mặc định** trong `.env`
2. **Không commit `.env`** vào Git
3. **Use secrets** cho sensitive data:
   ```bash
   echo "secret-password" | docker secret create db_password -
   ```
4. **Limit container resources** để tránh DOS
5. **Regular updates**: 
   ```bash
   docker-compose pull
   docker-compose up -d
   ```
6. **Firewall rules**: Chỉ expose port cần thiết
7. **SSL/TLS**: Luôn dùng HTTPS trong production

## 📝 Notes

- **AI Models**: DeepFace và YOLO models sẽ được download lần đầu chạy (~1GB)
- **GPU Support**: Nếu có GPU, dùng `nvidia-docker` để tăng performance
- **Development**: Dùng `docker-compose.dev.yml` với hot reload
- **Testing**: Tạo `docker-compose.test.yml` cho CI/CD
- **Scaling**: Dùng Docker Swarm hoặc Kubernetes cho production scale

## 🐛 Debug Mode

```bash
# Chạy app với debug logs
docker-compose exec app python -c "import logging; logging.basicConfig(level='DEBUG')"

# Exec vào container
docker-compose exec app bash

# Check Python packages
docker-compose exec app pip list

# Test database connection
docker-compose exec app python -c "import mysql.connector; print('OK')"
```

---

**Cần hỗ trợ?** Xem logs với `docker-compose logs -f` hoặc open issue trên GitHub.
