import os
import csv
from datetime import datetime
from config import global_date


class Logger:
    def __init__(self):
        self.global_date = global_date()
        self.check()

    def check(self):
        if not os.path.exists(f"logEvents/{self.global_date}"):
            os.makedirs(f"logEvents/{self.global_date}")

    def writeEvent(self, arr, log_file_name='events'):

        with open(f"logEvents/{self.global_date}/{log_file_name}.csv", "a", newline="") as fp:
            writer = csv.writer(fp, delimiter=",")
            try:
                writer.writerow(arr)
            except Exception as e:
                arr[1] = ''
                arr[7] = e
                self.writeError(arr)

    def writeError(self, arr, log_file_name='errors'):
        with open(f"logEvents/{self.global_date}/{log_file_name}.csv", "a", newline="") as fp:
            writer = csv.writer(fp, delimiter=",")
            try:
                writer.writerow(arr)
            except:
                pass

    def writeStartExecution(self, status, log_file_name='time'):
        with open(f"logEvents/{self.global_date}/{log_file_name}.csv", "a", newline="") as fp:
            writer = csv.writer(fp, delimiter=",")
            writer.writerow([datetime.now(), status])