import requests
import yAuth
import datetime
import xml.etree.ElementTree as ET
from config import global_date
from caldav_helper import CaldavHelper

DELTA_TO = 14
DELTA_FROM = 0

class YandexCalDav:
    def __init__(self, user_email):
        self.user_email: str = user_email
        self.event_code = 'yandex.ru'
        self.headers: dict = {
            'Authorization': f'OAuth {yAuth.get_access_token(user_email)}'
        }
        self.base_url: str = f'https://caldav.yandex.ru'
        self.calendars: list = []
        self.main_calendar: str = self.get_main_calendar()
        self.events_uids_list: list = []
        self.period_events_list: list = []
        self.events_list_others: list = []
        self.yandex_events: list = []
        self.google_events: list = []
        self.side_events: list = []
        self.get_calendars()
        self.get_all_events()
        self.get_events_from_to_dates()

    def get_calendars(self):
        respone = requests.request("GET", f'{self.base_url}/calendars/{self.user_email}', headers=self.headers)
        content = respone.content

        if isinstance(content, (bytes, bytearray)):
            content = content.decode('utf-8')

        content = content.split('\n')

        for _ in content:
            if _ in self.calendars:
                continue
            self.calendars.append(_)

    def get_main_calendar(self) -> None:
        respone = requests.request("GET", f'{self.base_url}/calendars/{self.user_email}', headers=self.headers)
        content = respone.content

        if isinstance(content, (bytes, bytearray)):
            content = content.decode('utf-8')

        content = content.split('\n')

        return content[2]

    def get_caldav_events(self) -> str:
        url = f"{self.base_url}{self.main_calendar}{self.user_email}"
        return requests.request("GET", url, headers=self.headers).text

    def get_event_by_uid(self, uid: str) -> str:
        url = f"{self.base_url}{self.main_calendar}{uid}.ics"
        return requests.request("GET", url, headers=self.headers).content.decode('utf-8')

    def get_events_from_to_dates(self, date_from=None, date_to=None) -> None:

        if date_from is None:
            now = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            date_from = (now + datetime.timedelta(days=DELTA_FROM)).strftime('%Y%m%dT%H%M%SZ')
            if date_to is None:
                date_to = (now + datetime.timedelta(days=DELTA_TO)).strftime('%Y%m%dT%H%M%SZ')

        time_range = f"<C:time-range start=\"{date_from}\" " \
                     f"              end=\"{date_to}\"/>"

        url = f"{self.base_url}{self.main_calendar}"

        payload = "<?xml version=\"1.0\" encoding=\"utf-8\" ?>\r\n" \
                  "<C:calendar-query xmlns:D=\"DAV:\"\r\n" \
                  "xmlns:C=\"urn:ietf:params:xml:ns:caldav\">\r\n\r\n\r\n" \
                  "<D:prop>" \
                  "<D:href />" \
                  "</D:prop>" \
                  "<C:filter>\r\n" \
                  "<C:comp-filter name=\"VCALENDAR\">\r\n" \
                  "<C:comp-filter name=\"VEVENT\">\r\n" \
                  f"{time_range}\r\n" \
                  "</C:comp-filter>\r\n" \
                  "</C:comp-filter>\r\n" \
                  "</C:filter>\r\n\r\n" \
                  "</C:calendar-query>"

        response = requests.request("REPORT", url, headers=self.headers, data=payload)

        tree = ET.fromstring(response.content)

        for href_element in tree.iter("{DAV:}href"):
            href = href_element.text
            if href and href not in self.period_events_list:
                uid = href.split('/')[-1].replace('.ics', '')
                self.period_events_list.append(uid)

                if 'yandex.ru' in uid:
                    self.yandex_events.append(uid)
                elif 'google.com' in uid:
                    self.yandex_events.append(uid)
                else:
                    self.side_events.append(uid)


    def get_all_events(self) -> None:

        url = f"{self.base_url}{self.main_calendar}"

        payload = "<?xml version=\"1.0\" encoding=\"utf-8\" ?>\r\n" \
                  "<C:calendar-query xmlns:C=\"urn:ietf:params:xml:ns:caldav\">\r\n  " \
                  "<D:prop xmlns:D=\"DAV:\">\r\n    " \
                  "<D:href/>\r\n  " \
                  "</D:prop>\r\n  " \
                  "<C:filter>\r\n    " \
                  "<C:comp-filter name=\"VCALENDAR\">\r\n      " \
                  "<C:comp-filter name=\"VEVENT\"/>\r\n    " \
                  "</C:comp-filter>\r\n  " \
                  "</C:filter>\r\n" \
                  "</C:calendar-query>"

        response = requests.request("REPORT", url, headers=self.headers, data=payload)

        tree = ET.fromstring(response.content)

        for href_element in tree.iter("{DAV:}href"):
            href = href_element.text
            if href and href not in self.events_uids_list:
                uid = href.split('/')[-1].replace('.ics', '')
                self.events_uids_list.append(uid)

    def create_event(self, payload, uid):
        headers = self.headers
        headers['Content-Type'] = 'text/calendar'
        url = f'{self.base_url}{self.main_calendar}{uid}_PIK_SYNCER.ics'
        return requests.request("PUT", url, headers=self.headers, data=payload)

    def delete_event_by_uid(self, uid):
        url = f"{self.base_url}{self.main_calendar}{uid}.ics"
        return requests.request("DELETE", url, headers=self.headers)

    def delete_g_events_others_period(self):
        for uid in self.period_events_list:
            if 'google.com' not in uid:
                continue

            caldav_text = self.get_event_by_uid(uid)
            cd_helper = CaldavHelper(caldav_text)

            organizer = cd_helper.get_org_from_main_body()

            if self.user_email not in organizer:
                self.delete_event_by_uid(uid)


    def delete_g_synced_google_events(self):...
