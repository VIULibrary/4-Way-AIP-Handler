import os
import zipfile
import re

SOURCE_DIR = "/Volumes/Vintage-1/atmire2"
CUTOFF_DATE = "2024-05-04"     #YYYY-MM-DD

date_re = re.compile(r"<mods:dateAvailable[^>]*>(.*?)<\/mods:dateAvailable>", re.IGNORECASE)

files = [f for f in os.listdir(SOURCE_DIR)
         if f.endswith(".zip") and not f.startswith("._")]

total = len(files)
print(f"Scanning {total} AIPs...\n")

matched = 0

for i, filename in enumerate(files, 1):
    print(f"[{i}/{total}] Checking {filename} ...", end="", flush=True)

    path = os.path.join(SOURCE_DIR, filename)

    try:
        with zipfile.ZipFile(path, "r") as z:
            mets = next((n for n in z.namelist() if n.lower().endswith("mets.xml")), None)
            if not mets:
                print(" no METS")
                continue

            data = z.read(mets).decode("utf-8", errors="ignore")

            m_date = date_re.search(data)
            if not m_date:
                print(" no dateAvailable")
                continue

            d = m_date.group(1)

            # Show the extracted date
            print(f" dateAvailable={d}")

            if d > CUTOFF_DATE:
                matched += 1

    except Exception as e:
        print(f" ERROR ({e})")

print("\n========== SUMMARY ==========")
print(f"Total AIPs scanned: {total}")
print(f"Dates newer than cutoff: {matched}")
