import os

from donstu_sdk import DonstuClient


with DonstuClient() as dstu:
    dstu.auth.login(
        os.environ["DONSTU_LOGIN"],
        os.environ["DONSTU_PASSWORD"],
    )

    print(dstu.auth.me())
    print(dstu.schedule.groups())
    print(dstu.schedule.get(group_id=12345, start_date="2026-09-21"))
