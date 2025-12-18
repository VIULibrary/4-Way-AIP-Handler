

import os
import zipfile
import csv
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil
from tqdm import tqdm

# ======================
# CONFIG
# ======================
SOURCE_DIR = "/Volumes/Vintage-1/atmire2"
DEST_DIR = "/Volumes/Vintage-1/filtered_AIPs"
MANIFEST = "/Volumes/Vintage-1/atmire/manifest.csv"
CUTOFF_DATE = datetime(2024, 5, 4)  # all records AFTER (year, month, day)
COPY_FILES = True
MAX_WORKERS = 2  # HDD-friendly
# ======================

os.makedirs(DEST_DIR, exist_ok=True)

date_re = re.compile(r"<mods:dateAvailable[^>]*>(.*?)<\/mods:dateAvailable>", re.IGNORECASE)
handle_re = re.compile(r"<mods:identifier[^>]*>(.*?)<\/mods:identifier>", re.IGNORECASE)


def process_aip(filename):
    # --- Skip hidden Apple spotlight files) ---
    if filename.startswith("._"):
        return {
            "filename": filename,
            "handle": "",
            "dateAvailable": "",
            "size_bytes": 0,
            "status": "SKIPPED",
            "reason": "Hidden AppleDouble file"
        }

    aip_path = os.path.join(SOURCE_DIR, filename)
    file_size = os.path.getsize(aip_path)
    result = {
        "filename": filename,
        "handle": "",
        "dateAvailable": "",
        "size_bytes": file_size,
        "status": "SKIPPED",
        "reason": ""
    }

    try:
        with zipfile.ZipFile(aip_path, "r") as z:
            mets_name = next((n for n in z.namelist() if n.lower().endswith("mets.xml")), None)
            if not mets_name:
                result["reason"] = "No METS file"
                return result

            data = z.read(mets_name).decode("utf-8", errors="ignore")

            # extract date
            m_date = date_re.search(data)
            if not m_date:
                result["reason"] = "No dateAvailable"
                return result

            try:
                parsed_date = datetime.fromisoformat(m_date.group(1).replace("Z", ""))
            except Exception:
                result["reason"] = "Date parse error"
                return result

            result["dateAvailable"] = parsed_date.isoformat()

            # Early filter
            if parsed_date < CUTOFF_DATE:
                result["reason"] = f"Older than cutoff ({CUTOFF_DATE.date()})"
                return result

            # extract handle/identifier
            m_handle = handle_re.search(data)
            handle = m_handle.group(1).strip() if m_handle else filename
            result["handle"] = handle

            # copy file if enabled
            if COPY_FILES:
                shutil.copy2(aip_path, os.path.join(DEST_DIR, filename))

            result["status"] = "COPIED"
            result["reason"] = ""
            return result

    except Exception as e:
        result["reason"] = f"Error: {str(e)}"
        return result


def main():
    # --- Filter files upfront to skip apple spotlight files---
    files = [
        f for f in os.listdir(SOURCE_DIR)
        if f.endswith(".zip") and not f.startswith("._")
    ]

    results = []

    print(f"Processing {len(files)} AIPs with {MAX_WORKERS} workers…")

    # Use ThreadPoolExecutor (HDD-friendly) and tqdm for progress
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_aip, f): f for f in files}
        for fut in tqdm(as_completed(futures), total=len(futures), unit="AIP"):
            res = fut.result()
            results.append(res)

    # Write CSV manifest
    with open(MANIFEST, "w", newline="") as f:
        fieldnames = ["filename", "handle", "dateAvailable", "size_bytes", "status", "reason"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in results:
            w.writerow(row)

    copied = sum(1 for r in results if r["status"] == "COPIED")
    print("\n======== COMPLETE ========")
    print(f"Total AIPs copied: {copied  }")
    print(f"CSV manifest: {MANIFEST}")
    print(f"Filtered AIPs: {DEST_DIR}")


if __name__ == "__main__":
    main()
