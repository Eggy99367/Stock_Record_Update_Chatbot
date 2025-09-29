# Stock Record Update Chatbot

A chatbot system that helps users update and query stock records through the **LINE Messaging API**, with data stored in **Google Sheets** instead of a traditional database.  
Users can add, update, and query stock records directly by chatting with the bot, while administrators manage and review data in Google Sheets.

---

## Features

- Query current stock records  
- Add or update stock entries via LINE Bot chat commands  
- Validate user inputs (dates, numbers, formats)  
- Confirm updates through chatbot replies  
- Data stored in **Google Sheets** for easy access and management  
- Hosted on [Render](https://render.com/)  

---

## Project Structure

```
Stock_Record_Update_Chatbot/
├── bot/                 # LINE Bot logic, message handlers
├── api/                 # Backend API endpoints
├── gsheet/              # Google Sheets integration logic
├── config/              # Configuration files
├── requirements.txt     # Python dependencies
└── ...
```

---

## Getting Started (Local Development)

### Prerequisites
- Python 3.9+  
- LINE Messaging API credentials (Channel Secret & Channel Access Token)  
- A Google Cloud Project with a Service Account and Google Sheets API enabled  

### Installation

```bash
# Clone the repository
git clone https://github.com/Eggy99367/Stock_Record_Update_Chatbot.git
cd Stock_Record_Update_Chatbot

# Install dependencies
pip install -r requirements.txt
```

Run the development server:

```bash
python main.py
```

---

## Google Sheets Setup

1. Create a new Google Sheet (this will be your stock database).  
2. Enable the **Google Sheets API** in your Google Cloud Project.  
3. Use the service account created for this project:  
   ```
   stock-record-update-linebot@stock-record-update-linebot.iam.gserviceaccount.com
   ```  
4. Share the Google Sheet with this service account email and give it **Editor** permission.  
5. Note the **Sheet ID** (found in the Google Sheet URL).  

Update your `SHEET_ID` through Line chatbot.

---

## Deployment on Render

1. **Connect GitHub Repo to Render**  
   - Go to [Render Dashboard](https://dashboard.render.com/)  
   - Create a new **Web Service**  
   - Select your GitHub repository  

2. **Set Environment Variables**  
   In the Render dashboard, configure environment variables:  

   | Variable | Description | Example |
   |----------|-------------|---------|
   | `LINE_CHANNEL_SECRET` | LINE Bot channel secret | `xxxxxx` |
   | `LINE_CHANNEL_ACCESS_TOKEN` | LINE Bot access token | `xxxxxx` |
   | `GOOGLE_SERVICE_ACCOUNT_JSON` | Service account JSON file's content | `credentials.json` |

3. **Select Build & Start Commands**  
   - Build Command:  
     ```bash
     pip install -r requirements.txt
     ```  
   - Start Command:  
     ```bash
     gunicorn app:app
     ```  

4. **Deploy**  
   Render will build and deploy your chatbot.  
   The service URL will be generated automatically (e.g. `https://your-app.onrender.com`).  
