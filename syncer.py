import icalendar
import concurrent.futures
import datetime
import math
import os

import config
from GCalDav import GoogleCalDav
from YCalDav import YandexCalDav
from logEvents import Logger
from caldav_helper import CaldavHelper

THREADS = 5


class Synchronizer:
    def __init__(self, user_email: str):
        self.user_email: str = user_email
        self.g_caldav_service = GoogleCalDav(user_email)
        self.y_caldav_service = YandexCalDav(user_email)
        self.Logger = Logger(user_email, datetime.datetime.now().strftime("%H:%M:%S"))

    def get_time(self):
        return datetime.datetime.now().strftime('%H:%M:%S')

    def sync_google_events_to_yandex(self) -> None:
        for _ in self.g_caldav_service.period_events_list:
            try:
                if 'yandex.ru' in _ or 'google.com' not in _:
                    continue

                caldav_event = self.g_caldav_service.get_event_by_uid(_)

                if 'No events found' in caldav_event:
                    continue

                caldav_event = cut_valarm(caldav_event)
                caldav_event = cut_org_attendees_to_description(caldav_event)

                result = self.y_caldav_service.create_event(caldav_event, _)
                self.Logger.write([self.user_email, _, result.status_code], 'G_PUT_Y_EVENTS')
            except Exception as e:
                self.Logger.write([self.user_email, _, e], 'G_PUT_Y_EVENTS_ERROR')
                continue

    def sync_yandex_events_to_google(self) -> None:
        for _ in self.y_caldav_service.period_events_list:
            try:
                if 'google.com' in _ or 'yandex.ru' not in _:
                    continue

                caldav_event = self.y_caldav_service.get_event_by_uid(_)

                if '<title>Error 404 Not Found</title>' in caldav_event:
                    continue

                caldav_event = cut_valarm(caldav_event)
                caldav_event = cut_org_attendees_to_description(caldav_event)

                result = self.g_caldav_service.create_event(caldav_event, _)
                self.Logger.write([self.user_email, _, result.status_code], 'Y_PUT_G_EVENTS')
            except Exception as e:
                self.Logger.write([self.user_email, _, e], 'Y_PUT_G_EVENTS_ERROR')
                continue

    def sync_side_events(self, cal_service_from, cal_service_to) -> None:
        for _ in cal_service_from.side_events:
            try:
                if 'PIK_SYNCER' in _:
                    continue

                caldav_event = cal_service_from.get_event_by_uid(_)

                if 'No events found' in caldav_event:
                    continue

                caldav_event = cut_valarm(caldav_event)
                caldav_event = cut_org_attendees_to_description(caldav_event)

                result = cal_service_to.create_event(caldav_event, _)
                self.Logger.write([self.user_email, _, result.status_code], f'{cal_service_from.event_code}_PUT_{cal_service_to.event_code}_EVENTS')
            except Exception as e:
                self.Logger.write([self.user_email, _, e], f'{cal_service_from.event_code}_PUT_{cal_service_to.event_code}_EVENTS_ERROR')
                continue

    def sync_deleted_G_from_Y(self):
        for _ in self.y_caldav_service.period_events_list:
            if 'google.com' not in _:
                continue
            result = list(filter(lambda x: x in _, self.g_caldav_service.events_uids_list))
            if not result:
                result = self.y_caldav_service.delete_event_by_uid(f'{_}')
                self.Logger.write([self.user_email, _, result.status_code], 'Y_DELETE_G_EVENTS')

    def sync_deleted_Y_from_G(self):
        for _ in self.g_caldav_service.period_events_list:
            if 'yandex.ru' not in _:
                continue
            result = list(filter(lambda x: x in _, self.y_caldav_service.events_uids_list))
            if not result:
                result = self.g_caldav_service.delete_event_by_uid(_)
                self.Logger.write([self.user_email, _, result.status_code], 'G_DELETE_Y_EVENTS')

    def sync_deleted_side(self):...

    def delete_y_events_not_pik_syncer_others_period(self):
        for _ in self.g_caldav_service.period_events_list:
            if 'yandex.ru' not in _:
                continue
            if 'PIK_SYNCER' in _:
                continue
            caldav_text = self.g_caldav_service.get_event_by_uid(_)
            cd_helper = CaldavHelper(caldav_text)
            organizer = cd_helper.get_org_from_main_body()
            if self.user_email not in organizer:
                result = self.g_caldav_service.delete_event_by_uid(_)
                self.Logger.write([self.user_email, _, result.status_code], 'G_DELETE_Y_EVENTS')

    def delete_g_events_not_pik_syncer_others_period(self):
        for _ in self.y_caldav_service.period_events_list:
            if 'google.com' not in _:
                continue
            if 'PIK_SYNCER' in _:
                continue
            caldav_text = self.y_caldav_service.get_event_by_uid(_)
            cd_helper = CaldavHelper(caldav_text)
            organizer = cd_helper.get_org_from_main_body()
            if self.user_email not in organizer:
                result = self.y_caldav_service.delete_event_by_uid(_)
                self.Logger.write([self.user_email, _, result.status_code], 'Y_DELETE_G_EVENTS')

    def delete_g_pik_syncer_events(self):
        for _ in self.g_caldav_service.period_events_list:
            if 'PIK_SYNCER' in _:
                self.g_caldav_service.delete_event_by_uid(_)

    def delete_y_pik_syncer_events(self):
        for _ in self.y_caldav_service.period_events_list:
            if 'PIK_SYNCER' in _:
                self.y_caldav_service.delete_event_by_uid(_)


# ====================================================================== HELPERS


def cut_valarm(text: str) -> str:
    while 'BEGIN:VALARM' in text:
        start = text.find('BEGIN:VALARM')
        end = text.find('END:VALARM', start)
        text = text[:start] + text[end+12:]
    return text


def cut_org_attendees_to_description(text: str) -> str:

    cal = icalendar.Calendar.from_ical(text)

    for event in cal.walk('VEVENT'):
        organizer = event.get('organizer')

        if organizer:
            organizer = organizer.replace('mailto:', '')
        else:
            organizer = 'Я'
        append_description = f'Организатор: {organizer}\nСписок участников:\n\n'

        attendees = event.get('attendee')

        if isinstance(attendees, list):
            for attendee in attendees:
                attendee_status = attendee.params.get('PARTSTAT')
                attendee_email = attendee.replace('mailto:', '')

                status = '❔'

                if 'ACCEPTED' in attendee_status:
                    status = '✅'
                if 'DECLINED' in attendee_status:
                    status = '❌'
                append_description += f'{attendee_email} {status}\n'

        elif isinstance(attendees, str):
            attendee_status = attendees.params.get('PARTSTAT')
            attendee_email = attendees.replace('mailto:', '')
            append_description += f'{attendee_email} {attendee_status}\n'

        event.pop('ORGANIZER', None)
        event.pop('ATTENDEE', None)

        description = event.get('DESCRIPTION')

        if description is None:
            new_description = append_description
        else:
            new_description = description + '\n\n' + append_description

        event['DESCRIPTION'] = new_description
        event['UID'] = f'{event.get("uid")}_PIK_SYNCER'

    return cal.to_ical()


def write_to_txt(text: str) -> None:
    if isinstance(text, bytes):
        text = text.decode('utf-8')
    f = open('caldav.txt', 'a', newline='', encoding="cp1251")
    f.write('\n==================================================================\n\n')
    f.write(text)
    f.write('\n')
    f.close()


def get_users_list() -> list:
    users_list = []
    with open('users_list.csv') as f:
        for line in f:
            line = line.strip()
            line = line.split(',')
            users_list.append(line)

    return users_list


def get_users_from_errors_list() -> list:
    arr = []
    path = f'logEvents/{config.global_date()}/Sync_Execution_ERROR.csv'
    with open(path) as f:
        rows = map(lambda x: x.split(','), f.readlines())
        if rows:
            [arr.append(x[1]) for x in rows if x[1] not in arr]
    os.remove(path)
    return arr


# ====================================================================== START


def sync_user_cal(user_email: str) -> None:
    print(f'Start SYNC for => {user_email}')

    syncer = Synchronizer(user_email)
    syncer.Logger.write([syncer.get_time(), 'START', user_email], 'Sync_Execution')

    # ====== SYNC G<=>Y ======
    syncer.sync_google_events_to_yandex()
    syncer.sync_yandex_events_to_google()

    syncer.sync_side_events(syncer.y_caldav_service, syncer.g_caldav_service)
    syncer.sync_side_events(syncer.g_caldav_service, syncer.y_caldav_service)

    # ====== CLEAN DELETED G<=>Y ======
    syncer.sync_deleted_G_from_Y()
    syncer.sync_deleted_Y_from_G()

    # ====== ERASE NOT PIK_SYNCER OTHERS EVENTS G<=>Y ======
    syncer.delete_g_events_not_pik_syncer_others_period()
    syncer.delete_y_events_not_pik_syncer_others_period()

    # ====== ERASE PIK_SYNCER EVENTS G<=>Y ======
    # syncer.delete_g_pik_syncer_events()
    # syncer.delete_y_pik_syncer_events()

    syncer.Logger.write([syncer.get_time(), 'END', user_email], 'Sync_Execution')

    print(f'End SYNC for => {user_email}')


def start_syncing(users_list) -> None:
    for user in users_list:
        user_email = user[0]
        try:
            sync_user_cal(user_email)
        except Exception as e:
            print(e)
            log = Logger(user_email, datetime.datetime.now().strftime('%H%M%SZ'))
            log.write([user_email, datetime.datetime.now().strftime('%Y%m%dT%H%M%SZ'), e], 'Sync_Execution_ERROR')


def process_sync_execution_errors() -> None:
    users_list = get_users_from_errors_list()
    for user_email in users_list:
        try:
            sync_user_cal(user_email)
        except Exception as e:
            print(e)
            log = Logger(user_email, datetime.datetime.now().strftime('%H%M%SZ'))
            log.write([user_email, datetime.datetime.now().strftime('%Y%m%dT%H%M%SZ'), e], 'Sync_Execution_ERROR')


def separate_processes():
    all_users_list = get_users_list()
    print(f'Users list len => {len(all_users_list)}')
    users_batch_limit = math.ceil(len(all_users_list)/THREADS)
    users_batch = []

    with concurrent.futures.ProcessPoolExecutor() as executor:
        for user in all_users_list:
            users_batch.append(user)
            if len(users_batch) == users_batch_limit:
                executor.submit(start_syncing, users_batch)
                users_batch = []

        if len(users_batch) > 0:
            executor.submit(start_syncing, users_batch)

if __name__ == "__main__":
    separate_processes()