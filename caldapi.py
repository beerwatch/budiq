#!/usr/bin/env python

# from calendar_quickstart Google API example
from __future__ import print_function

from dateutil import parser, tz
from datetime import datetime

import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

class CaldAPI_tester(object):
  # If modifying these scopes, delete the file token.json.
  SCOPES = ["https://www.googleapis.com/auth/calendar.events.readonly"]
  TOKENFILE="creds/client_token.json"
  CREDSFILE="creds/client_secret_625853770585-7i4p6nnkffb2b5cb7kbtu7bv2bv0kiv4.apps.googleusercontent.com.json"
  CALENDAR="6o6npp6u15a3uhklvlj23hkqpo@group.calendar.google.com"

  def __init__(self):
    self.caldapi=CaldAPI(self.SCOPES,self.TOKENFILE,self.CREDSFILE,self.CALENDAR)

  def _test(self):
    events=self.caldapi.fetch(2)
    if not events:
        print('No upcoming events found.')
#    print(events)
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        tmStart=parser.parse(start)
        print(tmStart.strftime("%A, %B %d, %Y at %H:%M %p %Z"), event['summary'])


class CaldAPI(object):
  def __init__(self,SCOPES,TOKENFILE,CREDSFILE,CALENDAR):
    self.SCOPES=SCOPES
    self.TOKENFILE=TOKENFILE
    self.CREDSFILE=CREDSFILE
    self.CALENDAR=CALENDAR

  def fetch(self,num=5):
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    print ("Opening credentials")
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(self.TOKENFILE):
        creds = Credentials.from_authorized_user_file(self.TOKENFILE, self.SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(self.CREDSFILE, self.SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(self.TOKENFILE, 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)

    # Call the Calendar API
    now = datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    print('Getting the upcoming ',num,' events')
    events_result = service.events().list(calendarId=self.CALENDAR, timeMin=now,
                                        maxResults=num, singleEvents=True, #timeZone='utc',
                                        orderBy='startTime').execute()
    events = events_result.get('items', [])
    return events


if __name__ == '__main__':
    print('start')
    tester=CaldAPI_tester()
    tester._test()
    print('exit')