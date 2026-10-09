# Task Management API

REST API для системи управління задачами на **FastAPI**. Користувачі створюють задачі, призначають виконавців, змінюють статуси за чіткими правилами, коментують, шукають, фільтрують і сортують задачі, а прострочені задачі автоматично скасовуються фоновим воркером.

## Зміст

- [Можливості](#можливості)
- [Технологічний стек](#технологічний-стек)
- [Швидкий старт](#швидкий-старт)
- [Конфігурація](#конфігурація)
- [Використання API](#використання-api)
- [Бізнес-правила](#бізнес-правила)
- [Архітектура](#архітектура)
- [Модель даних](#модель-даних)
- [Фонова задача](#фонова-задача)
- [Тестування](#тестування)
- [Локальна розробка](#локальна-розробка)
- [Прийняті припущення](#прийняті-припущення)
- [Усунення проблем](#усунення-проблем)

## Можливості

- Реєстрація та авторизація за **JWT** (OAuth2 Password flow, працює з кнопкою *Authorize* у Swagger).
- CRUD задач: назва, опис, статус, пріоритет, виконавець, автор, дедлайн, дата створення та останнього оновлення.
- Окремий endpoint для зміни статусу з контрольованими переходами (state machine).
- Коментарі до задач із пагінацією.
- Пошук за назвою та описом, фільтри (статус, пріоритет, виконавець, дедлайн), сортування (дата створення, дедлайн, пріоритет), пагінація.
- Список прострочених задач і статистика (за статусами, пріоритетами, прострочені, активні).
- Фонова задача, що періодично скасовує прострочені незавершені задачі.
- Запуск однією командою через Docker Compose, міграції застосовуються автоматично.

## Технологічний стек

| Компонент | Технологія |
|---|---|
| Фреймворк | FastAPI |
| ORM | SQLAlchemy 2 (async) + asyncpg |
| База даних | PostgreSQL 16 |
| Міграції | Alembic |
| Валідація | Pydantic v2 |
| Автентифікація | JWT (PyJWT), паролі хешуються Argon2 (pwdlib) |
| Тести | Pytest, pytest-asyncio, httpx |
| Оркестрація | Docker, Docker Compose |

## Швидкий старт

Потрібні лише **Docker** та **Docker Compose**.

```bash
# 1. Створіть файл конфігурації
cp .env.example .env

# 2. Згенеруйте секретний ключ і вставте його в SECRET_KEY у .env
python -c "import secrets; print(secrets.token_hex(32))"

# 3. Запустіть
docker compose up --build
```

При старті автоматично:

1. піднімається PostgreSQL (разом із тестовою базою `taskdb_test`);
2. застосовуються міграції Alembic (`alembic upgrade head`);
3. стартує API та фоновий воркер.

Після запуску:

| Адреса | Призначення |
|---|---|
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/redoc | ReDoc |
| http://localhost:8000/health | перевірка стану |

Зупинити: `docker compose down` (дані зберігаються). Зупинити й видалити дані БД: `docker compose down -v`.

## Конфігурація

Усі налаштування задаються змінними оточення (файл `.env`).

| Змінна | Опис | Приклад |
|---|---|---|
| `POSTGRES_USER` | користувач PostgreSQL | `taskuser` |
| `POSTGRES_PASSWORD` | пароль PostgreSQL | `taskpass` |
| `POSTGRES_DB` | назва основної БД | `taskdb` |
| `DATABASE_URL` | URL основної БД | `postgresql+asyncpg://taskuser:taskpass@localhost:5432/taskdb` |
| `TEST_DATABASE_URL` | URL тестової БД | `postgresql+asyncpg://taskuser:taskpass@localhost:5432/taskdb_test` |
| `SECRET_KEY` | ключ підпису JWT, **щонайменше 32 байти** | результат `secrets.token_hex(32)` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | час життя токена, хв | `60` |
| `OVERDUE_CHECK_INTERVAL` | період перевірки прострочених задач, сек | `60` |
| `OVERDUE_WORKER_ENABLED` | вмикання фонового воркера | `true` |

У Docker Compose хост БД для сервісу `api` автоматично підставляється як `db`. Значення `localhost` у `.env` потрібні для запуску на хост-машині.

## Використання API

Базовий префікс: `/api/v1`. Усі endpoints, крім реєстрації та логіну, потребують заголовка `Authorization: Bearer <token>`.

### Швидкий сценарій у Swagger

1. `POST /auth/register` — створіть користувача.
2. Натисніть **Authorize**, введіть **email** у поле `username` та пароль (`client_id` і `client_secret` залишіть порожніми).
3. `POST /tasks` — створіть задачу.
4. `PATCH /tasks/{id}/status` — змініть статус.

### Приклад через curl

```bash
# реєстрація
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","username":"alice","password":"password123"}'

# логін (у полі username — email)
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=alice@example.com&password=password123" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# створення задачі
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"title":"Підготувати звіт","priority":"HIGH","deadline":"2030-01-01T12:00:00Z"}'

# зміна статусу
curl -X PATCH http://localhost:8000/api/v1/tasks/1/status \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"status":"IN_PROGRESS"}'

# пошук + фільтр + сортування + пагінація
curl "http://localhost:8000/api/v1/tasks?search=звіт&priority=HIGH&sort_by=deadline&order=asc&page=1&size=20" \
  -H "Authorization: Bearer $TOKEN"
```

### Endpoints

| Метод | Шлях | Опис |
|---|---|---|
| POST | `/auth/register` | реєстрація користувача |
| POST | `/auth/login` | отримання JWT (form: `username` = email, `password`) |
| GET | `/auth/me` | поточний користувач |
| POST | `/tasks` | створити задачу |
| GET | `/tasks` | список задач (пошук, фільтри, сортування, пагінація) |
| GET | `/tasks/overdue` | прострочені задачі |
| GET | `/tasks/stats` | статистика |
| GET | `/tasks/{id}` | отримати задачу |
| PATCH | `/tasks/{id}` | редагувати задачу (без статусу) |
| DELETE | `/tasks/{id}` | видалити задачу |
| PATCH | `/tasks/{id}/status` | змінити статус |
| POST | `/tasks/{id}/comments` | додати коментар |
| GET | `/tasks/{id}/comments` | список коментарів (пагінація) |
| GET | `/health` | перевірка стану сервісу |

### Параметри `GET /tasks`

| Параметр | Тип | Опис |
|---|---|---|
| `search` | string | пошук за назвою та описом (без урахування регістру) |
| `status` | enum | `BACKLOG`, `IN_PROGRESS`, `REVIEW`, `DONE`, `CANCELLED` |
| `priority` | enum | `LOW`, `MEDIUM`, `HIGH` |
| `assignee_id` | int | фільтр за виконавцем |
| `deadline_from`, `deadline_to` | datetime | діапазон дедлайну |
| `sort_by` | enum | `created_at`, `deadline`, `priority` |
| `order` | enum | `asc` (за замовчуванням) або `desc` |
| `page` | int | номер сторінки, від 1 |
| `size` | int | розмір сторінки, 1–100 (за замовчуванням 20) |

Без `sort_by` задачі сортуються за пріоритетом (High → Medium → Low), а потім за найближчим дедлайном (задачі без дедлайну — в кінці). З `sort_by=priority` порядок задає `order`: `desc` — спочатку High.

Формат відповіді зі списком:

```json
{ "items": [ ... ], "total": 42, "page": 1, "size": 20, "pages": 3 }
```

### Коди помилок

| Код | Коли |
|---|---|
| `401` | немає або недійсний токен, невірний логін/пароль |
| `403` | користувач не є автором чи виконавцем задачі |
| `404` | задачу, виконавця чи користувача не знайдено |
| `409` | конфлікт стану: недозволений перехід, редагування/видалення заборонене станом, ліміт активних задач, дубль при реєстрації |
| `422` | порушення правила валідації: дедлайн у минулому, `Done` без виконавця тощо |

## Бізнес-правила

### Статуси та переходи

```mermaid
stateDiagram-v2
    [*] --> Backlog
    Backlog --> InProgress
    Backlog --> Cancelled
    InProgress --> Review
    InProgress --> Cancelled
    Review --> Done
    Done --> [*]
    Cancelled --> [*]
```

Будь-який інший перехід, зокрема повернення на попередній статус, завершується помилкою `409`.

### Правила

| Правило | Відповідь |
|---|---|
| Перехід лише за схемою вище | `409` |
| У `Done` не можна без виконавця | `422` |
| У `Done` не можна, якщо дедлайн минув | `422` |
| Дедлайн при створенні та редагуванні не може бути в минулому (перевіряється лише при зміні дедлайну) | `422` |
| Після `Review` та `Done` виконавця змінювати заборонено | `422` |
| Задачі в `Done` та `Cancelled` не редагуються | `409` |
| Задачу в `In Progress` або `Review` не можна видалити | `409` |
| Не більше **10 активних задач** на виконавця (`Backlog`, `In Progress`, `Review`) | `409` |
| Статус змінюється лише через `PATCH /tasks/{id}/status` | поле `status` у `PATCH /tasks/{id}` ігнорується |

Перевірка ліміту активних задач виконується під блокуванням рядка користувача (`SELECT ... FOR UPDATE`), тому паралельні запити не можуть його обійти.

### Оновлення через PATCH

`PATCH /tasks/{id}` змінює лише передані поля. `"assignee_id": null` знімає виконавця, `"deadline": null` прибирає дедлайн. Поля `title` та `priority` не можуть бути `null`.

## Архітектура

Шарувата архітектура: **Router → Service → Repository → DB**.

- **Router** приймає запити, валідує вхідні дані через Pydantic, викликає сервіс.
- **Service** містить усю бізнес-логіку та керує транзакціями.
- **Repository** інкапсулює запити SQLAlchemy.
- **Domain** — enum-и та state machine статусів (чисті функції, без залежності від БД).

```
.
├── app/
│   ├── api/
│   │   ├── deps.py              # залежності: сесія, поточний користувач, сервіси
│   │   └── v1/                  # auth, tasks, comments, router
│   ├── background/
│   │   └── overdue_worker.py    # автоскасування прострочених задач
│   ├── core/
│   │   ├── config.py            # налаштування (pydantic-settings)
│   │   ├── security.py          # JWT та хешування паролів
│   │   └── exceptions.py        # доменні винятки та їх обробники
│   ├── db/                      # Base, async engine, сесія
│   ├── domain/
│   │   ├── enums.py             # TaskStatus, TaskPriority
│   │   └── status_machine.py    # дозволені переходи
│   ├── models/                  # SQLAlchemy-моделі
│   ├── repositories/            # доступ до даних
│   ├── schemas/                 # Pydantic-схеми
│   ├── services/                # бізнес-логіка
│   └── main.py                  # застосунок, lifespan
├── alembic/                     # міграції
├── docker/postgres/             # init-скрипт тестової БД
├── tests/
│   ├── unit/                    # state machine
│   └── api/                     # API-тести
├── Dockerfile
├── docker-compose.yaml
└── requirements.txt / requirements-dev.txt
```

## Модель даних

```mermaid
erDiagram
    USERS ||--o{ TASKS : "автор"
    USERS ||--o{ TASKS : "виконавець"
    USERS ||--o{ COMMENTS : "пише"
    TASKS ||--o{ COMMENTS : "має"

    USERS {
        int id PK
        string email UK
        string username UK
        string hashed_password
        bool is_active
        datetime created_at
    }
    TASKS {
        int id PK
        string title
        text description
        enum status
        enum priority
        int assignee_id FK
        int author_id FK
        datetime deadline
        datetime created_at
        datetime updated_at
    }
    COMMENTS {
        int id PK
        int task_id FK
        int author_id FK
        text text
        datetime created_at
    }
```

Індекси: `tasks(assignee_id, status)` для перевірки ліміту, `tasks(status, deadline)` для overdue та воркера, `tasks(title)`, `users(email)`, `comments(task_id)`. При видаленні задачі її коментарі видаляються каскадно, а при видаленні виконавця `assignee_id` стає `NULL`.

## Фонова задача

Вбудований `BackgroundTasks` у FastAPI виконується лише після відповіді на запит і не вміє працювати періодично. Тому воркер реалізовано як `asyncio`-задачу, що стартує у `lifespan` застосунку.

Кожні `OVERDUE_CHECK_INTERVAL` секунд виконується один атомарний запит:

```sql
UPDATE tasks SET status = 'CANCELLED', updated_at = now()
WHERE deadline < now() AND status NOT IN ('DONE', 'CANCELLED');
```

- Запит **ідемпотентний**: кілька процесів або повторні запуски не шкодять один одному.
- Помилка в одній ітерації логується й не зупиняє воркер.
- При зупинці застосунку задача коректно скасовується.
- Вимкнути воркер: `OVERDUE_WORKER_ENABLED=false`.

## Тестування

Набір складається з unit-тестів state machine та API-тестів основного функціоналу: автентифікація, CRUD, усі бізнес-правила, ліміт активних задач, пошук, фільтри, сортування, пагінація, коментарі, overdue, статистика та фоновий воркер.

Тести використовують окрему БД `taskdb_test`. Для кожного тесту схема створюється й видаляється заново. Якщо `TEST_DATABASE_URL` порожній або збігається з `DATABASE_URL`, запуск зупиняється, тож робочі дані не постраждають.

**У контейнері:**

```bash
docker compose run --rm api pytest -q
```

**Локально** (потрібна запущена БД):

```bash
docker compose up -d db
pytest -v
```

Якщо том PostgreSQL створено до появи init-скрипта, тестову БД можна створити вручну:

```bash
docker compose exec db psql -U taskuser -d taskdb -c "CREATE DATABASE taskdb_test;"
```

## Локальна розробка

Потрібен Python 3.12 або новіший.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

docker compose up -d db            # лише база даних
alembic upgrade head
uvicorn app.main:app --reload
```

Корисні команди Alembic:

```bash
alembic revision --autogenerate -m "опис зміни"   # нова міграція
alembic upgrade head                               # застосувати
alembic downgrade -1                               # відкотити останню
alembic check                                      # чи збігаються моделі та міграції
```

## Прийняті припущення

Окремі місця ТЗ допускають кілька трактувань. Прийняті рішення:

- **«Todo»** у правилі про ліміт активних задач трактується як **Backlog**, оскільки такого статусу в переліку немає.
- **Права доступу.** Змінювати задачу, видаляти її та міняти статус може **автор або виконавець**. Переглядати та коментувати задачі може будь-який авторизований користувач. Правило зосереджене в `TaskService._ensure_participant`.
- **Дедлайн** порівнюється з поточним моментом (UTC), а не лише з датою. Значення без часового поясу вважаються UTC.
- **Автоскасування** може скасувати й задачу в `Review`. Це системний перехід, він обходить таблицю переходів, доступну користувачам.
- **Коментувати** можна задачі в будь-якому статусі, зокрема `Done` та `Cancelled`: заборона редагування стосується самої задачі.
- **Ліміт активних задач** рахується по виконавцю. Задачі без виконавця в ліміті не враховуються.
- Видалення задачі фізичне (не soft delete).

## Усунення проблем

| Симптом | Причина та рішення |
|---|---|
| `401 Not authenticated` у Swagger | не натиснуто **Authorize**; логін виконується через email, а не username |
| `404 Assignee not found` при створенні | у Swagger за замовчуванням підставляється `assignee_id: 0`; вкажіть `null` або id існуючого користувача |
| `422 Deadline cannot be in the past` | дедлайн уже минув; задайте дату в майбутньому |
| `connection refused` при запуску Alembic/pytest на хості | не запущена БД: `docker compose up -d db`; перевірте, що порт 5432 вільний |
| У логах `relation "tasks" does not exist` | не застосовано міграції; перевірте, що файл міграції є в `alembic/versions/` |
| `Is a directory` для init-скрипта БД | Docker створив папку замість файлу; видаліть її й створіть `docker/postgres/init-test-db.sql` |
| `InsecureKeyLengthWarning` | `SECRET_KEY` коротший за 32 байти; згенеруйте новий |
| Тести зупиняються з повідомленням про `TEST_DATABASE_URL` | задайте його в `.env` так, щоб він відрізнявся від `DATABASE_URL` |
