"""Script to backup the /var/www/osTicket directory."""

import glob  # needed to read list of files in directory
import os  # needed for environement variable reading
import tarfile  # needed to make tar file of directory
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
DIRECTORY_TO_BACKUP = '/var/www/osTicket/'  # define the directory that will be backed up
FILENAME_PREFIX = 'osTicket directory backup-'
GOOGLE_DRIVE_FOLDER_NAME = 'osTicket web folder backups'

if __name__ == '__main__':
    with open('osTicketDirBackupLog.txt', 'w') as log:
        startTime = datetime.now()
        startTime = startTime.strftime('%H:%M:%S')
        print(f'INFO: Execution started at {startTime}')
        print(f'INFO: Execution started at {startTime}', file=log)

        # handle creating the Google API connection
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

        timestamp = datetime.now().strftime('%Y-%m-%d-%H:%M:%S')  # get the current date and time
        filename = FILENAME_PREFIX + timestamp + '.tar.gz'  # create a filename based on our prefix and timestamp

        print(f'INFO: Creating tar archive of folder {DIRECTORY_TO_BACKUP}, with filename "{filename}" this may take a while')
        print(f'INFO: Creating tar archive of folder {DIRECTORY_TO_BACKUP}, with filename "{filename}" this may take a while', file=log)
        with tarfile.open(filename, "w:gz") as tar:  # create a tar with our filename
            tar.add(DIRECTORY_TO_BACKUP, arcname=os.path.basename(DIRECTORY_TO_BACKUP))  # add the files from the directory to the tar

        print(f'INFO: Successfully created tar file, attempting to upload to Google drive folder named "{GOOGLE_DRIVE_FOLDER_NAME}"')
        print(f'INFO: Successfully created tar file, attempting to upload to Google drive folder named "{GOOGLE_DRIVE_FOLDER_NAME}"',file=log)
        nextPageFolderToken = ''
        while nextPageFolderToken is not None:
            folderQuery = f"'me' in owners and mimeType='application/vnd.google-apps.folder' and name='{GOOGLE_DRIVE_FOLDER_NAME}' and trashed=false"
            folder = drive.files().list(corpora='user',q=folderQuery,pageToken=nextPageFolderToken).execute()
            # print(files)
            nextPageFolderToken = folder.get('nextPageToken')  # retrieve the next page token from the response
            folder = folder.get('files',[])  # retrieve just the folder from the files part of the response
            if folder:
                folderID = folder[0].get('id')  # get the folder id from the response so we can use it in the next query to find files in that folder specifically
                # print(folderID)  # debug
                # Upload the file to the parent folder
                try:
                    parentsArray = []
                    parentsArray.append(folderID)
                    file_metadata = {'name': filename, 'parents': parentsArray}  # define metadata about the file, like its name and the parent folder
                    media = media = MediaFileUpload(filename=filename, mimetype='application/octet-stream', resumable=True)  # create the media body for the file, which is the file, file type, and wether it is resumable
                    uploadFile = drive.files().create(body=file_metadata, media_body=media, fields='id').execute()  # do the creation of the file using the bodies defined above
                    print(f'INFO: Backup file "{filename}" was uploaded to Google Drive folder with ID {folderID}, resulting file ID is {uploadFile.get("id")}')
                    print(f'INFO: Backup file "{filename}" was uploaded to Google Drive folder with ID {folderID}, resulting file ID is {uploadFile.get("id")}', file=log)

                except HttpError as er:   # catch Google API http errors, get the specific message and reason from them for better logging
                    status = er.status_code
                    details = er.error_details[0]  # error_details returns a list with a dict inside of it, just strip it to the first dict
                    print(f'ERROR {status} from Google API while uploading Google Drive file {filename} to parent folder ID {folderID}: {details["message"]}. Reason: {details["reason"]}')
                    print(f'ERROR {status} from Google API while uploading Google Drive file {filename} to parent folder ID {folderID}: {details["message"]}. Reason: {details["reason"]}', file=log)
                except Exception as er:
                    print(f'ERROR while uploading Google Drive file {filename} to parent folder ID {folderID}: {er}')
                    print(f'ERROR while uploading Google Drive file {filename} to parent folder ID {folderID}: {er}', file=log)

                # count the number of files in the parent folder, attempt to cull down to max file limit
                try:
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
                                driveFileStarred = files[i].get('starred')  # get the starred status
                                driveFileID = files[i].get('id')
                                drivefilename = files[i].get('name')
                                # print(f'DBUG: Found file named {drivefilename} with ID {driveFileID}, starred {driveFileStarred}')
                                if filesToDelete > 0:  # only look at the files while we still need to delete files
                                    if driveFileStarred == False:
                                        print(f'INFO: File {drivefilename} with ID {driveFileID} is not starred and will be deleted')
                                        print(f'INFO: File {drivefilename} with ID {driveFileID} is not starred and will be deleted', file=log)
                                        try:
                                            drive.files().delete(fileId=driveFileID).execute()
                                            filesToDelete-=1  # decrement the number of files still needing to be deleted
                                        except HttpError as er:   # catch Google API http errors, get the specific message and reason from them for better logging
                                            status = er.status_code
                                            details = er.error_details[0]  # error_details returns a list with a dict inside of it, just strip it to the first dict
                                            print(f'ERROR {status} from Google API while deleting Google Drive file {drivefilename} with ID {driveFileID}: {details["message"]}. Reason: {details["reason"]}')
                                            print(f'ERROR {status} from Google API while deleting Google Drive file {drivefilename} with ID {driveFileID}: {details["message"]}. Reason: {details["reason"]}', file=log)
                                        except Exception as er:
                                            print(f'ERROR while deleting Google Drive file {drivefilename}, {driveFileID}: {er}')
                                            print(f'ERROR while deleting Google Drive file {drivefilename}, {driveFileID}: {er}', file=log)
                            if filesToDelete > 0:  # if we got through every file and we werent able to delete enough, give an error
                                print(f'ERROR: Could not reduce down to maximum file count, still need to delete {filesToDelete} more')
                                print(f'ERROR: Could not reduce down to maximum file count, still need to delete {filesToDelete} more', file=log)
                        else:
                            print(f'DBUG: Current # of files in the folder is {len(files)} which does not exceed the max of {MAX_FILES_IN_FOLDER}, no files deleted')
                            print(f'DBUG: Current # of files in the folder is {len(files)} which does not exceed the max of {MAX_FILES_IN_FOLDER}, no files deleted', file=log)

                except HttpError as er:   # catch Google API http errors, get the specific message and reason from them for better logging
                    status = er.status_code
                    details = er.error_details[0]  # error_details returns a list with a dict inside of it, just strip it to the first dict
                    print(f'ERROR {status} from Google API while fetching files in the Drive folder {GOOGLE_DRIVE_FOLDER_NAME}: {details["message"]}. Reason: {details["reason"]}')
                    print(f'ERROR {status} from Google API while fetching files in the Drive folder {GOOGLE_DRIVE_FOLDER_NAME}: {details["message"]}. Reason: {details["reason"]}', file=log)
                except Exception as er:
                    print(f'ERROR: {er}')
                    print(f'ERROR: {er}', file=log)

                # delete the created tar file from the local machine so we dont end up out of space just from local backups
                try:
                    os.remove(filename)
                    print('DBUG: Local tar file was successfully deleted after upload')
                    print('DBUG: Local tar file was successfully deleted after upload', file=log)
                except Exception as er:
                    print(f'ERROR while deleting local tar file after upload: {er}')
                    print(f'ERROR while deleting local tar file after upload: {er}', file=log)

            else:  # if there were no folders found matching the query
                print(f'ERROR: No folder found for "{GOOGLE_DRIVE_FOLDER_NAME}, make sure the folder exists and is owned by the user')
                print(f'ERROR: No folder found for "{GOOGLE_DRIVE_FOLDER_NAME}, make sure the folder exists and is owned by the user', file=log)
        endTime = datetime.now()
        endTime = endTime.strftime('%H:%M:%S')
        print(f'INFO: Execution ended at {endTime}')
        print(f'INFO: Execution ended at {endTime}', file=log)
