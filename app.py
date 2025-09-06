from flask import Flask, request, abort
from dotenv import load_dotenv
import os
import json
from google.oauth2.service_account import Credentials

# from linebot import LineBotApi, WebhookHandler
# from linebot.exceptions import InvalidSignatureError
# from linebot.models import TextSendMessage, TemplateSendMessage, ButtonsTemplate, MessageAction
from src.sheet_operations import SheetOperations
from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    TemplateMessage,
    ButtonsTemplate,
    MessageAction
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)
app = Flask(__name__)
load_dotenv()
# WEBHOOK_HANDLER = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
# LINE_BOT_API = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
CONFIGURATION = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
WEBHOOK_HANDLER = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

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

@WEBHOOK_HANDLER.add(MessageEvent, message=TextMessageContent)
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
    elif message == "新增交易紀錄":
        if "spreadsheet_id" not in user_data[user_id] or "sheet_name" not in user_data[user_id]:
            message = "請先設定試算表ID和工作表名稱，輸入「設定試算表」開始設定"
        else:
            user_data[user_id]["state"] = "add_trade_record"
            save_user_data()
            message = ("請輸入股票代碼:")
    elif user_data[user_id]["state"] == "set_spreadsheet_id":
        user_data[user_id]["spreadsheet_id"] = message
        user_data[user_id]["state"] = "set_sheet_name"
        save_user_data()
        message = f"已設定試算表ID為: {message}\n\n請接著輸入工作表名稱"
    elif user_data[user_id]["state"] == "set_sheet_name":
        user_data[user_id]["sheet_name"] = message
        user_data[user_id]["state"] = "message"
        save_user_data()
        message = f"已設定工作表名稱為: {message}\n\n可以開始更新了!"
    elif user_data[user_id]["state"] == "add_trade_record":
        if sheet_ops.row_of_ticker_symbol(user_data[user_id]["spreadsheet_id"], user_data[user_id]["sheet_name"], message) == -1:
            message = "表單中找不到股票代碼，請重新輸入股票代碼:\n(請確認是否已在試算表中新增該股票代碼)"
        else:
            user_data[user_id]["trade_record"] = {"code": message.strip().upper()}
            user_data[user_id]["state"] = "set_trade_option"
            save_user_data()

            message = TemplateMessage(
                alt_text="選擇交易選項",
                template=ButtonsTemplate(
                    text="請選擇交易選項: [買入/賣出]",
                    actions=[
                        MessageAction(label="買入", text="買入"),
                        MessageAction(label="賣出", text="賣出")
                    ]
                )
            )
    elif user_data[user_id]["state"] == "set_trade_option":
        if message not in ["買入", "賣出"]:
            message = "交易選項錯誤，請輸入「買入」或「賣出」"
        else:
            user_data[user_id]["trade_record"]["option"] = "+" if message == "買入" else "-"
            user_data[user_id]["state"] = "set_trade_quantity"
            message = "請輸入交易數量:"
            save_user_data()
    elif user_data[user_id]["state"] == "set_trade_quantity":
        try:
            quantity = int(message)
            if quantity <= 0:
                raise ValueError
            user_data[user_id]["trade_record"]["quantity"] = quantity
            user_data[user_id]["state"] = "set_trade_price"
            message = "請輸入交易價格:"
            save_user_data()
        except ValueError:
            message = "交易數量錯誤，請輸入正整數"
    elif user_data[user_id]["state"] == "set_trade_price":
        try:
            price = round(float(message), 2)
            if price < 0:
                raise ValueError
            user_data[user_id]["trade_record"]["price"] = price
            record = user_data[user_id]["trade_record"]
            message = TemplateMessage(
                alt_text="確認交易紀錄",
                template=ButtonsTemplate(
                    text="請確認交易紀錄是否正確:\n\n"
                            f"[{record['code']}] {'買入' if record['option'] == '+' else '賣出'} {record['option']}{record['quantity']} @${record['price']:.2f}",
                    actions=[
                        MessageAction(
                            label="確認",
                            text="確認"
                        ),
                        MessageAction(
                            label="取消",
                            text="取消"
                        )
                    ]
                )
            )
            user_data[user_id]["state"] = "confirm_trade"
            save_user_data()
        except ValueError:
            message = "交易價格錯誤，請輸入正數"
    elif user_data[user_id]["state"] == "confirm_trade":
        if message != "確認":
            message = "已取消新增交易紀錄"
        elif sheet_ops.row_of_ticker_symbol(user_data[user_id]["spreadsheet_id"], user_data[user_id]["sheet_name"], user_data[user_id]["trade_record"]["code"]) == -1:
            message = "表單中找不到股票代碼，已取消新增交易紀錄\n(請確認是否已在試算表中新增該股票代碼)"
        else:
            try:
                if "sheet_ids" not in user_data[user_id]:
                    user_data[user_id]["sheet_ids"] = {}
                    save_user_data()
                if "登錄交易紀錄" not in user_data[user_id]["sheet_ids"]:
                    sheet_id = sheet_ops.get_sheet_id(user_data[user_id]["spreadsheet_id"], "登錄交易紀錄")
                    if sheet_id is not None:
                        user_data[user_id]["sheet_ids"]["登錄交易紀錄"] = sheet_id
                        save_user_data()
                sheet_ops.insert_row(user_data[user_id]["spreadsheet_id"], user_data[user_id]["sheet_ids"]["登錄交易紀錄"], 3)
                print("row inserted")
                sheet_ops.copy_range(user_data[user_id]["spreadsheet_id"], user_data[user_id]["sheet_ids"]["登錄交易紀錄"], (1, 0), (2, 10), (2, 0))

                user_data[user_id]["record_details"] = sheet_ops.add_trade_record(user_data[user_id]["spreadsheet_id"], user_data[user_id]["sheet_name"], "登錄交易紀錄", user_data[user_id]["trade_record"])
                save_user_data()
                message = TemplateMessage(
                    alt_text="交易紀錄已新增成功!",
                    template=ButtonsTemplate(
                        text="交易紀錄已新增成功!",
                        actions=[
                            MessageAction(
                                label="詳細資訊",
                                text="詳細資訊"
                            ),
                            MessageAction(
                                label="繼續新增",
                                text="新增交易紀錄"
                            )
                        ]
                    )
                )
            except Exception as e:
                print(e)
                message = "新增交易紀錄失敗，請稍後再試"
        # user_data[user_id].pop("trade_record", None)
        user_data[user_id]["state"] = "record_added"
        save_user_data()
    elif user_data[user_id]["state"] == "record_added" and message == "詳細資訊":
        message = user_data[user_id]["record_details"]
    # cmd = message.split()[0]
    reply_msg(event.reply_token, message)

def reply_msg(reply_token, message):
    with ApiClient(CONFIGURATION) as api_client:
        line_bot_api = MessagingApi(api_client)
        if isinstance(message, str):
            messages = [TextMessage(text=message)]
        else:
            messages = [message]
            
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=messages
            )
        )




if __name__ == "__main__":
    app.run()
    pass