import os
import requests
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Setup
api_key = os.getenv("PERPLEXITY_API_KEY")
url = "https://api.perplexity.ai/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

print("🔐 Loaded Perplexity API Key:", "FOUND" if api_key else "MISSING")
print("🔗 Requesting URL:", url)
print("🧾 Headers:", headers)
print("📦 Request body:")
print(json.dumps({
    "model": "sonar-medium-chat",
    "messages": [
        {
            "role": "user",
            "content": (
                "List 3 upcoming major signage or print expos in 2025 in CSV format:\n\n"
                "name,url,relevance_score,reasoning\n"
                "Example Expo,https://example.com,8.5,Example description of relevance.\n"
            )
        }
    ]
}, indent=2))

# Prepare request body
body = {
    "model": "sonar",
    "messages": [
        {
            "role": "user",
            "content": (
                "List 3 upcoming major signage or print expos in 2025 in CSV format:\n\n"
                "name,url,relevance_score,reasoning\n"
                "Example Expo,https://example.com,8.5,Example description of relevance.\n"
            )
        }
    ]
}

# Run test
try:
    print("\n🚀 Sending request to Perplexity API...")
    response = requests.post(url, headers=headers, json=body)
    response.raise_for_status()
    print("✅ Success! Status Code:", response.status_code)
    print("📥 Response JSON:")
    print(json.dumps(response.json(), indent=2))

except requests.exceptions.HTTPError as e:
    print("❌ HTTPError:", str(e))
    print("📄 Response Text:")
    print(response.text)

except Exception as ex:
    print("❌ Exception:", str(ex))
