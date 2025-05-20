Monitoring System Implementation Prompt
Objective
Build a standalone monitoring system for a Docker Compose-based application running on a separate host, without backend code changes. The system will monitor uptime, collect logs (FastAPI, Celery, Nginx, Redis, frontend), measure performance, monitor frontend errors/load times, and send email alerts. It will run as a new Docker Compose stack (version 3.8) on a monitoring host, using open-source tools. Logs will be accessed via NFS mounts and a Promtail agent on the application host. The frontend logger will be resilient to ensure the frontend works if the monitoring stack is down.
Application Setup (Separate Host)
The application runs on a separate host with Docker Compose (version 3.8) services:

redis: Redis (port 6379, not public).
backend: FastAPI (port 8000, proxied via Nginx).
worker: Celery worker.
frontend: Vite frontend (served by Nginx).
nginx: Nginx (port 80, proxies /api/*, serves frontend).
Nginx logs: ./data/logs/nginx:/var/log/nginx.
Application URL: http://application:80 (placeholder).

The application’s docker-compose.yml will be modified to mount FastAPI/Celery/Redis logs and add a Promtail service.
Requirements

Uptime Monitoring:

Check http://application:80 every 1 minute.
“Up” means HTTP 200 status.
Use Prometheus with Blackbox Exporter.


Log Collection and Analysis:

Collect logs from:
FastAPI/Celery (/app/backend/logs/app.log, mounted to ./data/logs/app).
Nginx access/error (./data/logs/nginx).
Redis (/data/redis.log, mounted to ./data/logs/redis).
Frontend (via JS logger to Loki).


Aggregate using Grafana Loki.
Analyze for:
Errors (HTTP 4xx/5xx, Python exceptions, JS errors).
Slow requests (>1 second).
HTTP methods (GET, POST), endpoints.


Store logs for 7 days.
Visualize in Grafana.


Backend Performance Monitoring:

Measure request response times (P50, P95, P99) and TTFB via Blackbox probes to http://application:80.
Parse Nginx logs for additional metrics.
Store metrics for 7 days.
Use Prometheus with Blackbox Exporter.


Frontend Performance Monitoring:

Track page load times (DOMContentLoaded, full load) and JS errors.
Inject <script src="http://monitoring-host:3000/logger.js"> in frontend/index.html.
Logger sends to http://monitoring-host:3100/loki/api/v1/push, with try-catch and reachability checks.
Store logs in Loki.


Resource Monitoring:

Monitor monitoring host container resources (CPU, memory, disk) using cAdvisor.
Store metrics in Prometheus.


Alerts:

Email alerts for:
Website down (HTTP ≠ 200 or no response for 2 checks).
High error rates (>5% 4xx/5xx).
Slow requests (P95 latency >2 seconds).


Use Alertmanager with placeholder SMTP (smtp.example.com:587, user:pass).


Visualization:

Grafana dashboards for:
Uptime.
Performance (latency, errors).
Logs (errors, slow requests, JS errors).
Frontend performance.
Monitoring host resources.


Persist Grafana data.


Constraints:

Open-source tools only.
New Docker Compose stack for monitoring.
Store logs/metrics for 7 days.
No backend changes.
Resilient frontend logger.
NFS mounts for logs.



Implementation Steps

Application Docker Compose Changes:

Update docker-compose.yml:
Add log volumes:
backend: ./data/logs/app:/app/backend/logs.
worker: ./data/logs/app:/app/backend/logs.
redis: ./data/logs/redis:/data.


Configure loki logging driver for all services (loki_url: http://monitoring-host:3100/loki/api/v1/push).
Add Promtail service:
Image: grafana/promtail.
Scrape ./data/logs/app, ./data/logs/redis, ./data/logs/nginx.
Forward to http://monitoring-host:3100/loki/api/v1/push.




Ensure FastAPI/Celery log to /app/backend/logs/app.log, Redis to /data/redis.log.


Frontend Change:

Inject <script src="http://monitoring-host:3000/logger.js"> in frontend/index.html (async load).
Serve logger.js from Grafana or Nginx with:
Page load times (Navigation Timing API).
Errors (window.onerror, addEventListener('error')).
POST to http://monitoring-host:3100/loki/api/v1/push with JSON { "streams": [{ "stream": { "app": "frontend" }, "values": [[<timestamp>, <log>]] }] }.
Try-catch and reachability checks (e.g., timeout 2s).
Fallback to console if monitoring host is down.




Monitoring Docker Compose Setup:

Create docker-compose.yml (version 3.8) with:
Prometheus:
Image: prom/prometheus.
Port: 9090.
Scrape Blackbox Exporter, cAdvisor.
Store data for 7 days.
Volume: prometheus_data.


Blackbox Exporter:
Image: prom/blackbox-exporter.
Port: 9115.
Probe http://application:80 every 1 minute.


cAdvisor:
Image: gcr.io/cadvisor/cadvisor.
Port: 8080.
Monitor monitoring host containers.


Grafana:
Image: grafana/grafana.
Port: 3000.
Configure Prometheus, Loki data sources.
Serve logger.js (or use Nginx service).
Create dashboards.
Volume: grafana_data.


Loki:
Image: grafana/loki.
Port: 3100.
Receive logs at /loki/api/v1/push.
Store logs for 7 days.
Volume: loki_data.


Promtail:
Image: grafana/promtail.
Scrape NFS mounts: /mnt/nginx-logs, /mnt/app-logs, /mnt/redis-logs.
Forward to Loki.


Alertmanager:
Image: prom/alertmanager.
Port: 9093.
Configure placeholder SMTP.
Define alert rules.






Configure Logging:

Application: loki driver sends logs to http://monitoring-host:3100/loki/api/v1/push.
Promtail (application host): Scrapes ./data/logs/*, forwards to Loki.
Promtail (monitoring host): Scrapes NFS mounts.
Monitoring services: Use loki driver.


NFS Mounts:

Mount on monitoring host:
/mnt/nginx-logs (from application’s ./data/logs/nginx).
/mnt/app-logs (from ./data/logs/app).
/mnt/redis-logs (from ./data/logs/redis).


Document NFS setup (placeholder: nfs-server:/data/logs).


Persist Data:

Volumes: prometheus_data, grafana_data, loki_data.


Security:

Restrict Grafana, Prometheus, Alertmanager (basic auth).
Use environment variables for sensitive configs (e.g., Loki URL).



Deliverables

Updated application docker-compose.yml.
Monitoring docker-compose.yml.
Configuration files:
prometheus.yml for scrape targets.
alertmanager.yml with placeholder SMTP.
Grafana provisioning for data sources, dashboards.
Loki config for 7-day retention.
Promtail configs (application and monitoring hosts).
logger.js for frontend.


Frontend change: Add script tag to frontend/index.html.
Documentation:
Access Grafana, Prometheus (URLs, credentials).
Update SMTP, application URL, NFS mounts.
Customize log filters.



Notes

Placeholder URL: http://application:80.
NFS mounts: /mnt/nginx-logs, /mnt/app-logs, /mnt/redis-logs (from nfs-server:/data/logs).
Log paths: FastAPI/Celery (/app/backend/logs/app.log), Redis (/data/redis.log).
Frontend logger: Resilient with try-catch, 2s timeout, console fallback.
Placeholder SMTP: smtp.example.com:587, user:pass.
Generic log filters (HTTP methods/endpoints).
Test Blackbox probes, Promtail, frontend logger.
Verify Grafana dashboards.

Example Dashboard Layout

Uptime: Uptime percentage, probe success/failure.
Performance: Latency, TTFB, error rates.
Logs: Error counts, slow requests, JS errors.
Frontend: Page load times, JS error counts.
Resources: Monitoring host CPU/memory/disk.

Start building. Ask for application URL, NFS details, or log paths if needed.
