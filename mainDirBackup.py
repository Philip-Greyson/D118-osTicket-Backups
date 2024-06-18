"""Script to backup the /var/www/osTicket directory."""

import glob  # needed to read list of files in directory
import os  # needed for environement variable reading

import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/admin.directory.user', 'https://www.googleapis.com/auth/admin.directory.group', 'https://www.googleapis.com/auth/admin.directory.group.member', 'https://www.googleapis.com/auth/apps.licensing','https://www.googleapis.com/auth/drive']

MAX_FILES_IN_FOLDER = 3

if __name__ == '__main__':
    with open('osTicketDirBackupLog.txt', 'w') as log:
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        # create drive api client
        drive = build('drive', 'v3', credentials=creds)

        nextPageFolderToken = ''
        while nextPageFolderToken is not None:
            folder = drive.files().list(corpora='user',q="'me' in owners and mimeType='application/vnd.google-apps.folder' and name='Test Script' and trashed=false",pageToken=nextPageFolderToken).execute()
            # print(files)
            nextPageFolderToken = folder.get('nextPageToken')  # retrieve the next page token from the response
            folder = folder.get('files',[])  # retrieve just the folder from the files part of the response
            if folder:
                folderID = folder[0].get('id')  # get the folder id from the response so we can use it in the next query to find files in that folder specifically
                print(folderID)
                nextPageFileToken = ''
                while nextPageFileToken is not None:
                    fileQuery = f"'me' in owners and '{folderID}' in parents and trashed=false"  # define the query to include files we own in the folder found above
                    files = drive.files().list(corpora='user',orderBy='createdTime desc',fields="nextPageToken, files(id, name, ownedByMe, createdTime, starred)",q=fileQuery,pageToken=nextPageFileToken).execute()
                    # print(files)
                    nextPageFileToken = files.get('nextPageToken')  # retrieve the next page token from the response
                    files = files.get('files',[])  # retrieve just the files from the response
                    if len(files) > MAX_FILES_IN_FOLDER:
                        filesToDelete = len(files) - MAX_FILES_IN_FOLDER
                        print(f'WARN: Number of files in the folder is {len(files)} which is over the limit of {MAX_FILES_IN_FOLDER}, the oldest {filesToDelete} file(s) will be deleted unless starred')
                        print(f'WARN: Number of files in the folder is {len(files)} which is over the limit of {MAX_FILES_IN_FOLDER}, the oldest {filesToDelete} file(s) will be deleted unless starred', file=log)

                        for i in range(len(files)-1, -1, -1):  # iterate from the oldest file down to the newest. needs the -1 as the end since its non inclusive
                            if filesToDelete > 0:  # only look at the files while we still need to delete files
                                fileStarred = files[i].get('starred')  # get the starred status
                                fileID = files[i].get('id')
                                fileName = files[i].get('name')
                                print(f'DBUG: Found file named {fileName} with ID {fileID}, starred {fileStarred}')
                                if fileStarred == False:
                                    print(f'INFO: File {fileName} with ID {fileID} is not starred and will be deleted')
                                    print(f'INFO: File {fileName} with ID {fileID} is not starred and will be deleted', file=log)
                                    filesToDelete-=1  # decrement the number of files still needing to be deleted
                        if filesToDelete > 0:  # if we got through every file and we werent able to delete enough, give an error
                            print(f'ERROR: Could not reduce down to maximum file count, still need to delete {filesToDelete} more')
                            print(f'ERROR: Could not reduce down to maximum file count, still need to delete {filesToDelete} more', file=log)
