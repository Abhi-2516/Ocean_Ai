# generate_script_local.py (safe, reads testcase with utf-8-sig)
from backend.agent_tools import generate_selenium_script_html
import json, sys, os
# load testcase (supports BOM)
tc_path = "tests/sample_testcase.json"
if not os.path.exists(tc_path):
    print("ERROR: testcase file not found:", tc_path)
    sys.exit(1)
with open(tc_path, "r", encoding="utf-8-sig") as f:
    tc = json.load(f)
# load example.txt as fallback "HTML"
html_path = "assets/example.txt"
if not os.path.exists(html_path):
    print("ERROR: assets/example.txt not found at", html_path)
    sys.exit(1)
with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()
# set html_path url (update if you later create checkout.html)
file_url = "file:///D:/a last chancce/Ocean.AI/assets/checkout.html"
script = generate_selenium_script_html(tc, html, file_url)
out_path = "tests/generated_test.py"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(script)
print("WROTE", out_path)
