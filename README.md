# response_service

Отклики на задачи и комментарии. Денормализованные копии user/task/post для чтения и поля **`user_name`** в API.

## Порт и health

Внутри Docker: **8000**. Префикс API: `/response`.

```bash
curl http://localhost:8000/health
```

## API

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/response/responses?task_id=` | Список откликов + **`user_name`** |
| GET | `/response/responses/{id}` | Один отклик |
| POST | `/response/responses` | Создать отклик |
| GET | `/response/responses/{id}/comments` | Комментарии + **`user_name`** |
| POST | `/response/responses/{id}/comments` | Добавить комментарий |
| PATCH | `/response/responses/{id}/status` | Смена статуса |

## Kafka

| Направление | Топик |
|-------------|--------|
| In | `profile_service.user.registered`, `profile_service.profile.changed` |
| In | `project_service.task.*`, `project_service.post.*` |
| Out | `response_service.response.add`, `response_service.response.delete` |
| Out | `project-answers` (`answer.created` / `answer.deleted`) |

Константы: `src/kafka_topics.py`.

## База данных

- БД: `response_db`
- Миграции: `src/migrations/sql/`
- Таблицы: `response`, `comments`, `denormalized_user`, `denormalized_task`, `denormalized_post`

## Имена пользователей (для UI)

Поле **`user_name`** в ответах и комментариях заполняется из `denormalized_user.name` (синхронизация через Kafka). Отдельный запрос в profile_service не нужен.

## Переменные окружения

| Переменная | Назначение |
|------------|------------|
| `LOG_LEVEL` | `INFO`, `DEBUG`, … |
| `DATABASE_URL` | asyncpg DSN |
| `MIGRATIONS_DATABASE_URL` | yoyo |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka |
| `KAFKA_CONSUMER_GROUP` | `response-service-group` |
| `RUN_DB_MIGRATIONS_ON_STARTUP` | `true` |

## Логи

Формат: `время | уровень | logger | сообщение`.  
Настройка: `src/core/logging.py` → `setup_logging()` в `lifespan`.

**Docker:**

```bash
docker logs response -f
```

**Logger-ы:**

| Logger | Содержимое |
|--------|------------|
| `response_service` | Старт, миграции |
| `src.services.kafka_consumer` | Входящие топики |
| `src.services.kafka_event_handler` | Обработка denorm |
| `src.services.response_service` | CRUD откликов |
| `src.services.comment_service` | Комментарии |

```bash
# consumer / denorm
docker logs response 2>&1 | grep -E "Dispatching|denormalized|WARNING"

# публикация ответов
docker logs response 2>&1 | grep "Published event"
```

`aiokafka` и `httpx` по умолчанию на уровне WARNING.

## Запуск

```bash
cd ../infra_faberge && make response-dev
```

## Тесты

```bash
PYTHONPATH=. pytest tests -q
```
