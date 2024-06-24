"""Script to backup the sql database and upload to a Google Drive folder."""

import os  # needed for environement variable reading
import time as t
from datetime import *

import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/admin.directory.user', 'https://www.googleapis.com/auth/admin.directory.group', 'https://www.googleapis.com/auth/admin.directory.group.member', 'https://www.googleapis.com/auth/apps.licensing','https://www.googleapis.com/auth/drive']

MAX_FILES_IN_FOLDER = 14  # define the maximum number of files in the google drive folder. the oldest files will be deleted to reduce down to this number
FILENAME_PREFIX = 'osTicket database backup-'
GOOGLE_DRIVE_FOLDER_NAME = 'database backups'
SCRIPT_DIRECTORY = '/var/www/osTicket/scripts/D118-osTicket-Backups/'

DB_HOST = os.environ.get('OSTICKET_HOST')
DB_USER = os.environ.get('OSTICKET_USERNAME')
DB_PW = os.environ.get('OSTICKET_PASSWORD')
DB_NAME = os.environ.get('OSTICKET_DB_NAME')

if __name__ == '__main__':
    with open(SCRIPT_DIRECTORY + 'databaseBackupLog.txt', 'w') as log:
        startTime = datetime.now()
        startTime = startTime.strftime('%H:%M:%S')
        print(f'INFO: Execution started at {startTime}')
        print(f'INFO: Execution started at {startTime}', file=log)

        # handle creating the Google API connection
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        tokenPath = SCRIPT_DIRECTORY + 'token.json'
        credsPath = SCRIPT_DIRECTORY + 'credentials.json'
        if os.path.exists(tokenPath):
            creds = Credentials.from_authorized_user_file(tokenPath, SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(credsPath, SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(tokenPath, 'w') as token:
                token.write(creds.to_json())
        # create drive api client
        drive = build('drive', 'v3', credentials=creds)

        timestamp = datetime.now().strftime('%Y-%m-%d-%H:%M:%S')  # get the current date and time
        filename = SCRIPT_DIRECTORY + FILENAME_PREFIX + timestamp + '.sql'  # create a filename based on our prefix and timestamp
        dumpCMD = f'mysqldump -h {DB_HOST} -u {DB_USER} -p {DB_PW} {DB_NAME} > {filename}'  # create the SQL dump command to output to our given filename
        os.system(dumpCMD)  # execute the dump command on the system
