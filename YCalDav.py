import aiohttp
import asyncio
import requests
import yAuth
import datetime
import xml.etree.ElementTree as ET

from caldav_helper import CaldavHelper
from AsyncHTTPRequester import AsyncHttpRequester

DELTA_TO = 3
DELTA_FROM = 1


class YandexCalDav:
    def __init__(self, user_email):
        self.asyncer = AsyncHttpRequester()
        self.service_from = 'yandex.ru'
        self.service_to = 'google.com'
        self.user_email: str = user_email
        self.headers: dict = {
            'Authorization': f'OAuth {yAuth.get_access_token(user_email)}'
        }
        self.base_url: str = f'https://caldav.yandex.ru'
        self.calendars: list = []
        self.main_calendar: str = ''
        self.events_uids_list: list = []
        self.period_events_list: list = []
        self.events_list_others: list = []
        # self.get_calendars()
        # self.get_all_events()
        # self.get_events_from_to_dates()

    async def get_calendars(self):
        await self.asyncer.create_session()
        url = f'{self.base_url}/calendars/{self.user_email}'
        # response = requests.request("GET", url, headers=self.headers)
        # content = respone.content

        content = await self.asyncer.make_request(
            url=url,
            method='GET',
            headers=self.headers
        )
        await self.asyncer.close_session()

        if isinstance(content, (bytes, bytearray)):
            content = content.decode('utf-8')

        content = content.split('\n')

        for _ in content:
            if _ in self.calendars:
                continue
            self.calendars.append(_)

    async def get_main_calendar(self) -> None:
        await self.asyncer.create_session()

        url = f'{self.base_url}/calendars/{self.user_email}'
        # respone = requests.request("GET", url, headers=self.headers)

        response = await self.asyncer.make_request(
            url=url,
            method='GET',
            headers=self.headers
        )

        await self.asyncer.close_session()

        content = response
        if isinstance(content, (bytes, bytearray)):
            content = content.decode('utf-8')

        content = content.split('\n')

        self.main_calendar = content[2]

        return content[2]

    async def get_caldav_events(self) -> str:
        await self.asyncer.create_session()

        url = f"{self.base_url}{self.main_calendar}{self.user_email}"
        # return requests.request("GET", url, headers=self.headers).text

        response = await self.asyncer.make_request(
            url=url,
            method='GET',
            headers=self.headers
        )
        await self.asyncer.close_session()

        return response

    async def get_event_by_uid(self, uid: str) -> str:
        await self.asyncer.create_session()

        url = f"{self.base_url}{self.main_calendar}{uid}.ics"
        # return requests.request("GET", url, headers=self.headers).content.decode('utf-8')

        response = await self.asyncer.make_request(
            url=url,
            method='GET',
            headers=self.headers
        )
        await self.asyncer.close_session()

        return response

    async def get_events_from_to_dates(self, date_from=None, date_to=None) -> None:

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

        await self.asyncer.create_session()
        response = await self.asyncer.make_request(
            url=url,
            method='REPORT',
            headers=self.headers,
            data=payload
        )
        await self.asyncer.close_session()

        tree = ET.fromstring(response)

        for href_element in tree.iter("{DAV:}href"):
            href = href_element.text
            if href and href not in self.period_events_list:
                uid = href.split('/')[-1].replace('.ics', '')
                self.period_events_list.append(uid)

    async def get_all_events(self) -> None:

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

        await self.asyncer.create_session()
        response = await self.asyncer.make_request(
            url=url,
            method='REPORT',
            headers=self.headers,
            data=payload
        )
        await self.asyncer.close_session()

        tree = ET.fromstring(response)

        for href_element in tree.iter("{DAV:}href"):
            href = href_element.text
            if href and href not in self.events_uids_list:
                uid = href.split('/')[-1].replace('.ics', '')
                self.events_uids_list.append(uid)

    async def create_event(self, payload, uid):
        await self.asyncer.create_session()

        headers = self.headers
        headers['Content-Type'] = 'text/calendar'
        url = f'{self.base_url}{self.main_calendar}{uid}_PIK_SYNCER.ics'

        # return requests.request("PUT", url, headers=self.headers, data=payload)

        response = await self.asyncer.make_request(
            url=url,
            method='PUT',
            headers=self.headers,
            data=payload
        )

        await self.asyncer.close_session()

        return response

    async def delete_event_by_uid(self, uid):
        await self.asyncer.create_session()

        url = f"{self.base_url}{self.main_calendar}{uid}.ics"
        # return requests.request("DELETE", url, headers=self.headers)

        response = await self.asyncer.make_request(
            url=url,
            method='DELETE',
            headers=self.headers
        )

        await self.asyncer.close_session()

        return response

    async def delete_g_events_others_period(self):
        for uid in self.period_events_list:
            if 'google.com' not in uid:
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
