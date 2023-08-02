import schedule
import time
import concurrent.futures
from _datetime import datetime

import syncer


def start():
    while True:
        schedule.run_pending()
        time.sleep(1)


def run_syncer():
    # print(f'SYNC_TIME_{datetime.now().strftime("%H%M%S")}')
    with concurrent.futures.ProcessPoolExecutor() as executor:
        executor.submit(syncer.start_syncing)


schedule.every(5).seconds.do(run_syncer)


if __name__ == "__main__":
    start()
