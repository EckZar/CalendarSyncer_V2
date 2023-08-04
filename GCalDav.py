import aiohttp
import asyncio
import datetime
import xml.etree.ElementTree as ET

from caldav_helper import CaldavHelper
from gAuth import get_access_token
from AsyncHTTPRequester import AsyncHttpRequester

DELTA_TO = 3
DELTA_FROM = 1


class GoogleCalDav:
    def __init__(self, user_email):
        self.asyncer = AsyncHttpRequester()
        self.service_from = 'google.com'
        self.service_to = 'yandex.ru'
        self.user_email: str = user_email
        self.base_url: str = 'https://apidata.googleusercontent.com'
        self.events_uids_list: list = []
        self.period_events_list: list = []
        self.headers = {
            'Authorization': f'Bearer {get_access_token(user_email)}'
        }


    async def get_event_by_uid(self, uid: str) -> str:
        await self.asyncer.create_session()
        url = f"{self.base_url}/caldav/v2/{self.user_email}/events/{uid}.ics"

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
            href = href_element.text.replace('%40', '@')
            if href not in self.period_events_list:
                uid = href.split('/')[-1].replace('.ics', '')
                self.period_events_list.append(uid)

    async def get_all_events(self) -> None:

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
        url = f"{self.base_url}/caldav/v2/{self.user_email}/events/{uid}_PIK_SYNCER.ics"
        self.headers['Content-Type'] = 'text/calendar'
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
        url = f"{self.base_url}/caldav/v2/{self.user_email}/events/{uid}.ics"
        response = await self.asyncer.make_request(
            url=url,
            method='DELETE',
            headers=self.headers
        )
        await self.asyncer.close_session()
        return response

    async def delete_y_events_others_period(self):
        for uid in self.period_events_list:
            if 'yandex.ru' not in uid:
                continue

            caldav_text = self.get_event_by_uid(uid)
            cd_helper = CaldavHelper(caldav_text)

            summary = cd_helper.get_summary()
            organizer = cd_helper.get_org_from_main_body()

            if self.user_email not in organizer:
                await self.delete_event_by_uid(uid)
                print(f'Delete {summary}')
            print('\n<==========================>\n')
