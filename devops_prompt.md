ELK Monitoring Specification for Containerized Application
Objective
Implement a monitoring and alerting system using the ELK Stack (Elasticsearch, Logstash, Kibana) with Redis as a buffer to collect, process, and visualize logs and metrics from a containerized application consisting of frontend (Vite/Nginx), backend (FastAPI), Redis, and Celery. The setup must start locally, mimic a separate host using Docker networks, and be extensible to a separate host in production. Follow an iterative approach: start with backend logs, add Celery, frontend, and metrics, create Kibana dashboards, set alerts, and plan for production.
Current Setup

Docker Compose Version: 3.8
Services:
Redis: redis:alpine, port 6379, volume redis_data, used as Celery broker and result backend.
Backend: FastAPI with Uvicorn, port 8000, built from ./Dockerfile, mounts ./backend:/app/backend and ./data/temp:/app/backend/temp, depends on Redis.
Worker: Celery worker, built from ./Dockerfile, runs python -m celery -A backend.celery_app.celery_app worker -l info --pool=solo, mounts same volumes as backend, depends on Redis.
Frontend: Vite dev server (development), port 5173, built from ./frontend/Dockerfile (development stage), mounts ./frontend:/app, depends on backend.
Nginx: Production web server, port 80, built from nginx/Dockerfile, serves frontend and proxies backend, depends on backend.


Environment: Local development, all services run in Docker containers.
Logs:
Backend: FastAPI logs (e.g., INFO: 172.26.0.1:52546 - "GET /dashboard/reports-summary HTTP/1.1" 200 OK), httpx logs, custom logs (e.g., logger.error("Failed to connect to Supabase")), print() statements.
Celery: Task execution logs (e.g., task started, failed) via stdout/stderr.
Frontend: Vite logs (development), client-side JavaScript errors (to be sent to backend).
Nginx: Access/error logs (e.g., /var/log/nginx/access.log, /var/log/nginx/error.log).
Redis: Server logs (e.g., connection issues, errors).



Requirements

Architecture: Use ELK Stack with Redis as a buffer (Option 2 from recommendations).
Deploy Elasticsearch, Logstash, Kibana, and a dedicated logging Redis in separate containers.
Use Filebeat (sidecar containers per service) to collect logs and send to logging Redis.
Use Metricbeat to collect system, Docker, and Redis metrics.
Mimic a separate host locally using Docker networks (app-network, elk-network).


Log Collection:
Collect all logs from:
Backend: stdout/stderr (FastAPI, httpx, logger.error, print()).
Celery: stdout/stderr (task logs).
Frontend: Vite logs (development), client-side errors via backend API endpoint.
Nginx: Access/error logs from /var/log/nginx/*.log.
Redis: Server logs from stdout/stderr or log files.


Use Filebeat sidecar containers for each service (backend, worker, frontend, nginx, redis) to collect logs from Docker’s JSON log files (/var/lib/docker/containers/*/*.log) or specific log files.


Metrics Collection:
Use Metricbeat to collect:
System metrics: CPU, memory, disk, network usage per container.
Docker metrics: Container health, resource usage.
Redis metrics: Memory usage, connected clients, command latency, cache hit/miss ratios.
Backend metrics (optional): If exposed via a /metrics endpoint (e.g., Prometheus format).




Processing:
Logging Redis buffers logs from Filebeat.
Logstash pulls logs from Redis, parses them (e.g., extract fields from FastAPI logs, handle multi-line logger.error stack traces), and sends to Elasticsearch.


Visualization and Alerting:
Use Kibana to create dashboards for:
Backend: Request rates, HTTP status codes, error rates.
Celery: Task success/failure rates, queue lengths.
Frontend: Vite logs, client-side error rates.
Nginx: Request rates, error codes, response times.
Redis: Memory usage, cache hit ratios.
System: Container CPU/memory usage.


Set Kibana alerts for:
Backend errors (e.g., logger.error, HTTP 500s).
Celery task failures.
Nginx errors (e.g., 500s, 404s).
Redis memory usage exceeding thresholds.
Container crashes or high resource usage.




Local Development:
Run all components locally using two Docker Compose files:
docker-compose-app.yml: For app services (frontend, backend, redis, worker, nginx, Filebeat, Metricbeat).
docker-compose-elk.yml: For ELK services (elasticsearch, logstash, kibana, logging-redis).


Use Docker networks (app-network, elk-network) for isolation.
Limit ELK resources (e.g., 2GB RAM, 1 CPU for Elasticsearch) to avoid overloading the local machine.


Iterative Development:
Phase 1: Set up ELK locally, collect backend logs only, verify pipeline.
Phase 2: Add Celery, frontend, Nginx, and Redis log collection.
Phase 3: Add Metricbeat for metrics.
Phase 4: Create Kibana dashboards and alerts.
Phase 5: Plan for production (separate host or managed service like Elastic Cloud).


Production Plan:
Deploy ELK services (elasticsearch, logstash, kibana, logging-redis) on a separate host (e.g., AWS EC2, GCP VM).
Update Filebeat/Metricbeat to send data to the remote logging Redis.
Consider managed ELK (e.g., Elastic Cloud) if maintenance is a concern.



Implementation Details

Docker Compose Structure:

docker-compose-app.yml:
Services: frontend, backend, redis, worker, nginx, filebeat-backend, filebeat-worker, filebeat-frontend, filebeat-nginx, filebeat-redis, metricbeat.
Networks: app-network, elk-network (external).
Mount /var/lib/docker/containers for Filebeat to access Docker logs.
Mount ./data/temp for backend/worker as in current setup.


docker-compose-elk.yml:
Services: elasticsearch, logstash, kibana, logging-redis.
Network: elk-network.
Expose ports: 9200 (Elasticsearch), 5601 (Kibana), 6379 (logging-redis).
Use single-node Elasticsearch (discovery.type=single-node) for local development.




Filebeat Configuration:

Use sidecar Filebeat containers for each service (backend, worker, frontend, nginx, redis).
Configure filebeat.yml for each:
Input: Docker logs (type: container, paths: /var/lib/docker/containers/*/*.log) or specific files (e.g., /var/log/nginx/*.log for Nginx).
Output: Logging Redis (output.redis.hosts: ["logging-redis:6379"]).
Enable Docker autodiscovery for dynamic container detection.
Use multiline settings for multi-line logs (e.g., stack traces).




Metricbeat Configuration:

Run a single Metricbeat container in docker-compose-app.yml.
Configure metricbeat.yml to collect:
System metrics (CPU, memory, disk, network).
Docker metrics (container health, resource usage).
Redis metrics (via Redis module).
Backend metrics (if exposed via /metrics endpoint).


Output to Elasticsearch (output.elasticsearch.hosts: ["elasticsearch:9200"]).


Logstash Configuration:

Create logstash.conf in docker-compose-elk.yml volume:
Input: Redis (input { redis { host => "logging-redis" port => 6379 } }).
Filter: Parse logs (e.g., FastAPI HTTP logs, httpx logs, Celery task logs, Nginx access/error logs).
Output: Elasticsearch (output { elasticsearch { hosts => ["elasticsearch:9200"] } }).




Logging Redis:

Dedicated Redis container (logging-redis) in docker-compose-elk.yml.
Use redis:7 image, enable persistence (AOF or RDB).
Separate from app’s Redis to avoid interference.


Application Code:

No changes required for basic log collection (Filebeat collects stdout/stderr).
Optional: Add JSON logging in backend/Celery for easier Logstash parsing:
Use python-json-logger for structured logs (e.g., {"message": "Failed to connect", "error": "details"}).


Frontend: Send client-side JavaScript errors to backend /log endpoint for logging.


Kibana:

Access at http://localhost:5601.
Create dashboards for:
Backend: HTTP request rates, status codes, error rates (logger.error, httpx errors).
Celery: Task success/failure rates, queue lengths.
Nginx: Request rates, error codes, response times.
Redis: Memory usage, cache hit/miss ratios.
System: Container CPU/memory usage.


Set alerts for:
Backend: logger.error messages, HTTP 500s.
Celery: Task failures.
Nginx: 500/404 errors.
Redis: High memory usage.
System: Container crashes, high CPU/memory.





Constraints

Local Resources: Limit ELK to 4GB RAM total (e.g., 2GB for Elasticsearch, 1GB each for Logstash/Kibana) to avoid overloading the local machine.
Security: Disable X-Pack security for local development (xpack.security.enabled=false). Enable in production.
Ports: Ensure no conflicts (e.g., 9200, 5601, 6379 for logging-redis distinct from app’s Redis).
Docker Compose Version: Use 3.8, matching current setup.
No Code Changes: Minimize changes to backend/frontend code unless adding JSON logging or metrics endpoints.

Deliverables

docker-compose-app.yml:
Extend current Docker Compose with Filebeat sidecar containers (filebeat-backend, filebeat-worker, filebeat-frontend, filebeat-nginx, filebeat-redis) and metricbeat.
Add app-network and elk-network (external).


docker-compose-elk.yml:
Define elasticsearch, logstash, kibana, logging-redis.
Include elk-network.


Filebeat Configs:
filebeat-backend.yml, filebeat-worker.yml, filebeat-frontend.yml, filebeat-nginx.yml, filebeat-redis.yml for respective services.


Metricbeat Config:
metricbeat.yml for system, Docker, and Redis metrics.


Logstash Config:
logstash.conf for Redis input, log parsing, and Elasticsearch output.


README:
Instructions to run locally:
Create elk-network: docker network create elk-network.
Start ELK: docker-compose -f docker-compose-elk.yml up -d.
Start app: docker-compose -f docker-compose-app.yml up -d.
Access Kibana: http://localhost:5601.


Steps for production deployment (separate host or managed service).



Iterative Plan

Phase 1: Implement docker-compose-elk.yml and docker-compose-app.yml with filebeat-backend to collect backend logs. Verify logs in Kibana.
Phase 2: Add filebeat-worker, filebeat-frontend, filebeat-nginx, filebeat-redis for Celery, frontend, Nginx, and Redis logs.
Phase 3: Add metricbeat for system, Docker, and Redis metrics.
Phase 4: Create Kibana dashboards and alerts as specified.
Phase 5: Document production deployment steps (separate host or Elastic Cloud).

