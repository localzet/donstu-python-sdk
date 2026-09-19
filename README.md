# DONSTU Python SDK

Неофициальный Python-клиент для API образовательных сервисов ДГТУ (`edu.donstu.ru`).
Проект ориентирован на студенческие приложения, боты, виджеты расписания и другие учебные проекты.

> SDK не является официальным продуктом ДГТУ. Доступность и формат отдельных API-методов могут
> меняться. Используйте только те данные и операции, на которые у вашего аккаунта есть права.

## Возможности

- авторизация по логину/паролю или готовому Bearer-токену;
- синхронный и асинхронный клиент;
- расписание групп, преподавателей и студентов;
- списки групп, преподавателей, аудиторий и учебных лет;
- информация о пользователе/студенте и ролях;
- базовая работа с внутренней почтой;
- универсальные `request()` / `call_route()` для API-методов, которые ещё не получили отдельную обёртку;
- нормализованные исключения для HTTP, авторизации, сети и ошибок API;
- типизированный публичный интерфейс и `py.typed`.

## Установка

Пока пакет не опубликован в PyPI, его можно установить напрямую из GitHub:

```bash
pip install "donstu-sdk @ git+https://github.com/localzet/donstu-python-sdk.git"
```

Для разработки:

```bash
git clone https://github.com/localzet/donstu-python-sdk.git
cd donstu-python-sdk
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Быстрый старт: готовый токен

```python
import os

from donstu_sdk import DonstuClient

with DonstuClient(token=os.environ["DONSTU_TOKEN"]) as dstu:
    me = dstu.auth.me()
    groups = dstu.schedule.groups()

    schedule = dstu.schedule.get(
        group_id=12345,
        start_date="2026-09-21",
        end_date="2026-09-27",
    )

    print(me)
    print(groups)
    print(schedule)
```

Можно передать как сам JWT, так и строку вида `Bearer eyJ...` — SDK нормализует её автоматически.

## Авторизация по логину и паролю

```python
import os

from donstu_sdk import DonstuClient

with DonstuClient() as dstu:
    login = dstu.auth.login(
        os.environ["DONSTU_LOGIN"],
        os.environ["DONSTU_PASSWORD"],
    )

    print(login["accessToken"])
    print(dstu.auth.me())
```

После успешного `login()` полученный access token автоматически сохраняется в экземпляре клиента и
используется в следующих запросах.

Не храните логины, пароли и токены в исходном коде. Для локальной разработки удобнее использовать
переменные окружения или `.env`, исключённый из Git.

## Расписание

### Группа

```python
from datetime import date, timedelta

from donstu_sdk import DonstuClient

monday = date.today()
sunday = monday + timedelta(days=6)

with DonstuClient() as dstu:
    schedule = dstu.schedule.get(
        group_id=12345,
        start_date=monday,
        end_date=sunday,
    )
```

### Преподаватель

```python
schedule = dstu.schedule.get(
    teacher_id=123,
    start_date="2026-09-21",
    end_date="2026-09-27",
)
```

### Справочники расписания

```python
years = dstu.schedule.years()
groups = dstu.schedule.groups(year="2026-2027")
teachers = dstu.schedule.teachers(year="2026-2027")
auditories = dstu.schedule.auditories(year="2026-2027")
```

Для совместимости доступен низкоуровневый вариант с исходными именами query-параметров:

```python
schedule = dstu.schedule.rasp(
    idGroup=12345,
    sdate="2026-09-21",
    edate="2026-09-27",
)
```

## Async API

Для FastAPI, aiogram и других asyncio-приложений используйте `AsyncDonstuClient`:

```python
import asyncio
import os

from donstu_sdk import AsyncDonstuClient


async def main() -> None:
    async with AsyncDonstuClient(token=os.environ["DONSTU_TOKEN"]) as dstu:
        schedule = await dstu.schedule.get(group_id=12345)
        print(schedule)


asyncio.run(main())
```

Синхронный и асинхронный клиенты имеют одинаковую структуру: `auth`, `users`, `schedule`, `mail`.

## Пользователи

```python
student = dstu.users.student(123456)
staff = dstu.users.staff(123)
roles = dstu.users.roles(123)
```

Эти методы требуют токен с соответствующими правами.

## Универсальный запрос

Если нужный endpoint ещё не обёрнут отдельным методом SDK:

```python
result = dstu.request(
    "GET",
    "/api/SomeEndpoint",
    params={"id": 123},
)
```

Для route-параметров:

```python
result = dstu.call_route(
    "DELETE",
    "/api/SomeEndpoint/{id}",
    route_values={"id": 123},
)
```

`call_route()` не обходит серверную авторизацию и не расширяет права пользователя — запрос выполняется
с тем же токеном и теми же ограничениями, что и обычный API-вызов.

## Ответы API

Большинство методов API используют оболочку вида `state / msg / data`. SDK автоматически:

1. проверяет HTTP-статус;
2. разбирает JSON;
3. проверяет `state`;
4. возвращает `data`.

Если нужен полный JSON без автоматического распаковывания:

```python
payload = dstu.request("GET", "Rasp/ListYears", unwrap=False)
```

Если нужен сам `httpx.Response` — например, для файла:

```python
response = dstu.request_raw("GET", "/api/SomeFileEndpoint")
content = response.content
```

## Ошибки

```python
from donstu_sdk import (
    DonstuAPIError,
    DonstuAuthenticationError,
    DonstuHTTPError,
    DonstuNetworkError,
    DonstuProtocolError,
)
```

- `DonstuAuthenticationError` — HTTP 401/403;
- `DonstuHTTPError` — остальные HTTP-ошибки;
- `DonstuNetworkError` — таймаут/ошибка соединения;
- `DonstuAPIError` — API ответил успешно по HTTP, но `state` сообщает об ошибке;
- `DonstuProtocolError` — неожиданный формат ответа.

## Разработка

```bash
ruff check .
pytest
python -m build
```

Pull Request'ы с новыми безопасными high-level методами, тестами и улучшением типизации приветствуются.
