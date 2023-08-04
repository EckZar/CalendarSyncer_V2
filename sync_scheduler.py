import schedule
import time
import concurrent.futures
from _datetime import datetime
import asyncio

import syncer


def start():
    while True:
        schedule.run_pending()


def run_syncer():
    print(f'SYNC_TIME_{datetime.now().strftime("%H%M%S")}')
    with concurrent.futures.ProcessPoolExecutor() as executor:
        executor.submit(syncer.start_syncing)


schedule.every(15).minutes.do(run_syncer)


if __name__ == "__main__":
    # start()

    syncer.start_syncing()
