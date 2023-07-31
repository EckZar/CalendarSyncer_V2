import icalendar
import concurrent.futures
import datetime
import math

from GCalDav import GoogleCalDav
from YCalDav import YandexCalDav
from logEvents import Logger
from caldav_helper import CaldavHelper

class Synchronizer:
    def __init__(self, user_email):
        self.user_email = user_email
        self.g_caldav_service = GoogleCalDav(user_email)
        self.y_caldav_service = YandexCalDav(user_email)
        self.Logger = Logger()

    def get_time(self):
        return datetime.datetime.now().strftime('%Y%m%dT%H%M%SZ')

    def sync_google_events_to_yandex(self) -> None:

        for uid in self.g_caldav_service.period_events_list:
            try:
                if 'yandex.ru' in uid:
                    continue
                print(uid)

                caldav_event = self.g_caldav_service.get_event_by_uid(uid)

                if 'No events found' in caldav_event:
                    print(f'{uid} => {caldav_event}')
                    continue

                caldav_event = cut_valarm(caldav_event)
                caldav_event = rebuild_org_attendees_to_description_2(caldav_event)

                result = self.y_caldav_service.create_event(caldav_event, uid)

                print(f'{uid} => {result.status_code}')

            except Exception as e:
                print(f'ERROR, {uid} {e}')
                continue

    def sync_yandex_events_to_google(self) -> None:

        for uid in self.y_caldav_service.period_events_list:
            try:
                if 'google.com' in uid:
                    continue

                print(uid)
                caldav_event = self.y_caldav_service.get_event_by_uid(uid)

                if '<title>Error 404 Not Found</title>' in caldav_event:
                    print(f'{uid} => <title>Error 404 Not Found</title>')
                    continue

                caldav_event = cut_valarm(caldav_event)
                caldav_event = rebuild_org_attendees_to_description_2(caldav_event)

                result = self.g_caldav_service.create_event(caldav_event, uid)
                print(f'{uid} => {result.status_code}')
            except Exception as e:
                print(f'ERROR, {uid} {e}')
                continue

    def sync_others(self):...

    def sync_deleted_G_from_Y(self):
        for _ in self.y_caldav_service.period_events_list:
            if 'google.com' not in _:
                continue
            result = list(filter(lambda x: x in _, self.g_caldav_service.events_uids_list))
            if not result:
                print(f'Delete google from yandex {_}')
                result = self.y_caldav_service.delete_event_by_uid(f'{_}')
                print(f'{_} => {result.status_code}')

    def sync_deleted_Y_from_G(self):
        for _ in self.g_caldav_service.period_events_list:
            if 'yandex.ru' not in _:
                continue
            result = list(filter(lambda x: x in _, self.y_caldav_service.events_uids_list))
            if not result:
                print(f'Delete google from yandex {_}')
                result = self.g_caldav_service.delete_event_by_uid(_)
                print(f'{_} => {result.status_code}')

    def check_if_g_broken(self, uid):
        caldav_text = self.y_caldav_service.get_event_by_uid(uid)
        cd_helper = CaldavHelper(caldav_text)

        organizer = cd_helper.get_organizer()
        if organizer and self.user_email not in organizer:
            print(f'{self.user_email} <> {organizer}')
            return True

        attendees = cd_helper.get_attendees()
        if attendees:
            return True

        return False

    def check_if_y_broken(self):...

    def recreate_broken(self, uid):
        new_uid = f'{uid}_PIK_SYNCER'
        self.y_caldav_service.create_event(new_uid)

    def check_if_in_broken_list(self, uid=None, broken_list=[]):
        if uid is None:
            return False

        if not broken_list:
            return False

        for i in broken_list:
            if uid in i:
                return True

        return False


# ====================================================================== HELPERS


def cut_valarm(text) -> str:
    while 'BEGIN:VALARM' in text:
        start = text.find('BEGIN:VALARM')
        end = text.find('END:VALARM', start)
        text = text[:start] + text[end+12:]
    return text


def rebuild_org_attendees_to_description_2(text) -> str:

    cal = icalendar.Calendar.from_ical(text)

    for event in cal.walk('VEVENT'):
        organizer = event.get('organizer')

        if organizer:
            organizer = organizer.replace('mailto:', '')
        else:
            organizer = 'Я'
        append_description = f'Организатор: {organizer}\nСписок участников:\n\n'

        attendees = event.get('attendee')

        if attendees:
            for attendee in attendees:
                attendee_email = attendee.replace('mailto:', '')
                attendee_status = attendee.params.get('PARTSTAT')
                # status = '❔'
                #
                # if 'ACCEPTED' in attendee_status:
                #     status = '✅'
                # if 'DECLINED' in attendee_status:
                #     status = '❌'
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


def get_caldav_events_uids_list(text) -> str:
    list = []
    while 'UID:' in text:
        start = text.find('UID:')
        end = text.find('\n', start)
        uid = text[start+4:end-1]
        if uid not in list and 'google.com' in uid:
            list.append(uid)
        text = text[start+4:]
    return list


def get_users_list() -> list:
    users_list = []
    with open('users_list.csv') as f:
        for line in f:
            # strip whitespace
            line = line.strip()
            # separate the columns
            line = line.split(',')
            # save the line for use later
            users_list.append(line)

    return users_list


# ====================================================================== START


def start_syncing(users_list):
    for user in users_list:
        user_email = user[0]
        print(f'Start SYNC for => {user_email}')

        syncer = Synchronizer(user_email)
        syncer.Logger.writeEvent([syncer.get_time(), 'START', user_email], 'syncing_time')

        #====== SYNC G<=>Y ======
        syncer.sync_google_events_to_yandex()
        syncer.sync_yandex_events_to_google()

        # ====== CLEAN DELETED G<=>Y ======
        syncer.sync_deleted_G_from_Y()
        syncer.sync_deleted_Y_from_G()

        # ====== ERASE OTHERS EVENTS G<=>Y ======  ??? DELETE ???
        # syncer.y_caldav_service.delete_g_events_others_period()
        # syncer.g_caldav_service.delete_y_events_others_period()

        # ====== ERASE NOT PIK_SYNCER OTHERS EVENTS G<=>Y ======
        syncer.y_caldav_service.delete_g_events_not_pik_syncer_others_period()
        syncer.g_caldav_service.delete_y_events_not_pik_syncer_others_period()

        syncer.timer()
        syncer.Logger.writeEvent([syncer.get_time(), 'END', user_email], 'syncing_time')

        print(f'End SYNC for => {user_email}')


def separate_processes():
    all_users_list = get_users_list()
    print(f'Users list len => {len(all_users_list)}')
    threads = 10
    users_batch_limit = math.ceil(len(all_users_list)/threads)
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