# Manual Test: Docker Stack

## Test Steps

### 8.1 Full Stack Startup
1. `docker compose up -d`
2. Wait for all services healthy (check with `docker compose ps`)
3. Verify: postgres (healthy), redis (healthy), qdrant-product (healthy), minio (healthy), backend (running)

### 8.2 Health Endpoints
1. `curl http://localhost:8000/health` → `{"status":"ok",...}`
2. `curl http://localhost:8000/` → `{"name":"MycoAI Retrieval Backend","docs":"/docs",...}`
3. `curl http://localhost:9000/minio/health/live` → `200 OK`

### 8.3 Database Migrations
1. `docker compose run --rm --profile migrate db-migrate`
2. Expect: "Running upgrade -> head" or "No migrations to apply"
3. Check PostgreSQL has expected tables: `docker compose exec postgres psql -U mycoai -d mycoai -c "\dt"`

### 8.4 Celery Worker
1. Check worker logs: `docker compose logs celery-worker`
2. Expect: "celery@... ready" message
3. Worker connects to Redis broker without errors

### 8.5 Frontend Access
1. `curl http://localhost:80` → returns HTML (React app)
2. Browser: `http://localhost` loads login page

### 8.6 Volume Persistence
1. Upload an image (see 04-image-upload-segmentation.md)
2. `docker compose down`
3. `docker compose up -d`
4. Verify uploaded image still accessible via API

### 8.7 Resource Limits
1. `docker stats --no-stream` 
2. Verify memory usage within configured limits

### 8.8 Clean Shutdown
1. `docker compose down`
2. Verify all containers stopped: `docker compose ps -a`
3. Volumes preserved: `docker volume ls | grep mycoai`
