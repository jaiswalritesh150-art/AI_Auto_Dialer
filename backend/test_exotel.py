import os
import requests
from dotenv import load_dotenv

load_dotenv()

sid = os.getenv("EXOTEL_ACCOUNT_SID")
key = os.getenv("EXOTEL_API_KEY")
token = os.getenv("EXOTEL_API_TOKEN")

url = f"https://api.exotel.com/v2_beta/Accounts/{sid}/IncomingPhoneNumbers"

response = requests.get(
    url,
    auth=(key, token),
    timeout=15
)

print("HTTP:", response.status_code)
print(response.text[:1000])
