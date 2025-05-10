


## Local Development with ELK Stack

### Prerequisites

1.  Docker and Docker Compose installed.
2.  Sufficient resources (recommend at least 8GB RAM, 4GB allocated to ELK).
3.  Ensure ports 9200, 5601, 5044, 9600, 6380 (for logging-redis) are free on your host, or adjust port mappings in `docker-compose-elk.yml`.
    Also ensure application ports (8000, 5173, 80, 6379 for app-redis) are managed as per your setup.

### Setup Steps

1.  **Create the shared Docker network for ELK:**
    This network allows the application containers (specifically Filebeat/Metricbeat) to communicate with the ELK stack services.
    ```bash
    docker network create elk-network
    ```

2.  **Start the ELK Stack:**
    This will start Elasticsearch, Logstash, Kibana, and the `logging-redis` instance.
    ```bash
    docker-compose -f docker-compose-elk.yml up -d
    ```
    Wait for a few minutes for all services to initialize. You can check their status with `docker-compose -f docker-compose-elk.yml ps` and logs with `docker-compose -f docker-compose-elk.yml logs -f <service_name>`.
    Elasticsearch can take a moment to become healthy.

3.  **Start the Application Stack with Beats:**
    This will start your application services (backend, worker, etc.) along with their corresponding Filebeat instances and Metricbeat.
    ```bash
    docker-compose -f docker-compose-app.yml up -d --build
    ```
    The `--build` flag is recommended for the first run or when Dockerfiles change.

### Accessing Services

*   **Kibana (View Logs & Metrics):** [http://localhost:5601](http://localhost:5601)
    *   Go to "Management" -> "Stack Management" -> "Kibana" -> "Index Patterns".
    *   Create index patterns like `app-*-logs-*` (for logs from Logstash) and `metricbeat-*` (for metrics). Use `@timestamp` as the time field.
    *   Explore logs in "Discover" and metrics in pre-built Metricbeat dashboards or create your own.
*   **Application Frontend (Vite Dev):** [http://localhost:5173](http://localhost:5173) (if `frontend` service is up)
*   **Application Backend API:** [http://localhost:8000](http://localhost:8000)
*   **Application Nginx (Prod-like):** [http://localhost:80](http://localhost:80) (if `nginx` service is up)
*   **Elasticsearch API:** [http://localhost:9200](http://localhost:9200)

### Iterative Development Phases (as per your plan)

*   **Phase 1 (Backend Logs):**
    *   Ensure `docker-compose-elk.yml` is running.
    *   In `docker-compose-app.yml`, you can comment out other app services and their filebeat containers if you want to test *only* backend logs initially.
        For example, run: `docker-compose -f docker-compose-app.yml up -d backend filebeat-backend`
    *   Verify backend logs appear in Kibana under an index like `app-backend-logs-*`.
*   **Phase 2 (Add Celery, Frontend, Nginx, App Redis logs):**
    *   Uncomment/add the respective services and their `filebeat-*` containers in `docker-compose-app.yml`.
    *   Run `docker-compose -f docker-compose-app.yml up -d --build`.
    *   Verify logs from these services in Kibana.
*   **Phase 3 (Add Metricbeat):**
    *   Ensure `metricbeat` service is defined and running in `docker-compose-app.yml`.
    *   Verify metrics in Kibana (index pattern `metricbeat-*`). Check system, Docker, and Redis metrics.
*   **Phase 4 (Kibana Dashboards & Alerts):**
    *   Create dashboards in Kibana for visualization.
    *   Set up alerts based on queries (e.g., high error rates, task failures).
*   **Phase 5 (Plan for Production):**
    *   See "Production Considerations" below.

### Stopping the Environment

1.  **Stop Application Stack:**
    ```bash
    docker-compose -f docker-compose-app.yml down -v # -v removes volumes including Filebeat/Metricbeat data
    ```
2.  **Stop ELK Stack:**
    ```bash
    docker-compose -f docker-compose-elk.yml down -v # -v removes ELK data volumes
    ```
3.  **Remove the network (optional):**
    ```bash
    docker network rm elk-network
    ```

## Production Considerations

*   **Resource Allocation:** Adjust Java heap sizes (`ES_JAVA_OPTS`, `LS_JAVA_OPTS`) and Kibana's `NODE_OPTIONS` based on your production server's capacity and expected load.
*   **Security (X-Pack):**
    *   Enable X-Pack security for Elasticsearch, Kibana, and Beats in production. This involves setting up users, roles, and TLS encryption.
    *   Update configurations (Elasticsearch, Kibana, Logstash, Filebeat, Metricbeat) with credentials and TLS settings.
*   **Persistence:** Ensure all data volumes (`elasticsearch_data`, `logging_redis_data`, Logstash persistent queue if used) are robustly managed (e.g., backed by reliable storage, regular backups).
*   **Scalability:**
    *   Elasticsearch can be scaled to a multi-node cluster.
    *   Logstash can have multiple instances.
    *   Consider a more robust message queue than a single Redis instance for buffering logs at scale (e.g., Kafka, or a clustered Redis).
*   **Deployment Strategy:**
    *   **Separate Host(s):** Deploy the ELK stack (from `docker-compose-elk.yml`) on one or more dedicated servers. Update Filebeat/Metricbeat outputs in `docker-compose-app.yml` (or their respective YAML configs) to point to the remote Logstash/Elasticsearch/logging-Redis endpoints.
    *   **Managed Services:** Consider using managed services like Elastic Cloud, AWS Elasticsearch Service, etc., to offload ELK stack management. Filebeat/Metricbeat would then be configured to send data to these cloud endpoints.
*   **Log Rotation & Retention:** Configure index lifecycle management (ILM) in Elasticsearch to manage log retention (e.g., delete old indices, move to cold storage).
*   **Nginx Logging:** For production, you might want Nginx to log to files within its container, and have Filebeat read those files directly (by sharing a volume between Nginx and its Filebeat sidecar). This can be more robust than relying solely on Docker's stdout/stderr logging for Nginx in some scenarios.
*   **GeoIP Database for Logstash:** For the `geoip` filter to work, you'll need to configure Logstash to download and use a GeoIP database.

This setup provides a solid foundation for your ELK monitoring. Remember to iterate and adjust configurations as you gain more experience with the stack and understand your application's logging patterns better!