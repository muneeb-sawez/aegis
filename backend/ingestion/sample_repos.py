"""AEGIS Bundled Sample Repositories for Offline & Demonstration Testing.

Provides verified, realistic multi-tier microservice architectures for immediate
testing of repository ingestion, PREDICT risk analysis, and MONITOR health checks.
"""

from __future__ import annotations

SAMPLE_REPOSITORIES = {
    "shop-sphere/ecommerce-core": {
        "name": "ShopSphere E-Commerce Core",
        "slug": "shop-sphere/ecommerce-core",
        "description": "Enterprise cloud-native e-commerce topology with 11 microservices and external payment gateway.",
        "services_count": 11,
        "primary_language": "TypeScript / Go / Python",
        "yaml": """version: '3.8'

services:
  frontend:
    image: shopsphere/frontend:v2.4
    ports:
      - "80:8080"
    environment:
      - API_GATEWAY_URL=http://api-gateway:8000
    depends_on:
      - api-gateway

  api-gateway:
    image: shopsphere/gateway:v1.9
    ports:
      - "8000:8000"
    depends_on:
      - checkoutservice
      - cartservice
      - productcatalogservice

  checkoutservice:
    image: shopsphere/checkout:v3.1
    environment:
      - PAYMENT_SERVICE_ADDR=paymentservice:50051
      - CART_SERVICE_ADDR=cartservice:7070
      - SHIPPING_SERVICE_ADDR=shippingservice:50052
      - EMAIL_SERVICE_ADDR=emailservice:8080
      - CURRENCY_SERVICE_ADDR=currencyservice:7000
    depends_on:
      - paymentservice
      - cartservice
      - shippingservice
      - emailservice
      - currencyservice

  paymentservice:
    image: shopsphere/payment:v2.0
    environment:
      - DATABASE_URL=postgres://payment_usr:secret@postgres-payment:5432/payments
      - STRIPE_API_ENDPOINT=https://api.stripe.com/v1
    depends_on:
      - postgres-payment

  cartservice:
    image: shopsphere/cart:v1.8
    environment:
      - REDIS_ADDR=redis-cart:6379
    depends_on:
      - redis-cart

  productcatalogservice:
    image: shopsphere/catalog:v2.1
    ports:
      - "3550:3550"

  currencyservice:
    image: shopsphere/currency:v1.2
    ports:
      - "7000:7000"

  shippingservice:
    image: shopsphere/shipping:v1.5
    ports:
      - "50052:50052"

  emailservice:
    image: shopsphere/email:v1.1
    ports:
      - "8081:8080"

  postgres-payment:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=payments
      - POSTGRES_USER=payment_usr
      - POSTGRES_PASSWORD=secret
    ports:
      - "5432:5432"

  redis-cart:
    image: redis:7-alpine
    ports:
      - "6379:6379"
""",
    },
    "fintech-nexus/ledger-core": {
        "name": "Fintech Nexus Ledger & Settlement",
        "slug": "fintech-nexus/ledger-core",
        "description": "High-throughput financial ledger, transaction router, fraud detection, and PostgreSQL audit vault.",
        "services_count": 7,
        "primary_language": "Rust / Java / Go",
        "yaml": """version: '3.8'

services:
  edge-gateway:
    image: nexus/edge-router:v4.0
    ports:
      - "443:8443"
    depends_on:
      - auth-service
      - transaction-router

  auth-service:
    image: nexus/auth-guard:v2.2
    environment:
      - REDIS_CACHE=redis-session:6379
    depends_on:
      - redis-session

  transaction-router:
    image: nexus/tx-router:v3.5
    environment:
      - FRAUD_DETECTOR_URL=http://fraud-detector:9000
      - LEDGER_WRITER_URL=http://ledger-writer:8080
    depends_on:
      - fraud-detector
      - ledger-writer

  fraud-detector:
    image: nexus/fraud-ai:v1.8
    environment:
      - LEDGER_DB=postgres-ledger:5432
    depends_on:
      - postgres-ledger

  ledger-writer:
    image: nexus/ledger-core:v5.1
    environment:
      - DB_HOST=postgres-ledger:5432
    depends_on:
      - postgres-ledger

  postgres-ledger:
    image: postgres:16-bullseye
    environment:
      - POSTGRES_DB=ledger_vault
    ports:
      - "5433:5432"

  redis-session:
    image: redis:7.2-alpine
    ports:
      - "6380:6379"
""",
    },
    "data-mesh/streaming-pipeline": {
        "name": "CloudMesh Real-Time Streaming",
        "slug": "data-mesh/streaming-pipeline",
        "description": "Real-time event streaming topology with telemetry ingestion, Kafka broker, and ClickHouse analytics.",
        "services_count": 6,
        "primary_language": "Python / Scala",
        "yaml": """version: '3.8'

services:
  event-collector:
    image: mesh/collector:v1.4
    ports:
      - "9092:9092"
    environment:
      - KAFKA_BROKER=kafka-broker:29092
    depends_on:
      - kafka-broker

  kafka-broker:
    image: confluentinc/cp-kafka:7.5.0
    environment:
      - KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181
    depends_on:
      - zookeeper

  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    ports:
      - "2181:2181"

  stream-processor:
    image: mesh/processor:v2.0
    depends_on:
      - kafka-broker
      - clickhouse-analytics

  clickhouse-analytics:
    image: clickhouse/clickhouse-server:23.8
    ports:
      - "8123:8123"

  grafana-dashboard:
    image: grafana/grafana:10.1.0
    ports:
      - "3000:3000"
    depends_on:
      - clickhouse-analytics
""",
    },
    "health-sync/telehealth-platform": {
        "name": "HealthSync Telehealth Engine",
        "slug": "health-sync/telehealth-platform",
        "description": "HIPAA-compliant telehealth platform with patient portal, appointment router, and encrypted database.",
        "services_count": 5,
        "primary_language": "TypeScript / Node.js",
        "yaml": """version: '3.8'

services:
  patient-portal:
    image: healthsync/portal:v3.0
    ports:
      - "80:3000"
    depends_on:
      - appointment-api
      - video-relay

  appointment-api:
    image: healthsync/appointments:v2.1
    environment:
      - DB_URL=postgres://health_user@patient-db:5432/health_records
    depends_on:
      - patient-db

  video-relay:
    image: healthsync/webrtc-relay:v1.5
    ports:
      - "8443:8443"

  patient-db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=health_records
    ports:
      - "5434:5432"

  notification-worker:
    image: healthsync/notifier:v1.2
    depends_on:
      - appointment-api
""",
    },
    "spring-petclinic/spring-petclinic-microservices": {
        "name": "Spring Petclinic Java Microservices",
        "slug": "spring-petclinic/spring-petclinic-microservices",
        "description": "Cloud-native Java / Spring Boot reference microservices architecture with Spring Cloud Gateway, Eureka, Config Server, and dedicated datastores.",
        "services_count": 13,
        "primary_language": "Java / Spring Boot",
        "yaml": """version: '3.8'

services:
  api-gateway:
    image: springcommunity/spring-petclinic-api-gateway:3.1.0
    ports:
      - "8080:8080"
    environment:
      - SPRING_PROFILES_ACTIVE=docker
      - CUSTOMERS_SERVICE_URL=http://customers-service:8081
      - VISITS_SERVICE_URL=http://visits-service:8082
      - VETS_SERVICE_URL=http://vets-service:8083
    depends_on:
      - config-server
      - discovery-server

  customers-service:
    image: springcommunity/spring-petclinic-customers-service:3.1.0
    ports:
      - "8081:8081"
    environment:
      - SPRING_PROFILES_ACTIVE=docker,mysql
      - MYSQL_URL=mysql-customers:3306
    depends_on:
      - config-server
      - discovery-server
      - mysql-customers

  visits-service:
    image: springcommunity/spring-petclinic-visits-service:3.1.0
    ports:
      - "8082:8082"
    environment:
      - SPRING_PROFILES_ACTIVE=docker,mysql
      - MYSQL_URL=mysql-visits:3306
    depends_on:
      - config-server
      - discovery-server
      - mysql-visits

  vets-service:
    image: springcommunity/spring-petclinic-vets-service:3.1.0
    ports:
      - "8083:8083"
    environment:
      - SPRING_PROFILES_ACTIVE=docker,mysql
      - MYSQL_URL=mysql-vets:3306
    depends_on:
      - config-server
      - discovery-server
      - mysql-vets

  discovery-server:
    image: springcommunity/spring-petclinic-discovery-server:3.1.0
    ports:
      - "8761:8761"
    depends_on:
      - config-server

  config-server:
    image: springcommunity/spring-petclinic-config-server:3.1.0
    ports:
      - "8888:8888"

  admin-server:
    image: springcommunity/spring-petclinic-admin-server:3.1.0
    ports:
      - "9090:9090"
    depends_on:
      - config-server
      - discovery-server

  tracing-server:
    image: openzipkin/zipkin:2.24
    ports:
      - "9411:9411"

  mysql-customers:
    image: mysql:8.0
    ports:
      - "3306:3306"

  mysql-visits:
    image: mysql:8.0
    ports:
      - "3307:3306"

  mysql-vets:
    image: mysql:8.0
    ports:
      - "3308:3306"

  prometheus-server:
    image: prom/prometheus:v2.45.0
    ports:
      - "9091:9090"

  grafana-server:
    image: grafana/grafana:10.0.3
    ports:
      - "3000:3000"
    depends_on:
      - prometheus-server
""",
    },
}

# Alias common demo repos to verified topologies for zero-friction testing
SAMPLE_REPOSITORIES["googlecloudplatform/microservices-demo"] = SAMPLE_REPOSITORIES["shop-sphere/ecommerce-core"]
SAMPLE_REPOSITORIES["muneeb-sawez/aegis"] = SAMPLE_REPOSITORIES["shop-sphere/ecommerce-core"]
SAMPLE_REPOSITORIES["spring-petclinic"] = SAMPLE_REPOSITORIES["spring-petclinic/spring-petclinic-microservices"]
SAMPLE_REPOSITORIES["spring-projects/spring-petclinic"] = SAMPLE_REPOSITORIES["spring-petclinic/spring-petclinic-microservices"]
SAMPLE_REPOSITORIES["spring-projects/spring-petclinic-microservices"] = SAMPLE_REPOSITORIES["spring-petclinic/spring-petclinic-microservices"]


