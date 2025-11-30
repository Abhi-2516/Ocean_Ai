# debug_generate.py
from backend.agent_tools import generate_selenium_script_html
import json, os, sys, pprint
tc_path = "tests/sample_testcase.json"
if not os.path.exists(tc_path):
    print("ERROR: testcase file missing:", tc_path)
    sys.exit(1)
tc = json.load(open(tc_path, "r", encoding="utf-8-sig"))
print("=== Loaded testcase keys ===")
print(list(tc.keys()))
print("=== Testcase preview ===")
pprint.pprint(tc, width=120)
html_path = "assets/example.txt"
if not os.path.exists(html_path):
    print("ERROR: assets/example.txt missing:", html_path)
    sys.exit(1)
html = open(html_path, "r", encoding="utf-8").read()
print("\\nCalling generate_selenium_script_html(...) now...")
script = generate_selenium_script_html(tc, html, "file:///D:/a last chancce/Ocean.AI/assets/example.txt")
print("TYPE OF RETURNED:", type(script))
if script is None:
    print("Generator returned None — possible causes:")
    print("- The input testcase may be missing required fields (Test_Steps, Test_ID, etc.)")
    print("- The generator logic found nothing to build on and returned None.")
else:
    print("Length of script:", len(script))
    print("\\n--- script head (first 800 chars) ---\\n")
    print(script[:800])
    with open("tests/generated_test_debug.py", "w", encoding='utf-8') as f:
        f.write(script)
    print("\\nWROTE tests/generated_test_debug.py")
