from datetime import datetime


def global_date():
    return datetime.now().strftime('%Y%m%d')