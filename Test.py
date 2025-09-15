import requests

# Replace with your actual production webhook URL
WEBHOOK_URL = "https://torrinkay.app.n8n.cloud/webhook-test/logLead"

# Sample test payload
payload = {
    "name": "Torrin Kay",
    "email": "amatorri847@gmail.com",
    "phone": "0412345678",
    "business": "Builders United",
    "inquiry": "Looking to streamline my business systems and website"
}

# Send POST request
response = requests.post(WEBHOOK_URL, json=payload)

# Output result
print("Status Code:", response.status_code)
print("Response:", response.text)