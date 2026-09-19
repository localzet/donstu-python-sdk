# DONSTU Python SDK

SDK собран по исходникам без сетевого probing production-системы.
Основная цель — дать нормальный Python-клиент к `https://edu.donstu.ru/api/` и сохранить
полный каталог маршрутов.

## Установка

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Использование

```python
from donstu_sdk import DonstuClient

with DonstuClient() as dstu:
    dstu.auth.login("login", "password")
    me = dstu.auth.me()
    student = dstu.users.student(-123456)
    schedule = dstu.schedule.rasp(idGroup=1234, sdate="2026-09-19")
```

Можно передать уже существующий токен:

```python
client = DonstuClient(token="...")
```

## Полный route catalog

```python
for route in client.catalog.find("Certificates"):
    print(route.method, route.path, route.params, route.authorize)
```

Либо вызвать endpoint напрямую:

```python
result = client.call_route(
    "GET",
    "/api/Rasp",
    params={"idGroup": 1234, "sdate": "2026-09-19"},
)
```

## Ограничения реверса

Исходники декомпилированы, а часть маршрутов содержит сложные DTO. Поэтому полный каталог
сохраняет оригинальные C# типы параметров, но высокоуровневые Python-модели пока сделаны только для
наиболее используемых частей. Для редких endpoint'ов используйте `call_route()` и `catalog.find()`.
