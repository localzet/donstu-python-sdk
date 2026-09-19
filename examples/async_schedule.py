import asyncio
import os

from donstu_sdk import AsyncDonstuClient


async def main() -> None:
    async with AsyncDonstuClient(token=os.environ["DONSTU_TOKEN"]) as dstu:
        schedule = await dstu.schedule.get(group_id=12345)
        print(schedule)


if __name__ == "__main__":
    asyncio.run(main())
