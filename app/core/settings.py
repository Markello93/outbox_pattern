import pydantic
import pydantic_settings


class BaseSettings(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        use_enum_values=True,
        extra="ignore",
    )


class DatabaseSettings(pydantic.BaseModel):
    dsn: pydantic.PostgresDsn
    engine_pool_size: int = pydantic.Field(default=20)
    engine_max_overflow: int = pydantic.Field(default=0)
    engine_pool_ping: bool = pydantic.Field(default=False)
    engine_pool_timeout: int = pydantic.Field(default=30)


class TaskBrokerSettings(pydantic.BaseModel):
    dsn: pydantic.RedisDsn


class RabbitServerSettings(pydantic.BaseModel):
    host: str = pydantic.Field(default="localhost")
    port: int = pydantic.Field(default=5672)
    username: str = pydantic.Field(default="guest")
    password: str = pydantic.Field(default="guest")
    vhost: str = pydantic.Field(default="/")


class BaseJobSettings(pydantic.BaseModel):
    name: str | None = pydantic.Field(default=None)
    cron_expression: str | None = pydantic.Field(default=None)
    run: bool = pydantic.Field(default=False)


class OutboxWorkerSettings(BaseJobSettings):
    name: str = pydantic.Field(default="outbox_worker")
    events_limit: int = pydantic.Field(default=1000)
    max_attempts: int = pydantic.Field(default=3, ge=1)
    retry_base_delay_seconds: int = pydantic.Field(default=5, gt=0)


class PaymentConsumerSettings(pydantic.BaseModel):
    gateway_delay_min_seconds: float = pydantic.Field(default=2.0, gt=0)
    gateway_delay_max_seconds: float = pydantic.Field(default=5.0, gt=0)
    gateway_success_rate: float = pydantic.Field(default=0.9, ge=0, le=1)
    webhook_timeout_seconds: float = pydantic.Field(default=10.0, gt=0)
    queue_retry_ttl_seconds: int = pydantic.Field(default=30, gt=0)
    max_queue_delivery_attempts: int = pydantic.Field(default=5, ge=1)
    prefetch_count: int = pydantic.Field(default=10, ge=1)


class ApiSettings(BaseSettings):
    database: DatabaseSettings = pydantic.Field(default_factory=DatabaseSettings)
    api_key: str = pydantic.Field(default="dev-api-key")


class ConsumerSettings(BaseSettings):
    database: DatabaseSettings = pydantic.Field(default_factory=DatabaseSettings)
    rabbit: RabbitServerSettings = pydantic.Field(default_factory=RabbitServerSettings)
    payment_consumer: PaymentConsumerSettings = pydantic.Field(default_factory=PaymentConsumerSettings)
    logging_level: str = pydantic.Field(default="DEBUG")
    consumer_health_port: int = pydantic.Field(default=8002)
    consumer_rabbit_ping_timeout: float = pydantic.Field(default=5.0)


class WorkersSettings(BaseSettings):
    database: DatabaseSettings = pydantic.Field(default_factory=DatabaseSettings)
    task_broker: TaskBrokerSettings = pydantic.Field(default_factory=TaskBrokerSettings)
    outbox_worker: OutboxWorkerSettings = pydantic.Field(default_factory=OutboxWorkerSettings)
    rabbit: RabbitServerSettings = pydantic.Field(default_factory=RabbitServerSettings)
