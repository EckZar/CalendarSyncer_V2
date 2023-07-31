class CaldavHelper:
    def __init__(self, caldav_text):
        self.caldav_text = caldav_text
        self.check_for_byte_str()
        self.main_body = ''
        self.get_main_body()
        self.organizer = ''
        self.vevents_list = []
        self.summary = ''
        self.attendees = []
        self.rrule = ''
        self.dtstart = ''
        self.dtend = ''

    def check_for_byte_str(self):
        if isinstance(self.caldav_text, bytes):
            self.caldav_text = self.caldav_text.decode('utf-8')

    def get_summary(self, caldav_text=None) -> str:
        if caldav_text is None:
            caldav_text =self.caldav_text
        start = caldav_text.find('SUMMARY')
        end = caldav_text.find('\n', start)
        return self.caldav_text[start:end]

    def get_starttime(self) -> str:
        start = self.caldav_text.find('DTSTART')
        end = self.caldav_text.find('\n', start)
        text = self.caldav_text[start:end]
        return text

    def get_endtime(self) -> str:
        start = self.caldav_text.find('DTEND')
        end = self.caldav_text.find('\n', start)
        text = self.caldav_text[start:end]
        return text

    def get_main_body(self) -> str:
        start = self.caldav_text.find('BEGIN:VEVENT')
        end = self.caldav_text.find('END:VEVENT', start)
        self.main_body = self.caldav_text[start:end+10]

    def get_org_from_main_body(self):
        start = self.caldav_text.find('ORGANIZER')
        end = self.caldav_text.find('\n', start)
        return self.caldav_text[start:end]

    def get_organizer(self, caldav_text=None):
        if caldav_text is None:
            caldav_text = self.caldav_text
        start = caldav_text.find('ORGANIZER')
        end = caldav_text.find('\n', start)
        organizer = caldav_text[start:end]
        self.organizer = organizer
        return organizer

    def is_reccurences(self):
        if 'RECURRENCE-ID' in self.caldav_text:
            return True
        else:
            return False

    def get_rrule(self):
        start = self.caldav_text.find('RRULE')
        end = self.caldav_text.find('\n', start)
        return self.caldav_text[start:end]

    def get_attendees(self, vevent=None):
        if vevent is None:
            vevent = self.main_body

        list = []
        while 'ATTENDEE' in vevent:
            start = vevent.find('ATTENDEE')
            end = vevent.find('\n', start)
            attendee = vevent[start:end - 1]
            list.append(attendee)
            vevent = vevent[end:]
        self.attendees = list
        return list