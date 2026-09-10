import re

with open("data/raw/habsos/habsos_data.zip", "r", encoding="utf-8", errors="replace") as f:
    html = f.read()

# Find all hrefs
links = re.findall(r'href="([^"]+)"', html)
print("=== ALL LINKS ===")
for l in links:
    print(" ", l)

# Find form actions
forms = re.findall(r'action="([^"]+)"', html)
print("\n=== FORM ACTIONS ===")
for f in forms:
    print(" ", f)

# Print snippet around "download"
idx = html.lower().find("download")
if idx >= 0:
    print("\n=== DOWNLOAD CONTEXT ===")
    print(html[max(0, idx-100):idx+400])
