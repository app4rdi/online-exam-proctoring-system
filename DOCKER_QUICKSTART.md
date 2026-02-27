# 🐳 Docker Quick Start

## ⚡ Chạy nhanh (Development)

```bash
# 1. Copy environment variables
cp .env.example .env

# 2. Start containers
docker-compose up -d

# 3. Xem logs
docker-compose logs -f app

# 4. Truy cập: http://localhost:8080
```

## 🚀 Production Deployment

```bash
# 1. Sửa .env với passwords mạnh
nano .env

# 2. Run production setup
docker-compose -f docker-compose.prod.yml up -d

# 3. Setup SSL (optional)
cd nginx && bash setup-ssl.sh

# 4. Restart nginx
docker-compose restart nginx
```

## 📊 Kiểm tra Status

```bash
# Container status
docker-compose ps

# Health check
curl http://localhost:8080/health

# Database check
docker-compose exec mysql mysqladmin -u root -p ping
```

## 🛑 Stop & Clean

```bash
# Stop containers
docker-compose down

# Stop + remove volumes (XÓA DATA!)
docker-compose down -v
```

## 📖 Chi tiết

Xem [DOCKER_GUIDE.md](DOCKER_GUIDE.md) để biết thêm chi tiết.

## ⚠️ Lưu ý

- Lần đầu build sẽ mất ~10-15 phút (download AI models)
- Cần ít nhất 4GB RAM
- Docker image size: ~3-4GB
- GPU không required nhưng khuyến nghị cho AI processing
