input {
    redis {
    host => "logging-redis"
    port => 6379
    data_type => "list"
    key => "backend_logs" # Start with just one to test
    codec => "json"
    threads => 1
    batch_count => 50
  }
  redis {
    host => "logging-redis"
    port => 6379
    data_type => "list"
    key => "worker_logs"
    codec => "json"
    # add_field => { "log_type" => "worker" }
    threads => 2
    batch_count => 125
  }
  redis {
    host => "logging-redis"
    port => 6379
    data_type => "list"
    key => "frontend_logs"
    codec => "json"
    # add_field => { "log_type" => "frontend" }
    threads => 1
    batch_count => 125
  }
  redis {
    host => "logging-redis"
    port => 6379
    data_type => "list"
    key => "nginx_logs"
    codec => "json"
    # add_field => { "log_type" => "nginx" }
    threads => 1
    batch_count => 125
  }
  redis {
    host => "logging-redis"
    port => 6379
    data_type => "list"
    key => "app_redis_logs"
    codec => "json"
    # add_field => { "log_type" => "app_redis" }
    threads => 1
    batch_count => 50
  }
}

filter {
  # Common processing: try to parse message if it's a JSON string
  if [message] =~ /^\{.*\}$/ {
    json {
      source => "message"
      target => "log_payload" # Store parsed JSON here
      # remove_field => ["message"] # Optionally remove original if successfully parsed
    }
  }

  # Add ECS service name from Filebeat field
  if [log_source_service] {
    mutate {
      rename => { "log_source_service" => "[service][name]" }
    }
  }


  # --- Backend (FastAPI/Uvicorn) Log Processing ---
  if [service][name] == "backend" or [service][name] == "worker" {
    # Attempt to parse standard Uvicorn access logs
    grok {
      match => { "message" => "%{LOGLEVEL:log.level_original}\s*:\s+(?:%{IPORHOST:source.ip}:%{NUMBER:source.port:int}\s+-\s+)?\"%{WORD:http.request.method}\s+%{NOTSPACE:url.path}\s+HTTP/%{NUMBER:http.version}\"\s+%{NUMBER:http.response.status_code:int}(\s+%{GREEDYDATA:http.response.status_phrase})?" }
      tag_on_failure => ["_grokparsefailure_uvicorn_access"]
      # Keep original message for now
    }

    # If it's a Python stack trace (Filebeat should have handled multiline)
    if "Traceback (most recent call last):" in [message] {
      mutate {
        add_tag => ["stacktrace", "python_error"]
      }
      # You might want to use the dissect filter for simpler structured logs
    }
  }

  # --- Nginx Log Processing ---
  if [service][name] == "nginx" {
    # Nginx logs are usually sent by Docker's json-file driver, message field contains the raw log line.
    # Default Nginx format: $remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"
    grok {
      match => { "message" => "%{IPORHOST:source.ip} - %{DATA:user.name} \[%{HTTPDATE:nginx.time}\] \"%{WORD:http.request.method} %{DATA:url.original} HTTP/%{NUMBER:http.version}\" %{NUMBER:http.response.status_code:int} %{NUMBER:http.response.body.bytes:int} \"%{DATA:http.request.referrer}\" \"%{DATA:user_agent.original}\"" }
      tag_on_failure => ["_grokparsefailure_nginx_access"]
    }
    if !("_grokparsefailure_nginx_access" in [tags]) {
      date {
        match => [ "nginx.time", "dd/MMM/yyyy:HH:mm:ss Z" ]
        target => "@timestamp" # Overwrite with Nginx log time
        remove_field => ["nginx.time"]
      }
      useragent {
        source => "user_agent.original"
        target => "user_agent"
      }
      geoip { # Requires GeoIP database setup in Logstash
         source => "source.ip"
         target => "source.geo"
      }
    }
  }

  # --- Celery Log Processing (if specific patterns exist beyond backend/worker generic handling) ---
  if [service][name] == "worker" {
    # Example: [2023-10-27 10:00:00,123: INFO/MainProcess] Task backend.tasks.my_task[uuid] succeeded in 0.123s: None
    grok {
      match => { "message" => "\[%{TIMESTAMP_ISO8601:celery.timestamp}: %{LOGLEVEL:log.level_original}/%{DATA:celery.process_name}\]\s+Task\s+%{NOTSPACE:celery.task_name}\[%{UUID:celery.task_id}\]\s+%{WORD:celery.task_status}(\s+in\s+%{NUMBER:celery.task_duration:float}s)?:\s+%{GREEDYDATA:celery.task_result}"}
      tag_on_failure => ["_grokparsefailure_celery"]
    }
    if !("_grokparsefailure_celery" in [tags]) {
       date {
         match => [ "celery.timestamp", "YYYY-MM-dd HH:mm:ss,SSS" ] # Adjust format if needed
         target => "@timestamp"
       }
    }
  }

  # Convert log levels to ECS compliant `log.level`
  # This is a simplified example; you might need more robust mapping
  if [log.level_original] {
    translate {
      field => "[log.level_original]"
      destination => "[log][level]"
      dictionary => {
        "INFO" => "info"
        "SUCCESS" => "info" # For Celery
        "WARN" => "warn"
        "WARNING" => "warn"
        "ERROR" => "error"
        "CRITICAL" => "fatal"
        "DEBUG" => "debug"
      }
      fallback => "unknown"
      # remove_field => ["[log.level_original]"] # Optional
    }
  }

  # Remove Filebeat's agent fields if not needed after processing
  # mutate {
  #   remove_field => ["agent"] # Contains version, type, etc.
  # }
}

output {
  stdout {
    codec => rubydebug
  }
  # Keep Elasticsearch output commented for now
  # elasticsearch {
  #   hosts => ["http://elasticsearch:9200"]
  #   index => "app-test-%{+YYYY.MM.dd}"
  # }
} 