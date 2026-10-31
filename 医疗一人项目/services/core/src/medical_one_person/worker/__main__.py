from __future__ import annotations

import asyncio
import signal


async def run() -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for name in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(name, stop.set)

    print("medical-one-person worker skeleton started; Agent job handlers begin in W05")
    await stop.wait()
    print("medical-one-person worker skeleton stopped")


if __name__ == "__main__":
    asyncio.run(run())
