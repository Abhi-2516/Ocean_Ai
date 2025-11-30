# call_generate_script.py
import json, requests, pathlib, sys

# load testcase
tc_path = pathlib.Path("tests/sample_testcase.json")
if not tc_path.exists():
    print("Missing tests/sample_testcase.json")
    sys.exit(1)
tc = json.load(tc_path.open("r", encoding="utf-8-sig"))

# load checkout html
html_path = pathlib.Path("assets/checkout.html")
if not html_path.exists():
    print("Missing assets/checkout.html")
    sys.exit(1)
checkout_html = html_path.read_text(encoding="utf-8-sig")

payload = {
    "test_case": tc,
    "checkout_html": checkout_html,
    "html_path": "file:///D:/a last chancce/Ocean.AI/assets/checkout.html"
}

url = "http://127.0.0.1:8000/generate_script"
print("Posting to", url)
r = requests.post(url, json=payload, timeout=90)
print("STATUS:", r.status_code)
# print the body (pretty if possible)
try:
    print(json.dumps(r.json(), indent=2))
except Exception:
    print(r.text)

# if there is a script field, save it
try:
    data = r.json()
    if data and "script" in data and data["script"]:
        out = pathlib.Path("tests/generated_test_from_api.py")
        out.write_text(data["script"], encoding="utf-8-sig")
        print("WROTE", out)
except Exception:
    pass
