#!/usr/bin/env python3
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from httplib2 import Http
from oauth2client import file, client, tools
from pathlib import Path
import sys
import os
import datetime

APP_DIR = str(Path.home()) + '/.config/budget-cli/'
SPREADSHEET_ID_PATH = APP_DIR + 'spreadsheet.id'

# writes spreadsheet ID to file
def writeId(ssheetId):
    with open(SPREADSHEET_ID_PATH, 'w') as f:
        f.write(ssheetId)
    print("Spreadsheet ID has been set:", ssheetId)
    sys.exit(0)

# reads spreadsheet ID from file
def readId():
    try:
        with open(SPREADSHEET_ID_PATH) as f:
            return f.read()
    except:
        print("Spreadsheet ID not found. Set it using one of the following commands:", file=sys.stderr)
        print("budget id <SPREADSHEET_ID>\nbudget url <SPREADSHEET_URL>", file=sys.stderr)
        sys.exit(1)

def readRange(service, ssheetId, rangeName):
    try:
        return service.spreadsheets().values().get(spreadsheetId=ssheetId, range=rangeName).execute().get('values', [])
    except HttpError:
        print("Invalid spreadsheet ID: " + ssheetId + "\nSet it using one of the following commands:", file=sys.stderr)
        print("budget id <SPREADSHEET_ID>\nbudget url <SPREADSHEET_URL>", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    # validate command
    command = sys.argv[1]
    if command != 'id' and command != 'url' and command != 'expense' and command != 'income' and command != 'summary':
        print("Invalid command. Valid commands are 'id', 'url', 'summary', 'expense' and 'income'.", file=sys.stderr)
        sys.exit(1)
    arg = None if len(sys.argv) == 2 else sys.argv[2]

    # handle 'url' command
    if command == 'url': 
        start = arg.find("spreadsheets/d/")
        end = arg.find("/edit#")
        if start == -1 or end == -1:
            print("Invalid URL:", arg, file=sys.stderr)
            sys.exit(1)
        writeId(arg[(start + 15):end])
        sys.exit(0)

    # handle 'id' command
    if command == 'id':
        if arg == None:
            print("Spreadsheet ID:", readId())
        else:
            writeId(arg)
        sys.exit(0)

    # temporarily change working directory to read token.json & authorize
    initialDir = os.getcwd()
    os.chdir(APP_DIR)
    store = file.Storage('token.json')
    creds = store.get()
    service = build('sheets', 'v4', http=creds.authorize(Http()))
    os.chdir(initialDir)

    # read spreadsheet ID and get date
    ssheetId = readId()
    date = readRange(service, ssheetId, 'Summary!B2:E3')[0][0]

    # handle 'summary' command
    if command == 'summary':
        print("\n" + date + "\n=======================")
        print("Total Expense:", readRange(service, ssheetId, 'Summary!C16')[0][0])
        print("Total Income:", readRange(service, ssheetId, 'Summary!I16')[0][0])
        sys.exit(0)

    # remove leading & trailing whitespaces from input parameters if any
    entry = [e.strip() for e in arg.split(',')]

    # validate transaction if command is 'expense' or 'income'
    if len(entry) != 3 and len(entry) != 4:
        print("Invalid number of fields in transaction.", file=sys.stderr)
        sys.exit(1)
    if len(entry) is 3:
        print("Only 3 fields were specified. Assigning today to date field.")
        now = datetime.datetime.now()
        entry.insert(0, str(now)[:10])

    # fetch existing data in order to find the row index of the last transaction
    values = readRange(service, ssheetId, 'Transactions!C5:C74' if command == 'expense' else 'Transactions!H5:H74')
    rowIdx = 5 if not values else 5 + len(values)

    # add new transaction
    startCol = "B" if command == 'expense' else "G"
    endCol = "E" if command == 'expense' else "J"
    rangeName = "Transactions!" + startCol + str(rowIdx) + ":" + endCol + str(rowIdx)
    body = {'values': [entry]}
    result = service.spreadsheets().values().update(spreadsheetId=ssheetId, range=rangeName,
                                                    valueInputOption="USER_ENTERED", body=body).execute()
    print('{0} cells updated for {1}.'.format(result.get('updatedCells'), date))
