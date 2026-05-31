# Outbox Pattern

Демонстрационный проект сервиса обработки платежей с **Outbox pattern**.

API принимает платёж и сохраняет его вместе с outbox-событием в БД. Фоновый worker публикует события в RabbitMQ, consumer обрабатывает платёж и вызывает webhook клиента.

## Локальный запуск

Файл окружения: `compose/local/.env`.

Копирование переменных:
```bash
cp compose/local/.env.example compose/local/.env
```

Запуск:
```bash
docker compose -f compose/local/docker-compose.yml up -d
```

Остановка:

```bash
docker compose -f compose/local/docker-compose.yml down
```

### Доступные сервисы

- API — http://localhost:8000
- Webhook mock — http://localhost:8001
- Consumer health — http://localhost:8002/health
- Consumer metrics (Prometheus) — http://localhost:8002/metrics
- RabbitMQ UI — http://localhost:15672 (`payments` / `payments`)

---

## Запуск тестов

Файл окружения: `compose/tests/.env`.

Копирование переменных:
```bash
cp compose/tests/.env.example compose/tests/.env
```

Запуск
```bash
docker compose -f compose/tests/docker-compose.yml up --build --abort-on-container-exit --exit-code-from test_payment_runner
```


Остановка:
```bash
docker compose -f compose/tests/docker-compose.yml down -v
```

---

## Стек

- **Runtime:** Python 3.12, Docker
- **API:** FastAPI, Uvicorn, Pydantic v2
- **БД:** PostgreSQL 16, SQLAlchemy 2, asyncpg, Alembic
- **Messaging:** RabbitMQ 3, FastStream
- **Workers:** TaskIQ, Redis
- **DI:** Punq
- **Тесты:** Pytest
- **Metrics:** Prometheus client
- **Dev:** Poetry, Make, Black, isort, Ruff
---

## Структура проекта

```
payments-service/
|-- app/
|   |-- api/              # REST API (FastAPI)
|   |-- consumers/        # RabbitMQ consumer (FastStream)
|   |-- workers/          # Outbox worker, publisher, TaskIQ scheduler
|   |-- core/             # БД, settings, messaging, decorators
|
|-- webhook_mock/         # Мок webhook
|
|-- compose/
|   |-- local/            # docker-compose для локальной разработки
|   |   |-- .env.example
|   |-- tests/            # docker-compose для pytest
|   |   |-- .env.example
|
|-- tests/
|   |-- api/              
|   |-- consumers/       
|   |-- workers/          
|
|-- Makefile
|-- Dockerfile
```

---

## Сервисы

- **API** — создание платежа и идемпотентность по `Idempotency-Key`; чтение статуса.
- **Outbox worker** — периодически забирает pending-события из БД и публикует в RabbitMQ.
- **Consumer** — симулирует payment gateway, меняет статус платежа, вызывает `webhook_url`.
- **Webhook mock** — мок HTTP-сервера для локальной проверки.

Топология RabbitMQ (exchange, очереди, DLQ) — `app/core/messaging/topology.py`.

---

## API

Создание платежа.

- **Заголовки:** `X-API-Key`(значение из `API_KEY` в `.env`)., `Idempotency-Key` (UUID, обязателен)
- **Ответ:** `202 Accepted` — `payment_id`, `status` (`PENDING`), `created_at`
- **Тело:** `amount` (decimal > 0), `currency` (`RUB` / `USD` / `EUR`), `description`, `metadata`, `webhook_url`
- **Идемпотентность:** повтор с тем же `Idempotency-Key` вернёт ранее созданный платеж

### GET /api/v1/payments/{payment_id}

Получение деталей платежа.

- **Заголовки:** `X-API-Key`(значение из `API_KEY` в `.env`).
- **Ответ:** `200 OK` — полные данные платежа; `404` — если не найден

---

## Переменные окружения

Шаблоны: [`compose/local/.env.example`](compose/local/.env.example), [`compose/tests/.env.example`](compose/tests/.env.example).

### Обязательные

`POSTGRES_USER` — пользователь PostgreSQL  
`POSTGRES_PASSWORD` — пароль PostgreSQL  
`POSTGRES_DB` — имя базы  
`DATABASE__DSN` — async DSN для SQLAlchemy  

`RABBITMQ_DEFAULT_USER` — пользователь образа RabbitMQ  
`RABBITMQ_DEFAULT_PASS` — пароль образа RabbitMQ  
`RABBIT__HOST` — хост брокера  
`RABBIT__PORT` — порт брокера (5672)  
`RABBIT__USERNAME` — пользователь для приложения  
`RABBIT__PASSWORD` — пароль для приложения  
`RABBIT__VHOST` — virtual host  

`TASK_BROKER__DSN` — Redis-брокер TaskIQ (outbox worker)  

`API_KEY` — значение заголовка `X-API-Key`  

`OUTBOX_WORKER__RUN` — включить cron outbox worker (`True` для local, `False` для tests)  
`OUTBOX_WORKER__CRON_EXPRESSION` — расписание cron (нужно при `RUN=True`)  

`PAYMENT_CONSUMER__QUEUE_RETRY_TTL_SECONDS` — пауза между queue-retry (сек)  
`PAYMENT_CONSUMER__MAX_QUEUE_DELIVERY_ATTEMPTS` — циклов main→retry до DLQ  
`PAYMENT_CONSUMER__PREFETCH_COUNT` — QoS prefetch consumer  

### Опциональные

`LOGGING_LEVEL` — default `DEBUG`

`OUTBOX_WORKER__NAME` — имя TaskIQ-задачи (default `outbox_worker`)  
`OUTBOX_WORKER__EVENTS_LIMIT` — батч outbox событий (default `1000`)  
`OUTBOX_WORKER__MAX_ATTEMPTS` —  лимит попыток публикации события (default `3`)  
`OUTBOX_WORKER__RETRY_BASE_DELAY_SECONDS` — базовая задержка retry (default `5`)  

`PAYMENT_CONSUMER__GATEWAY_DELAY_MIN_SECONDS` — мин. задержка симуляции gateway (default `2.0`)  
`PAYMENT_CONSUMER__GATEWAY_DELAY_MAX_SECONDS` — макс. задержка (default `5.0`)  
`PAYMENT_CONSUMER__GATEWAY_SUCCESS_RATE` — вероятность успеха gateway (default `0.9`)  
`PAYMENT_CONSUMER__WEBHOOK_TIMEOUT_SECONDS` — таймаут HTTP webhook (default `10.0`)  

`CONSUMER_HEALTH_PORT` — порт health/metrics consumer (default `8002`)  
`CONSUMER_RABBIT_PING_TIMEOUT` — таймаут ping RabbitMQ в healthcheck (default `5.0`)  
