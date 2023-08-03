import schedule
import time
import concurrent.futures
from _datetime import datetime
import asyncio

import syncer


def start():
    while True:
        schedule.run_pending()
        time.sleep(1)


def run_syncer():
    print(f'SYNC_TIME_{datetime.now().strftime("%H%M%S")}')
    with concurrent.futures.ProcessPoolExecutor() as executor:
        executor.submit(syncer.start_syncing)


def run_pe():
    print(f'SYNC_TIME_{datetime.now().strftime("%H%M%S")}')
    with concurrent.futures.ProcessPoolExecutor() as executor:
        executor.submit(syncer.process_sync_execution_errors)


schedule.every(15).minutes.do(run_syncer)
schedule.every(5).minutes.do(run_pe)


if __name__ == "__main__":
    # start()

    asyncio.run(syncer.start_syncing())
