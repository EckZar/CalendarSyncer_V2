import requests
from gAuth import get_access_token
import datetime
import xml.etree.ElementTree as ET
from config import global_date
from caldav_helper import CaldavHelper

DELTA_TO = 1
DELTA_FROM = 0

class GoogleCalDav:
    def __init__(self, user_email):
        self.user_email: str = user_email
        self.token: str = get_access_token(user_email)
        self.base_url: str = 'https://apidata.googleusercontent.com'
        self.events_uids_list: list = []
        self.period_events_list: list = []
        self.events_list_broken: list = []
        self.headers = {
            'Authorization': f'Bearer {self.token}'
        }
        self.get_all_events()
        self.get_events_from_to_dates()

    def get_events_uids_list(self):
        return self.events_uids_list

    def get_caldav_events(self) -> str:
        url = f"{self.base_url}/caldav/v2/{self.user_email}/events"
        return requests.request("GET", url, headers=self.headers).text

    def get_event_by_uid(self, uid: str) -> str:
        url = f"{self.base_url}/caldav/v2/{self.user_email}/events/{uid}.ics"
        return requests.request("GET", url, headers=self.headers).text

    def get_events_from_to_dates(self, date_from=None, date_to=None) -> None:

        if date_from is None:
            now = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            date_from = (now + datetime.timedelta(days=DELTA_FROM)).strftime('%Y%m%dT%H%M%SZ')
            if date_to is None:
                date_to = (now + datetime.timedelta(days=DELTA_TO)).strftime('%Y%m%dT%H%M%SZ')

        time_range = f"<C:time-range start=\"{date_from}\" " \
                     f"              end=\"{date_to}\"/>"
        payload = "<?xml version=\"1.0\" encoding=\"utf-8\" ?>\r\n" \
                  "<C:calendar-query xmlns:D=\"DAV:\"\r\n" \
                                    "xmlns:C=\"urn:ietf:params:xml:ns:caldav\">\r\n\r\n\r\n" \
                      "<C:filter>\r\n" \
                        "<C:comp-filter name=\"VCALENDAR\">\r\n" \
                            "<C:comp-filter name=\"VEVENT\">\r\n" \
                                f"{time_range}\r\n" \
                            "</C:comp-filter>\r\n" \
                        "</C:comp-filter>\r\n" \
                      "</C:filter>\r\n\r\n" \
                  "</C:calendar-query>"

        url = f"{self.base_url}/caldav/v2/{self.user_email}/events"

        try:
            response = requests.request("REPORT", url, headers=self.headers, data=payload)
        except Exception as e:
            print(e)
        tree = ET.fromstring(response.content)

        for href_element in tree.iter("{DAV:}href"):
            href = href_element.text.replace('%40', '@')
            if href not in self.period_events_list:
                uid = href.split('/')[-1].replace('.ics', '')
                if 'PIK_SYNCER' in uid:
                    self.events_list_broken.append(uid)
                self.period_events_list.append(uid)

    def get_all_events(self) -> None:

        url = f"{self.base_url}/caldav/v2/{self.user_email}/events"

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
            href = href_element.text#.replace('%40', '@')
            if href and href not in self.events_uids_list:
                uid = href.split('/')[-1].replace('.ics', '')
                if 'PIK_SYNCER' in uid:
                    self.events_list_broken.append(uid)
                self.events_uids_list.append(uid)

    def create_event(self, payload, uid):
        url = f"{self.base_url}/caldav/v2/{self.user_email}/events/{uid}_PIK_SYNCER.ics"
        self.headers['Content-Type'] = 'text/calendar'
        return requests.request("PUT", url, headers=self.headers, data=payload)

    def delete_event_by_uid(self, uid):
        url = f"{self.base_url}/caldav/v2/{self.user_email}/events/{uid}.ics"
        return requests.request("DELETE", url, headers=self.headers)

    def delete_y_events_not_pik_syncer_others_period(self):
        for uid in self.period_events_list:
            if 'yandex.ru' not in uid:
                continue

            if 'PIK_SYNCER' in uid:
                continue

            #Begin
            caldav_text = self.get_event_by_uid(uid)
            cd_helper = CaldavHelper(caldav_text)

            #Events properties
            summary = cd_helper.get_summary()
            organizer = cd_helper.get_org_from_main_body()

            if self.user_email not in organizer:
                self.delete_event_by_uid(uid)
                print(f'Delete {summary}')
            print('\n<==========================>\n')

    def delete_y_events_others_period(self):
        for uid in self.period_events_list:
            if 'yandex.ru' not in uid:
                continue

            #Begin
            caldav_text = self.get_event_by_uid(uid)
            cd_helper = CaldavHelper(caldav_text)

            #Events properties
            summary = cd_helper.get_summary()
            organizer = cd_helper.get_org_from_main_body()

            if self.user_email not in organizer:
                self.delete_event_by_uid(uid)
                print(f'Delete {summary}')
            print('\n<==========================>\n')