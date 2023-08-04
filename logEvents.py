import os
import csv
import asyncio
from _datetime import datetime


class Logger:
    def __init__(self, user_email: str, time: str):
        self.global_date = datetime.now().strftime('%Y%m%d')
        asyncio.ensure_future(self.check())
        self.id = f'{user_email}_{time}'

    async def check(self):
        if not os.path.exists(f"logEvents/{self.global_date}"):
            os.makedirs(f"logEvents/{self.global_date}")

    async def write(self, arr, log_file_name):
        with open(f"logEvents/{self.global_date}/{log_file_name}.csv", "a", newline="") as fp:
            writer = csv.writer(fp, delimiter=",")
            try:
                writer.writerow([self.id, *arr])
            except Exception as e:
                await self.write([self.id, e], 'LOG_ERROR')
