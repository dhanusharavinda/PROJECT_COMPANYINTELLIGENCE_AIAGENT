import os
import requests
from dotenv import load_dotenv

load_dotenv()
HOST = os.environ["DATABRICKS_HOST"]
TOKEN = os.environ["DATABRICKS_TOKEN"]
GENIE_SPACE_ID = os.environ["GENIE_SPACE_ID"]
headers = {"Authorization": f"Bearer {TOKEN}"}

print("Test 1: Databricks connectivity")
resp = requests.get(f"{HOST}/api/2.0/clusters/list", headers=headers)
print(f"  Status {resp.status_code}", "OK" if resp.status_code == 200 else "CHECK TOKEN")

print("Test 2: Genie MCP endpoint")
resp = requests.get(f"{HOST}/api/2.0/mcp/genie/{GENIE_SPACE_ID}", headers=headers)
print(f"  Status {resp.status_code}", "OK" if resp.status_code in (200, 405, 406) else "CHECK URL")

print("Test 3: Vector Search MCP endpoint")
resp = requests.get(f"{HOST}/api/2.0/mcp/vector-search/nimbus/silver", headers=headers)
print(f"  Status {resp.status_code}", "OK" if resp.status_code in (200, 405, 406) else "CHECK URL")