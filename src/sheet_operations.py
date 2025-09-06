import os
import json
import re
import time
from googleapiclient.discovery import build
from google.oauth2 import service_account

def Create_Service(client_secret, api_name, api_version, *scopes):
    SCOPES = [scope for scope in scopes[0]]
    cred = service_account.Credentials.from_service_account_file(
        client_secret, scopes=SCOPES
    )
    try:
        service = build(api_name, api_version, credentials=cred)
        return service
    except Exception as e:
        print('Unable to connect', api_name, api_version, scopes, sep='-')
        print(e)
        return None

class SheetOperations:
    def __init__(self, client_secret):
        creds_dict = json.loads(client_secret)
        with open("google_service_account.json", "w") as f:
            json.dump(creds_dict, f, indent=4)
        self.ss_service = Create_Service("google_service_account.json", 'sheets', 'v4', ['https://www.googleapis.com/auth/spreadsheets'])
        self.drive_service = Create_Service("google_service_account.json", 'drive', 'v3', ['https://www.googleapis.com/auth/drive'])
        os.remove("google_service_account.json")

    def check_sheet_exist(self, spreadsheet_id, sheet_name):
        try:
            sheet = self.ss_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id,
                ranges=sheet_name
            ).execute()
            return True
        except Exception as e:
            # print(f"Error checking sheet existence: {e}")
            return False

    def get_sheet_id(self, spreadsheet_id, sheet_name):
        spreadsheet = self.ss_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        for s in spreadsheet.get("sheets", []):
            if s["properties"]["title"] == sheet_name:
                return s["properties"]["sheetId"]
        return None

    def insert_row(self, spreadsheet_id, sheet_id, row_number):
        request_body = {
            "requests": [
                {
                    "insertDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "ROWS",
                            "startIndex": row_number - 1,  # 0-based index
                            "endIndex": row_number
                        },
                        "inheritFromBefore": True
                    }
                }
            ]
        }

        self.ss_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=request_body
        ).execute()

    def edit_cell(self, spreadsheet_id, ss_name, index, new_value):
        range_name = f'{ss_name}!{chr(65 + index[1])}{index[0] + 1}'
        # print(range_name)
        request_body = {
            'values': [[new_value]]
        }
        response = self.ss_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=request_body
        ).execute()

    def edit_range(self, spreadsheet_id, ss_name, start_index, end_index, new_values):
        range_name = f'{ss_name}!{chr(65 + start_index[1])}{start_index[0] + 1}:{chr(65 + end_index[1])}{end_index[0] + 1}'
        request_body = {
            'values': new_values
        }
        response = self.ss_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=request_body
        ).execute()

    def get_range(self, spreadsheet_id, ss_name, start_index, end_index):
        range_name = f'{ss_name}!{chr(65 + start_index[1])}{start_index[0] + 1}:{chr(65 + end_index[1])}{end_index[0] + 1}'

        get_values = self.ss_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            majorDimension='ROWS',
            range=range_name
        ).execute()['values']

        return get_values

    def copy_range(self, spreadsheet_id, sheet_id,
                    start, end, dest, paste_type="PASTE_NORMAL"):
        start_row, start_col = start
        end_row, end_col = end
        dest_start_row, dest_start_col = dest
        requests = [
            {
                "copyPaste": {
                    "source": {
                        "sheetId": sheet_id,
                        "startRowIndex": start_row,
                        "endRowIndex": end_row,
                        "startColumnIndex": start_col,
                        "endColumnIndex": end_col
                    },
                    "destination": {
                        "sheetId": sheet_id,
                        "startRowIndex": dest_start_row,
                        "endRowIndex": dest_start_row + (end_row - start_row),
                        "startColumnIndex": dest_start_col,
                        "endColumnIndex": dest_start_col + (end_col - start_col)
                    },
                    "pasteType": paste_type
                }
            }
        ]

        body = {"requests": requests}
        self.ss_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()

        print(f"Copied range {start_row}-{end_row}, {start_col}-{end_col} to {dest_start_row}, {dest_start_col}")


    def row_of_ticker_symbol(self, spreadsheet_id, sheet_name, ticker_symbol):
        range_name = f'{sheet_name}!A:A'
        result = self.ss_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        values = result.get('values', [])
        for i, row in enumerate(values):
            if not row or not row[0]:
                continue
            row = re.split(r'\W+', row[0])[0]
            if row.upper() == ticker_symbol.strip().upper():
                return i
        return -1
    
    def add_trade_record(self, spreadsheet_id, overview_sheet_name, record_sheet_name, record):
        print("Adding trade record:", record)
        original_record = self.get_current_records(spreadsheet_id, overview_sheet_name, record["code"])
        range_name = f'{record_sheet_name}!A:E'
        original_amount  = float(original_record['股數']["value"]) if original_record and '股數' in original_record and original_record['股數']["value"] != "" else 0
        new_amount = round(original_amount + record['quantity'] if record['option'] == '+' else original_amount - record['quantity'], 4)
        original_cost = float(original_record['成本']["value"]) if original_record and '成本' in original_record and original_record['成本']["value"] != "" else 0
        new_cost = round(original_cost + (record['quantity'] * record['price']) if record['option'] == '+' else original_cost - (record['quantity'] * record['price']), 2)
        values = [[
            time.strftime("%Y/%m/%d %H:%M:%S"),
            record['code'],
            '買入' if record['option'] == '+' else '賣出',
            record['option'] + str(record['quantity']),
            record['price'],
            record['price'] * record['quantity'],
            original_amount,
            new_amount,
            original_cost,
            new_cost,
        ]]
        print(values)
        self.edit_range(spreadsheet_id, record_sheet_name, (1,0), (1,len(values[0]) - 1), values)

        self.edit_cell(spreadsheet_id, overview_sheet_name, (self.row_of_ticker_symbol(spreadsheet_id, overview_sheet_name, record["code"]), original_record['股數']['index']), new_amount)
        self.edit_cell(spreadsheet_id, overview_sheet_name, (self.row_of_ticker_symbol(spreadsheet_id, overview_sheet_name, record["code"]), original_record['成本']['index']), new_cost)

        new_record = self.get_current_records(spreadsheet_id, overview_sheet_name, record["code"])
        if str(new_record['股數']['value']) != str(new_amount) or str(new_record['成本']['value']) != str(new_cost):
            raise ValueError("Failed to update the trade record correctly.")

        col = [{"label": "股數", "value": "股數"}, {"label": "均價", "value": "平均價位"}, {"label": "現價", "value": "現價"}, {"label": "成本", "value": "成本"}, {"label": "現值", "value": "現值"}, {"label": "盈虧", "value": "目前盈虧"}, {"label": "佔比", "value": "佔比"}, {"label": "預定佔比", "value": "預定佔比"}, {"label": "可用餘額", "value": "可用餘額"}, {"label": "執行比率", "value": "執行率"}]
        text = f"代碼: {record['code']}"
        for c in col:
            text += f"\n{c['label']}: {original_record[c['value']]['value'] if c['value'] in original_record else '0'} -> {new_record[c['value']]['value'] if c['value'] in new_record else '0'}"
        return text

    def get_current_records(self, spreadsheet_id, ss_name, ticker_symbol):
        row_idx = self.row_of_ticker_symbol(spreadsheet_id, ss_name, ticker_symbol)
        if row_idx == -1:
            return None
        column = self.get_range(spreadsheet_id, ss_name, (0, 0), (0, 15))[0]
        data = self.get_range(spreadsheet_id, ss_name, (row_idx, 0), (row_idx, 15))[0]
        data = [{"index": idx, "value": value} for idx, value in enumerate(data)]
        record = dict(zip(column, data))
        return record