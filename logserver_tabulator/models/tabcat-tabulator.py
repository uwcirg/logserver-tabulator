import os.path
from pathlib import Path
from warnings import warn

from google.auth.transport.requests import Request
# from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import csv

import requests
import json
from jsonpath_ng import jsonpath, parse
import itertools
import re
import pandas as pd

TEST = True
TEST_FILE = "tabcat-test-data.json"
LOGSERVER_URL = "https://logs.acc.dev.cosri.cirg.washington.edu/events?select=event&event-%3Etags=eq.%22tabcat_detailed%22"

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.']
CREDENTIALS_FILE = 'credentials.json'
SCHEMA_FILE = 'MeasureReportSchema.yaml'

# The ID and range of a sample spreadsheet.
SPREADSHEET_ID = '1PXovisgLzbefPVe5Til7S7kbEtdMgY6LyolZLnr98Y8'
RANGE = ''

def getLogsFromFile(filename):
    with open(filename, 'r') as data:
        logs = json.loads(data)
        return logs

def getLogsFromLogServer(url):
    hed = {'Authorization': 'Bearer TOKEN'}
    response = requests.get(url, headers=hed)
    logs = json.loads(response.text)
    return logs

schema = {
    'denormalize': [
        '$.message.tabcat_json.eventLog',
    ],
    'columns': {
        'patientID': '$.message.patientID',
        'sessionID': '$.message.sessionID',
        'projectID': '$.message.projectID',
        'asctime': '$.asctime',
        'clinicsite': '$.',
        'startedAt': '$.message.tabcat_json.startedAt',
        'finishedAt': '$.message.tabcat_json.finishedAt',
        'totalCorrect': '$.message.tabcat_json.scores[?(title="TotalCorrect")].value',
        'totalErrors': '$.message.tabcat_json.scores[?(title="TotalErrors")].value',
        'trialNum': '$.message.tabcat_json.eventLog[{denormalize[0]}].state.trialNum',
        'practiceMode': '$.message.tabcat_json.eventLog[{denormalize[0]}].state.practiceMode',
        'now': '$.message.tabcat_json.eventLog[{denormalize[0]}]now',
        'choice': '$.message.tabcat_json.eventLog[{denormalize[0]}]interpretation.choice',
        'correct': '$.message.tabcat_json.eventLog[{denormalize[0]}]interpretation.correct',
        'stimuli': '$.message.tabcat_json.eventLog[{denormalize[0]}].state.stimuli',
        'numberCorrect': '$.message.tabcat_json.eventLog[{denormalize[0]}].state.numberCorrect',
        'secondsSinceStart': '$.message.tabcat_json.eventLog[{denormalize[0]}].state.secondsSinceStart',
    }
}

def getMatches(data, path, select='all'):
    matches = [match.value for match in parse(path).find(data)]
    if select == 'all':
        return matches
    if select == 'first':
        return matches[0]
    if select == 'last':
        return matches[-1]

def getSubIterations(data, schema):
    ranges = []
    for path in schema['denormalize']:
        rowWiseList = getMatches(data, path, select='first')
        if rowWiseList is list:
            ranges.append(range(len(rowWiseList)))
        else:
            raise TypeError(f'Object at denormalize path {path} must be a list')
    # build list of ranges from denormalized paths
    return itertools.product(*ranges)

def buildRow(element, schema, *iteration):
    # replace each {iter[n]} with corresponding iters value
    columnNames = schema['columns'].keys()
    row = dict.fromkeys(columnNames, None)
    for column in columnNames:
        path = schema[column]
        pathWithSubIter = path.format(denormalize=iteration)
        row[column] = getMatches(element, pathWithSubIter, select='first')
    return row

def applySchema(data, schema):
    # for each data, for each getIteration(), build row
    rows = []
    for element in data:
        denormalizedIterations = getSubIterations(data, schema)
        for iter in denormalizedIterations:
            rows.append(buildRow(element, schema, *iter))
    return rows

def logDataToDataFrame(data, schema):
    flattenedData = applySchema(data, schema)
    df = pd.DataFrame(flattenedData)
    return df

def upload(data):
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    creds = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE)

    # REMOVED IN FAVOR OF SERVICE ACCOUNT
    # creds = None
    # # The file token.json stores the user's access and refresh tokens, and is
    # # created automatically when the authorization flow completes for the first
    # # time.
    # if os.path.exists('token.json'):
    #     creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # # If there are no (valid) credentials available, let the user log in.
    # if not creds or not creds.valid:
    #     if creds and creds.expired and creds.refresh_token:
    #         creds.refresh(Request())
    #     else:
    #         flow = InstalledAppFlow.from_client_secrets_file(
    #             'credentials.json', SCOPES)
    #         creds = flow.run_local_server(port=0)
    #     # Save the credentials for the next run
    #     with open('token.json', 'w') as token:
    #         token.write(creds.to_json())

    try:
        service = build('sheets', 'v4', credentials=creds)
        # Call the Sheets API
        sheet = service.spreadsheets()

        # The A1 notation of the values to clear.
        data_range = RANGE

        clear_values_request_body = {
            # TODO: Add desired entries to the request body.
        }

        request = sheet.values().clear(spreadsheetId=SPREADSHEET_ID, range=data_range, body=clear_values_request_body)
        response = request.execute()
        print(response)
        #TODO Process clear response

        #OLD Get the values from the csv file
        # data = list(csv.reader(datafile))

        # How the input data should be interpreted.
        value_input_option = 'USER_ENTERED'

        value_range_body = {
            'range': data_range,
            'values': data,
        }

        request = sheet.values().update(spreadsheetId=SPREADSHEET_ID, range=data_range, valueInputOption=value_input_option, body=value_range_body)
        response = request.execute()
        print(response)
        #TODO Process update response

        #Sample code:
        # result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
        #                             range=table_name).execute()
        # values = result.get('values', [])

        # if not values:
        #     print('No data found.')
        #     return

        # print('Name, Major:')
        # for row in values:
        #     # Print columns A and E, which correspond to indices 0 and 4.
        #     print('%s, %s' % (row[0], row[4]))
    except HttpError as err:
        print(err)

def main():
    logs = None
    if TEST:
        logs = getLogsFromFile(TEST_FILE)
    else:
        logs = getLogsFromLogServer(LOGSERVER_URL)
    data = logDataToDataFrame(logs)
    upload(data)

if __name__ == '__main__':
    main()
