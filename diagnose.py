import os
import requests
from dotenv import load_dotenv

load_dotenv()
HOST = os.environ["DATABRICKS_HOST"]
TOKEN = os.environ["DATABRICKS_TOKEN"]
GENIE_SPACE_ID = os.environ["GENIE_SPACE_ID"]

print("HOST:", HOST)
print("GENIE_SPACE_ID:", GENIE_SPACE_ID)
print("TOKEN starts with:", TOKEN[:8], "... length:", len(TOKEN))

headers = {"Authorization": f"Bearer {TOKEN}"}

# Does the token work at all?
r = requests.get(f"{HOST}/api/2.0/preview/scim/v2/Me", headers=headers)
print("\nToken check (who am I):", r.status_code)
if r.status_code == 200:
    print("  Token works. User:", r.json().get("userName", "unknown"))
else:
    print("  Token problem:", r.text[:200])

# Does the Genie MCP endpoint exist?
genie_url = f"{HOST}/api/2.0/mcp/genie/{GENIE_SPACE_ID}"
print("\nGenie MCP URL:", genie_url)
r = requests.post(genie_url, headers=headers, json={})
print("  POST status:", r.status_code)
print("  Response:", r.text[:300])