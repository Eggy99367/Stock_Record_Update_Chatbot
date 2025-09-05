from flask import Flask, request, abort
from dotenv import load_dotenv
import os
import json
from google.oauth2.service_account import Credentials

from linebot import LineBotApi
from linebot.v3.webhook import WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, TemplateSendMessage, ButtonsTemplate, MessageAction
from src.service import Create_Service
from src.sheet_operations import SheetOperations

app = Flask(__name__)
load_dotenv()
WEBHOOK_HANDLER = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
LINE_BOT_API = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

# SS_SERVICE = Create_Service('sheets', 'v4', ['https://www.googleapis.com/auth/spreadsheets'])
# DRIVE_SERVICE = Create_Service('drive', 'v3', ['https://www.googleapis.com/auth/drive'])
sheet_ops = SheetOperations(os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"))
# load user data
USER_DATA_FILE = 'user_data.json'
if os.path.exists(USER_DATA_FILE):
    with open(USER_DATA_FILE, 'r') as f:
        user_data = json.load(f)
else:
    user_data = {}
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(user_data, f)

def save_user_data():
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(user_data, f)

@app.route("/", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        WEBHOOK_HANDLER.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@WEBHOOK_HANDLER.add(MessageEvent, message=TextMessage)
def handle_message(event):
    message = event.message.text
    user_id = event.source.user_id

    print(f"{user_id}: {message}")
    if user_id not in user_data:
        user_data[user_id] = {
            "state": "message",
            "prod": None,
            "name": None,
            "email": None,
            "phone": None,
            "quantity": None
        }
        save_user_data()
    if message == "設定試算表":
        user_data[user_id]["state"] = "set_spreadsheet_id"
        message = "請輸入試算表ID"
    elif user_data[user_id]["state"] == "set_spreadsheet_id":
        user_data[user_id]["sheet_id"] = message
        user_data[user_id]["state"] = "set_sheet_name"
        save_user_data()
        message = f"已設定試算表ID為: {message}\n\n請接著輸入工作表名稱"
    elif user_data[user_id]["state"] == "set_sheet_name":
        user_data[user_id]["sheet_name"] = message
        user_data[user_id]["state"] = "message"
        save_user_data()
        message = f"已設定工作表名稱為: {message}\n\n可以開始更新了!"
    elif message.startswith("新增交易紀錄"):
        if "sheet_id" not in user_data[user_id] or "sheet_name" not in user_data[user_id]:
            message = "請先設定試算表ID和工作表名稱，輸入「設定試算表」開始設定"
        else:
            user_data[user_id]["state"] = "add_trade_record"
            save_user_data()
            message = ("請輸入股票代碼:")
    elif user_data[user_id]["state"] == "add_trade_record":
        user_data[user_id]["trade_record"] = {"code": message}
        user_data[user_id]["state"] = "set_trade_option"
        save_user_data()
        message = TemplateSendMessage(
            alt_text="選擇交易選項",
            template=ButtonsTemplate(
                text = "請選擇交易選項: [買入/賣出]",
                actions = [
                    MessageAction(
                        label = "買入",
                        text = "買入"
                    ),
                    MessageAction(
                        label = "賣出",
                        text = "賣出"
                    )
                ]
            )
        )
    elif user_data[user_id]["state"] == "set_trade_option":
        if message not in ["買入", "賣出"]:
            message = "交易選項錯誤，請輸入「買入」或「賣出」"
        else:
            user_data[user_id]["trade_record"]["option"] = message
            user_data[user_id]["state"] = "set_trade_quantity"
            message = "請輸入交易數量:"
            save_user_data()
    elif user_data[user_id]["state"] == "set_trade_quantity":
        try:
            quantity = int(message)
            if quantity < 0:
                raise ValueError
            user_data[user_id]["trade_record"]["quantity"] = quantity
            user_data[user_id]["state"] = "set_trade_price"
            message = "請輸入交易價格:"
            save_user_data()
        except ValueError:
            message = "交易數量錯誤，請輸入正整數"
    elif user_data[user_id]["state"] == "set_trade_price":
        try:
            price = float(message)
            if price <= 0:
                raise ValueError
            user_data[user_id]["trade_record"]["price"] = price
            record = user_data[user_id]["trade_record"]

            

            message = (f"已新增交易紀錄:\n股票代碼: {record['code']}\n交易選項: {record['option']}\n"
                          f"交易數量: {record['quantity']}\n交易價格: {record['price']}")
            message = TemplateSendMessage(
            alt_text="確認交易紀錄",
            template=ButtonsTemplate(
                text = "請確認交易紀錄是否正確:\n"
                        f"股票代碼: {record['code']}\n"
                        f"交易選項: {record['option']}\n"
                        f"交易數量: {record['quantity']}\n"
                        f"交易價格: {record['price']}",
                actions = [
                    MessageAction(
                        label = "確認",
                        text = "確認"
                    ),
                    MessageAction(
                        label = "取消",
                        text = "取消"
                    )
                ]
            )
        )
            user_data[user_id]["state"] = "confirm_trade"
            user_data[user_id].pop("trade_record", None)
            save_user_data()
        except ValueError:
            message = "交易價格錯誤，請輸入正數"

    # cmd = message.split()[0]
    reply_msg(event.reply_token, message)

def reply_msg(reply_token, message):
    if type(message) == str:
        LINE_BOT_API.reply_message(reply_token, TextSendMessage(text=message))
    else:
        LINE_BOT_API.reply_message(reply_token, message)





if __name__ == "__main__":
    print(sheet_ops.check_sheet_exist('1BIo33P4uYqxXZRwuktu2dQObOYDhOLo-ACjRfVAapBk', '登錄交易紀錄'))
    print(sheet_ops.check_sheet_exist('1BIo33P4uYqxXZRwuktu2dQObOYDhOLo-ACjRfVAapBk', '出入金紀錄'))
    # app.run()
    # edit_cell('1BIo33P4uYqxXZRwuktu2dQObOYDhOLo-ACjRfVAapBk', 'Vincent', (0, 0), "TEST")
    pass