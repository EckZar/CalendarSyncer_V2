import syncer
import datetime

users_list = syncer.get_users_from_errors_list()

for user_email in users_list:
    try:
        syncer.sync_user_cal(user_email)
    except Exception as e:
        print(e)
        log = syncer.Logger(user_email, datetime.datetime.now().strftime('%H%M%SZ'))
        log.write([user_email, datetime.datetime.now().strftime('%Y%m%dT%H%M%SZ'), e], 'Sync_Execution_ERROR')