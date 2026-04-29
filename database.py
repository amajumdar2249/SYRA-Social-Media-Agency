import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()

CREDENTIALS_FILE = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "credentials.json")
# You will need to create a Google Sheet and name it here, or use its URL
SHEET_NAME = "AI_Social_Media_Queue" 

def save_to_sheet(topic: str, score: float, post_content: str) -> bool:
    """
    Saves the generated post and metadata to Google Sheets.
    """
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"⚠️ Google Sheets credentials file '{CREDENTIALS_FILE}' not found.")
        print("Skipping Google Sheets saving. Please download your service account JSON and place it here.")
        return False
        
    try:
        # Define the scope
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        # Add credentials to the account
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        
        # Authorize the clientsheet 
        client = gspread.authorize(creds)
        
        # Get the instance of the Spreadsheet
        sheet = client.open(SHEET_NAME).sheet1
        
        # Data to insert
        row_to_insert = [topic, str(score), post_content, "Pending Review"]
        
        # Insert row
        sheet.append_row(row_to_insert)
        print("📊 Successfully saved post to Google Sheets!")
        return True
        
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"❌ Spreadsheet '{SHEET_NAME}' not found. Make sure you shared it with the service account email.")
        return False
    except Exception as e:
        print(f"❌ Failed to save to Google Sheets: {e}")
        return False

if __name__ == "__main__":
    # Test
    save_to_sheet("Test Topic", 9.0, "Test content")
