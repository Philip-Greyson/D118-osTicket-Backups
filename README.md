# # D118-osTicket-Backups

These scripts uploads archives of the osTicket directory and database to Google Drive folders for an "off-site" backup solution.

## Overview

These scripts are a fairly quick and dirty backup solution for the osTicket database and install folder. They use the Google API to upload to a defined folder name, and will delete the oldest non-starred files when there are more than a defined max number of files in that folder, in order to not take up infinite storage space. The directory backup creates a compressed tar file to be uploaded, while the database backup just uses a MySQL dump to generate a .sql file.

## Requirements

The following Python libraries must be installed on the host machine (links to the installation guide):

- [Python-Google-API](https://github.com/googleapis/google-api-python-client#installation)

In addition, an OAuth credentials.json file must be in the same directory as the overall script. This is the credentials file you can download from the Google Cloud Developer Console under APIs & Services > Credentials > OAuth 2.0 Client IDs. Download the file and rename it to credentials.json. When the program runs for the first time, it will open a web browser and prompt you to sign into a Google account. Based on this login it will generate a token.json file that is used for authorization. Since these scripts run on the osTicket server which likely does not have a browser, it will instead show a link in the output you can copy/paste to a different machine with a browser to complete the sign-in process. When the token expires it should auto-renew unless you end the authorization on the account or delete the credentials from the Google Cloud Developer Console. One credentials.json file can be shared across multiple similar scripts if desired.
There are full tutorials on getting these credentials from scratch available online. But as a quickstart, you will need to create a new project in the Google Cloud Developer Console, and follow [these](https://developers.google.com/workspace/guides/create-credentials#desktop-app) instructions to get the OAuth credentials, and then enable APIs in the project (the Admin SDK API is used in this project).

The script will attempt to upload the files to the user who has been authorized through the token process described above, and so they need to own the folders to match whatever is defined in `GOOGLE_DRIVE_FOLDER_NAME`

The following Environment Variables must be set on the machine running the database backup script:

- OSTICKET_HOST (likely localhost if you are running it on the osTicket server)
- OSTICKET_USERNAME
- OSTICKET_PASSWORD
- OSTICKET_DB_NAME

These are fairly self-explanatory and are simply the information about the database that is then used to create the MySQL dump. You can edit these to just directly include the information if you do not wish to use environment variables.

## Customization

Both the database and directory backup scripts are fairly simple, with a few constants you can change:

- As noted above, `GOOGLE_DRIVE_FOLDER_NAME` should be changed to the name of the Google Drive folder that is owned by the Google account used to sign in.
- `MAX_FILES_IN_FOLDER` is pretty self explanatory, the scripts will cull the oldest non-starred files after upload of the new file in order to get down to this max number of files.
- `FILENAME_PREFIX` is just the text string that will precede the timestamp on the filename
- `SCRIPT_DIRECTORY` is the full path to the directory where the script runs (by default assuming you clone the git repo into the scripts folder inside a typical osTicket install), which is needed because cron jobs by default run in the home folder of their user, which means stuff like the token/credentials file will not be found unless their full path is defined.
- `DIRECTORY_TO_BACKUP` is used to define the directory path that is added to the .tar.gz archive for the directory backup script. By default, this is /var/www/osTicket/, but it could be changed to be any directory on the system
- If you want to back up more than one directory, I would make a copy of the script renamed to something else and edit it to have different values of the above constants, then just call the copy. This can be done with as many directories as you want to back up, while uploading them to separate Drive folders with individual max file counts.
