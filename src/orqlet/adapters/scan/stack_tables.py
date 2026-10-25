"""What the scanners recognise by name, per ecosystem. Anything not listed is not guessed.

Each table maps what a manifest calls a thing to a kind and a display name. The tables are data:
adding a technology is one line, and a technology that is missing is simply not reported.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from orqlet.adapters.scan.known_technologies import normalize_name
from orqlet.application.contracts.profile import TechnologyKind


@dataclass(frozen=True, slots=True)
class Known:
    kind: TechnologyKind
    name: str


def _table(rows: dict[str, tuple[TechnologyKind, str]]) -> dict[str, Known]:
    return {key: Known(kind, name) for key, (kind, name) in rows.items()}


PYPI = _table(
    {
        "fastapi": ("framework", "FastAPI"),
        "flask": ("framework", "Flask"),
        "django": ("framework", "Django"),
        "starlette": ("framework", "Starlette"),
        "aiohttp": ("framework", "aiohttp"),
        "tornado": ("framework", "Tornado"),
        "sanic": ("framework", "Sanic"),
        "litestar": ("framework", "Litestar"),
        "typer": ("framework", "Typer"),
        "click": ("framework", "Click"),
        "celery": ("framework", "Celery"),
        "apache-airflow": ("framework", "Apache Airflow"),
        "pyspark": ("framework", "Apache Spark"),
        "sqlalchemy": ("library", "SQLAlchemy"),
        "sqlmodel": ("library", "SQLModel"),
        "pydantic": ("library", "Pydantic"),
        "psycopg": ("database", "PostgreSQL"),
        "psycopg2": ("database", "PostgreSQL"),
        "psycopg2-binary": ("database", "PostgreSQL"),
        "asyncpg": ("database", "PostgreSQL"),
        "pymysql": ("database", "MySQL"),
        "mysqlclient": ("database", "MySQL"),
        "pymongo": ("database", "MongoDB"),
        "motor": ("database", "MongoDB"),
        "redis": ("database", "Redis"),
        "opensearch-py": ("database", "OpenSearch"),
        "elasticsearch": ("database", "Elasticsearch"),
        "confluent-kafka": ("queue", "Kafka"),
        "kafka-python": ("queue", "Kafka"),
        "aiokafka": ("queue", "Kafka"),
        "pika": ("queue", "RabbitMQ"),
        "aio-pika": ("queue", "RabbitMQ"),
        "nats-py": ("queue", "NATS"),
    }
)

# Go module paths are matched by prefix: `github.com/jackc/pgx/v5` matches `github.com/jackc/pgx`.
GO = _table(
    {
        "github.com/gin-gonic/gin": ("framework", "Gin"),
        "github.com/labstack/echo": ("framework", "Echo"),
        "github.com/gofiber/fiber": ("framework", "Fiber"),
        "github.com/go-chi/chi": ("framework", "chi"),
        "google.golang.org/grpc": ("framework", "gRPC"),
        "github.com/spf13/cobra": ("framework", "Cobra"),
        "gorm.io/gorm": ("library", "GORM"),
        "github.com/jackc/pgx": ("database", "PostgreSQL"),
        "github.com/lib/pq": ("database", "PostgreSQL"),
        "github.com/go-sql-driver/mysql": ("database", "MySQL"),
        "go.mongodb.org/mongo-driver": ("database", "MongoDB"),
        "github.com/redis/go-redis": ("database", "Redis"),
        "github.com/go-redis/redis": ("database", "Redis"),
        "github.com/opensearch-project/opensearch-go": ("database", "OpenSearch"),
        "github.com/segmentio/kafka-go": ("queue", "Kafka"),
        "github.com/confluentinc/confluent-kafka-go": ("queue", "Kafka"),
        "github.com/ibm/sarama": ("queue", "Kafka"),
        "github.com/shopify/sarama": ("queue", "Kafka"),
        "github.com/rabbitmq/amqp091-go": ("queue", "RabbitMQ"),
        "github.com/streadway/amqp": ("queue", "RabbitMQ"),
        "github.com/nats-io/nats.go": ("queue", "NATS"),
        "github.com/minio/minio-go": ("infrastructure", "MinIO"),
        "go.opentelemetry.io/otel": ("infrastructure", "OpenTelemetry"),
        "github.com/prometheus/client_golang": ("infrastructure", "Prometheus"),
    }
)

CRATES = _table(
    {
        "axum": ("framework", "Axum"),
        "actix-web": ("framework", "Actix Web"),
        "rocket": ("framework", "Rocket"),
        "warp": ("framework", "Warp"),
        "tonic": ("framework", "gRPC"),
        "clap": ("framework", "clap"),
        "tokio": ("library", "Tokio"),
        "sqlx": ("library", "SQLx"),
        "diesel": ("library", "Diesel"),
        "sea-orm": ("library", "SeaORM"),
        "tokio-postgres": ("database", "PostgreSQL"),
        "postgres": ("database", "PostgreSQL"),
        "mysql": ("database", "MySQL"),
        "mysql_async": ("database", "MySQL"),
        "mongodb": ("database", "MongoDB"),
        "redis": ("database", "Redis"),
        "opensearch": ("database", "OpenSearch"),
        "rdkafka": ("queue", "Kafka"),
        "lapin": ("queue", "RabbitMQ"),
        "async-nats": ("queue", "NATS"),
    }
)

NPM = _table(
    {
        "express": ("framework", "Express"),
        "fastify": ("framework", "Fastify"),
        "koa": ("framework", "Koa"),
        "@nestjs/core": ("framework", "NestJS"),
        "next": ("framework", "Next.js"),
        "react": ("framework", "React"),
        "vue": ("framework", "Vue"),
        "@angular/core": ("framework", "Angular"),
        "svelte": ("framework", "Svelte"),
        "prisma": ("library", "Prisma"),
        "@prisma/client": ("library", "Prisma"),
        "pg": ("database", "PostgreSQL"),
        "mysql2": ("database", "MySQL"),
        "mysql": ("database", "MySQL"),
        "mongodb": ("database", "MongoDB"),
        "mongoose": ("database", "MongoDB"),
        "redis": ("database", "Redis"),
        "ioredis": ("database", "Redis"),
        "@opensearch-project/opensearch": ("database", "OpenSearch"),
        "kafkajs": ("queue", "Kafka"),
        "amqplib": ("queue", "RabbitMQ"),
    }
)

# Container image names, as the last path component of the image reference.
IMAGES = _table(
    {
        "python": ("language", "Python"),
        "golang": ("language", "Go"),
        "go": ("language", "Go"),
        "rust": ("language", "Rust"),
        "node": ("runtime", "Node.js"),
        "openjdk": ("language", "Java"),
        "eclipse-temurin": ("language", "Java"),
        "amazoncorretto": ("language", "Java"),
        "dotnet": ("runtime", ".NET"),
        "ruby": ("language", "Ruby"),
        "php": ("language", "PHP"),
        "postgres": ("database", "PostgreSQL"),
        "postgresql": ("database", "PostgreSQL"),
        "mysql": ("database", "MySQL"),
        "mariadb": ("database", "MariaDB"),
        "mongo": ("database", "MongoDB"),
        "mongodb": ("database", "MongoDB"),
        "redis": ("database", "Redis"),
        "valkey": ("database", "Valkey"),
        "cassandra": ("database", "Cassandra"),
        "clickhouse": ("database", "ClickHouse"),
        "clickhouse-server": ("database", "ClickHouse"),
        "opensearch": ("database", "OpenSearch"),
        "elasticsearch": ("database", "Elasticsearch"),
        "kafka": ("queue", "Kafka"),
        "cp-kafka": ("queue", "Kafka"),
        "redpanda": ("queue", "Redpanda"),
        "rabbitmq": ("queue", "RabbitMQ"),
        "nats": ("queue", "NATS"),
        "pulsar": ("queue", "Pulsar"),
        "minio": ("infrastructure", "MinIO"),
        "nginx": ("infrastructure", "NGINX"),
        "traefik": ("infrastructure", "Traefik"),
        "envoy": ("infrastructure", "Envoy"),
        "opentelemetry-collector": ("infrastructure", "OpenTelemetry Collector"),
        "airflow": ("framework", "Apache Airflow"),
        "spark": ("framework", "Apache Spark"),
        "trino": ("infrastructure", "Trino"),
        "localstack": ("infrastructure", "LocalStack"),
    }
)

_VERSION = re.compile(r"v?(\d+(?:\.\d+){0,2})")


def lookup_pypi(name: str) -> Known | None:
    return PYPI.get(normalize_name(name))


def lookup_prefix(table: dict[str, Known], module: str) -> Known | None:
    """The entry whose key is `module` or a path prefix of it (longest key wins)."""
    lowered = module.lower()
    best: str | None = None
    for key in table:
        matches = lowered == key or lowered.startswith((key + "/", key + "."))
        if matches and (best is None or len(key) > len(best)):
            best = key
    return None if best is None else table[best]


def lookup_image(reference: str) -> Known | None:
    """`registry/team/python:3.13-dev` is Python; `postgres:16` is PostgreSQL."""
    name = reference.split("@", 1)[0].split(":", 1)[0].rsplit("/", 1)[-1].lower()
    return IMAGES.get(name)


def image_version(reference: str) -> str | None:
    """The leading version of an image tag (`3.13-dev` gives `3.13`). `latest` gives `None`."""
    if ":" not in reference.split("/")[-1]:
        return None
    tag = reference.split("@", 1)[0].rsplit(":", 1)[-1]
    match = _VERSION.match(tag)
    return None if match is None else match.group(1)
