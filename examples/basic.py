import os

from donstu_sdk import DonstuClient


with DonstuClient() as dstu:
    dstu.auth.login(
        os.environ["DONSTU_LOGIN"],
        os.environ["DONSTU_PASSWORD"],
    )

    me = dstu.auth.me()
    print(me)

    # Пример обычного расписания группы.
    rasp = dstu.schedule.rasp(idGroup=12345, sdate="2026-09-19")
    print(rasp)

    # Найти неизвестный заранее endpoint в каталоге.
    for route in dstu.catalog.find("Rasp", method="GET")[:10]:
        print(route.method, route.path, route.params)
