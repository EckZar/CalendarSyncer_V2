import main
import datetime

users_list = main.get_users_from_errors_list()

for user_email in users_list:
    try:
        main.sync_user_cal(user_email)
    except Exception as e:
        log = main.Logger(user_email, datetime.datetime.now().strftime('%H%M%SZ'))
        log.write([user_email, datetime.datetime.now().strftime('%Y%m%dT%H%M%SZ'), e], 'Sync_Execution_ERROR')