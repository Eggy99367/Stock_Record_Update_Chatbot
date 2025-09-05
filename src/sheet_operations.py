from .service import Create_Service
import os
import json

class SheetOperations:
    def __init__(self, client_secret):
        creds_dict = json.loads(client_secret)
        with open("google_service_account.json", "w") as f:
            json.dump(creds_dict, f, indent=4)
        self.ss_service = Create_Service("google_service_account.json", 'sheets', 'v4', ['https://www.googleapis.com/auth/spreadsheets'])
        self.drive_service = Create_Service("google_service_account.json", 'drive', 'v3', ['https://www.googleapis.com/auth/drive'])
        os.remove("google_service_account.json")

    def check_sheet_exist(self, sheet_id, sheet_name):
        try:
            sheet = self.ss_service.spreadsheets().get(
                spreadsheetId=sheet_id,
                ranges=sheet_name
            ).execute()
            return True
        except Exception as e:
            # print(f"Error checking sheet existence: {e}")
            return False

    def edit_cell(self, sheet_id, ss_name, index, new_value):
        range_name = f'{ss_name}!{chr(65 + index[1])}{index[0] + 1}'
        print(range_name)
        request_body = {
            'values': [[new_value]]
        }
        response = self.ss_service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=request_body
        ).execute()