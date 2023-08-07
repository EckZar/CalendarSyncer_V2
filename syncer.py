import icalendar
import asyncio
import aiohttp
from datetime import datetime

from GCalDav import GoogleCalDav
from YCalDav import YandexCalDav
from logEvents import Logger
from caldav_helper import CaldavHelper


class Synchronizer:
    def __init__(self, user_email: str):
        self.user_email: str = user_email
        self.g_caldav_service = GoogleCalDav(user_email)
        self.y_caldav_service = YandexCalDav(user_email)
        self.DATE = datetime.now().strftime('%Y%m%d')
        self.TIME = datetime.now().strftime("%H:%M:%S")
        self.Logger = Logger(user_email, self.TIME)

    async def sync_events(self, cal_service_from, cal_service_to) -> None:
        for _ in cal_service_from.period_events_list:
            try:
                if cal_service_from.service_to in _ or cal_service_from.service_from not in _:
                    continue

                caldav_event = await cal_service_from.get_event_by_uid(_)

                if 'No events found' in caldav_event or '<title>Error 404 Not Found</title>' in caldav_event:
                    continue

                caldav_event = cut_valarm(caldav_event)
                caldav_event = cut_org_attendees_to_description(caldav_event)

                result = await cal_service_to.create_event(caldav_event, _)
                await self.Logger.write([self.user_email, _, result.status_code],
                                        f'{cal_service_from.service_from}_PUT_{cal_service_from.service_to}_EVENTS')
            except Exception as e:
                await self.Logger.write([self.user_email, _, e],
                                        f'{cal_service_from.service_from}_PUT_{cal_service_from.service_to}_EVENTS_ERROR')
                continue

    async def sync_deleted(self, cal_service_from, cal_service_to):
        for _ in cal_service_to.period_events_list:
            if cal_service_from.service_from not in _:
                continue
            result = list(filter(lambda x: x in _, cal_service_from.events_uids_list))
            if not result:
                result = await cal_service_to.delete_event_by_uid(_)
                await self.Logger.write([self.user_email, _, result.status_code],
                                        f'{cal_service_to.service_from}_DELETE_{cal_service_to.service_to}_EVENTS')

    async def delete_events_not_pik_syncer_others_period(self, cal_service):
        for _ in cal_service.period_events_list:
            if cal_service.service_from not in _:
                continue
            if 'PIK_SYNCER' in _:
                continue
            caldav_text = await cal_service.get_event_by_uid(_)
            cd_helper = CaldavHelper(caldav_text)
            organizer = cd_helper.get_org_from_main_body()
            if self.user_email not in organizer:
                result = await cal_service.delete_event_by_uid(_)
                await self.Logger.write([self.user_email, _, result.status_code],
                                        f'{cal_service.service_from}_DELETE_{cal_service.service_to}_EVENTS')

    async def delete_pik_syncer_events(self, cal_service):
        for _ in cal_service.period_events_list:
            if 'PIK_SYNCER' in _:
                await cal_service.delete_event_by_uid(_)


# ====================================================================== HELPERS


def cut_valarm(text: str) -> str:
    while 'BEGIN:VALARM' in text:
        start = text.find('BEGIN:VALARM')
        end = text.find('END:VALARM', start)
        text = text[:start] + text[end + 12:]
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


# ====================================================================== START


async def sync_user_cal(user_email: str) -> None:
    print(f'Start SYNC for => {user_email}')

    syncer = Synchronizer(user_email)

    await syncer.Logger.write([syncer.TIME, 'START', user_email], 'Sync_Execution')

    await syncer.g_caldav_service.get_events_from_to_dates()
    await syncer.g_caldav_service.get_all_events()

    await syncer.y_caldav_service.get_main_calendar()

    await syncer.y_caldav_service.get_events_from_to_dates()
    await syncer.y_caldav_service.get_all_events()
    await syncer.y_caldav_service.get_calendars()

    # ====== SYNC G<=>Y ======
    # await syncer.sync_events(syncer.g_caldav_service, syncer.y_caldav_service)
    await syncer.sync_events(syncer.y_caldav_service, syncer.g_caldav_service)
    #
    # # ====== CLEAN DELETED G<=>Y ======
    #
    # await syncer.sync_deleted(syncer.g_caldav_service, syncer.y_caldav_service)
    # await syncer.sync_deleted(syncer.y_caldav_service, syncer.g_caldav_service)
    #
    # # ====== ERASE NOT PIK_SYNCER OTHERS EVENTS G<=>Y ======
    # await syncer.delete_events_not_pik_syncer_others_period(syncer.g_caldav_service)
    # await syncer.delete_events_not_pik_syncer_others_period(syncer.y_caldav_service)

    # ====== ERASE PIK_SYNCER EVENTS G<=>Y ======
    # syncer.delete_pik_syncer_events(syncer.g_caldav_service)
    # syncer.delete_pik_syncer_events(syncer.y_caldav_service)

    await syncer.Logger.write([syncer.TIME, 'END', user_email], 'Sync_Execution')
    print(f'End SYNC for => {user_email}')


def start_syncing() -> None:
    users_list = get_users_list()
    for user in users_list:
        user_email = user[0]
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(sync_user_cal(user_email))
            loop.close()
        except Exception as e:
            print(e)
            log = Logger(user_email, datetime.now().strftime('%H%M%SZ'))
            asyncio.ensure_future(log.write([user_email, datetime.now().strftime('%Y%m%dT%H%M%SZ'), e], 'Sync_Execution_ERROR'))
