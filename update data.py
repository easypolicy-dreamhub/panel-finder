#!/usr/bin/env python3
"""
GE Panel Finder - monthly data refresh script.

Visits the Great Eastern panel locator page, finds the current links for
the three listings (Panel Hospital, Panel Specialist, Panel Clinic), downloads
them, extracts the data, and rewrites the JSON files under data/.

Run with: python3 scripts/update_data.py
Designed to run unattended inside GitHub Actions once a month.
"""

import json
import re
import sys
import difflib
import subprocess
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
import pdfplumber

LOCATOR_URL = "https://www.greateasternlife.com/my/en/customer-services/healthcare-services/healthcare-overview/locators-search-page.html"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TMP_DIR = Path("/tmp/panel-finder-pdfs")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

# ---------------------------------------------------------------------------
# Town -> (lat, lng) lookup, used to approximate "near me" sorting.
# ---------------------------------------------------------------------------
TOWN_COORDS = {
    "Alor Setar": (6.1210, 100.3690), "Ampang": (3.1500, 101.7622),
    "Batu Pahat": (1.8549, 102.9326), "Bayan Lepas": (5.2966, 100.2668),
    "Bintulu": (3.1729, 113.0414), "Bukit Mertajam": (5.3644, 100.4670),
    "Butterworth": (5.3991, 100.3638), "Cheras": (3.1073, 101.7414),
    "George Town": (5.4141, 100.3288), "Georgetown": (5.4141, 100.3288),
    "Ipoh": (4.5975, 101.0901), "Iskandar Puteri": (1.4241, 103.6357),
    "Johor Bahru": (1.4927, 103.7414), "Kajang": (2.9931, 101.7874),
    "Kangar": (6.4414, 100.1986), "Klang": (3.0333, 101.4500),
    "Kluang": (2.0311, 103.3186), "Kota Bahru": (6.1254, 102.2381),
    "Kota Kinabalu": (5.9804, 116.0735), "Kuala Lumpur": (3.1390, 101.6869),
    "Kuala Selangor": (3.3410, 101.2530), "Kuala Terengganu": (5.3302, 103.1408),
    "Kuantan": (3.8077, 103.3260), "Kuching": (1.5535, 110.3593),
    "Malacca": (2.1896, 102.2501), "Masai": (1.4661, 103.8963),
    "Melaka": (2.1896, 102.2501), "Miri": (4.3993, 113.9914),
    "Muar": (2.0442, 102.5689), "Nilai": (2.8145, 101.7965),
    "Nusajaya": (1.4241, 103.6357), "Pasir Gudang": (1.4726, 103.8998),
    "Penang": (5.4141, 100.3288), "Perai": (5.3833, 100.3833),
    "Petaling Jaya": (3.1073, 101.6067), "Puchong": (3.0219, 101.6172),
    "Rawang": (3.3186, 101.5772), "Segamat": (2.5142, 102.8159),
    "Senawang": (2.6667, 101.9500), "Seremban": (2.7297, 101.9381),
    "Seri Manjung": (4.2019, 100.6900), "Shah Alam": (3.0733, 101.5185),
    "Sibu": (2.2870, 111.8305), "Simpang Ampat": (5.2833, 100.4667),
    "Sitiawan": (4.2153, 100.6980), "Sri Gading": (1.9333, 102.9333),
    "Subang Jaya": (3.0567, 101.5851), "Sungai Petani": (5.6474, 100.4876),
    "Taiping": (4.8500, 100.7333), "Tanjung Bungah": (5.4667, 100.3000),
    "Teluk Intan": (4.0225, 101.0202), "Alor Gajah": (2.3785, 102.2088),
    "Ayer Itam": (5.4064, 100.2775), "Ayer Tawar": (4.1180, 100.7480),
    "Bahau": (2.8083, 102.4167), "Bangi": (2.9280, 101.7900),
    "Batu Berendam": (2.2515, 102.2650), "Batu Caves": (3.2379, 101.6840),
    "Batu Ferringhi": (5.4728, 100.2470), "Batu Gajah": (4.4650, 101.0390),
    "Batu Kawan": (5.2939, 100.4258), "Beranang": (2.8747, 101.8397),
    "Bidor": (4.1050, 101.2650), "Bukit Beruang": (2.2460, 102.2960),
    "Cameron Highlands": (4.4715, 101.3798), "Cyberjaya": (2.9213, 101.6559),
    "Dengkil": (2.8272, 101.6675), "Dungun": (4.7620, 103.4230),
    "Gelang Patah": (1.4270, 103.5960), "Gelugor": (5.3610, 100.3070),
    "Gemencheh": (2.5760, 102.2450), "Gopeng": (4.4560, 101.1830),
    "Gurun": (5.8140, 100.4610), "Hutan Melintang": (4.0430, 100.9950),
    "Jelebu": (2.9370, 101.8830), "Jelutong": (5.3970, 100.3080),
    "Jempol": (2.8600, 102.3670), "Jengka": (3.6110, 102.4130),
    "Jenjarom": (2.8080, 101.4270), "Jerantut": (3.9370, 102.3620),
    "Kahang": (2.1550, 103.2010), "Kampar": (4.3080, 101.1450),
    "Kamunting": (4.8570, 100.7290), "Kapar": (3.0940, 101.4180),
    "Karak": (3.4880, 101.9470), "Kemaman": (4.2350, 103.4170),
    "Keningau": (5.3380, 116.1610), "Kepala Batas": (5.5170, 100.4390),
    "Kota Tinggi": (1.7370, 103.9010), "Kuala Kangsar": (4.7710, 100.9370),
    "Kuala Krai": (5.5330, 102.2020), "Kuala Lipis": (4.1840, 102.0470),
    "Kuala Pilah": (2.7370, 102.2500), "Kulai": (1.6630, 103.6020),
    "Kulim": (5.3660, 100.5610), "Labis": (2.3870, 103.0210),
    "Lahad Datu": (5.0300, 118.3270), "Langkap": (4.2650, 100.9770),
    "Langkawi": (6.3500, 99.8000), "Limbang": (4.7500, 115.0080),
    "Lunas": (5.5860, 100.5330), "Mantin": (2.7290, 101.9260),
    "Marang": (5.2060, 103.2070), "Masjid Tanah": (2.3480, 102.0870),
    "Mentakab": (3.4830, 102.3540), "Mersing": (2.4310, 103.8400),
    "Nibong Tebal": (5.1670, 100.4830), "Pagoh": (2.1370, 102.7420),
    "Pantai Remis": (4.3960, 100.6560), "Papar": (5.7350, 115.9310),
    "Parit Buntar": (5.1210, 100.4900), "Pasir Mas": (6.0470, 102.1420),
    "Pekan": (3.4920, 103.3980), "Pekan Nanas": (1.5140, 103.4870),
    "Penampang": (5.9350, 116.1080), "Pokok Sena": (5.9420, 100.5100),
    "Pontian": (1.4870, 103.3900), "Port Dickson": (2.5220, 101.7960),
    "Ranau": (5.9540, 116.6580), "Rantau": (2.5940, 101.9820),
    "Raub": (3.7930, 101.8580), "Sandakan": (5.8402, 118.1179),
    "Sarikei": (2.1250, 111.5170), "Semenyih": (2.9450, 101.8420),
    "Semporna": (4.4820, 118.6110), "Senai": (1.5850, 103.6300),
    "Sepang": (2.7160, 101.7040), "Seri Kembangan": (3.0250, 101.7050),
    "Serian": (1.1670, 110.5830), "Skudai": (1.5340, 103.6570),
    "Sungai Bakap": (5.2280, 100.4870), "Sungai Besar": (3.6720, 100.9990),
    "Sungai Buloh": (3.2020, 101.5800), "Sungai Jawi": (5.2200, 100.4870),
    "Sungai Nibong": (5.3400, 100.3060), "Sungai Siput": (4.8250, 101.0870),
    "Tampin": (2.4680, 102.2300), "Tanah Merah": (5.8000, 102.1420),
    "Tangkak": (2.2680, 102.5510), "Tanjong Malim": (3.6880, 101.5170),
    "Tanjung Sepat": (2.6570, 101.5730), "Tanjung Tokong": (5.4460, 100.3070),
    "Tawau": (4.2440, 117.8910), "Telok Panglima Garang": (2.8500, 101.5330),
    "Temerloh": (3.4510, 102.4200), "Triang": (3.1590, 102.4720),
    "Tuaran": (6.1830, 116.2330), "Ulu Tiram": (1.5860, 103.8110),
    "W P Labuan": (5.2831, 115.2308), "Yong Peng": (2.0060, 103.0680),
    "Pulau Pinang": (5.4141, 100.3288),
}


def find_coord(town, address=""):
    if not town:
        town = ""
    coord = TOWN_COORDS.get(town.strip().title())
    if coord:
        return coord
    for t, c in TOWN_COORDS.items():
        if t.lower() in (town or "").lower() or t.lower() in address.lower():
            return c
    return (None, None)


# ---------------------------------------------------------------------------
# Step 1: find the three current PDF links on the locator page
# ---------------------------------------------------------------------------
LINK_LABELS = {
    "hospital": "Download Panel Hospital List",
    "specialist": "Download Panel Specialist List",
    "clinic": "Download Panel Clinic (for New Business",
}


def find_pdf_links():
    resp = requests.get(LOCATOR_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    links = {}
    for a in soup.find_all("a", href=True):
        text = " ".join(a.get_text(" ", strip=True).split())
        for key, label in LINK_LABELS.items():
            if label in text and key not in links:
                links[key] = urljoin(LOCATOR_URL, a["href"])
    missing = [k for k in LINK_LABELS if k not in links]
    if missing:
        raise RuntimeError(
            f"Could not find link(s) on locator page for: {missing}. "
            "The page layout may have changed."
        )
    return links


def download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    return dest


# ---------------------------------------------------------------------------
# Step 2a: parse the hospital PDF (pdftotext -layout, fixed line format)
# ---------------------------------------------------------------------------
STATES_SET = {
    "KEDAH", "PERLIS", "PENANG", "PERAK", "SELANGOR", "WILAYAH PERSEKUTUAN",
    "NEGERI SEMBILAN", "MELAKA", "JOHOR", "PAHANG", "TERENGGANU", "KELANTAN",
    "SABAH", "SARAWAK",
}


def parse_hospitals(pdf_path):
    raw = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        capture_output=True, text=True, check=True,
    ).stdout
    raw = raw.replace("\x0c", "\n")
    lines = raw.split("\n")

    current_state = None
    records = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s in STATES_SET:
            current_state = "Wilayah Persekutuan (KL)" if s == "WILAYAH PERSEKUTUAN" else s.title()
            continue
        if (s.startswith("Updated as of") or s.startswith("Notes") or
                re.match(r"^\d\.\s", s) or s.startswith("Great Eastern") or
                s.startswith("NO.")):
            continue
        m = re.match(
            r"^(\d+)\s{2,}(.+?)\s{2,}(.+?)\s{2,}(\d[\d\- ]{6,}\d)\s{2,}(Yes|None Upon Admission)\s*$",
            line,
        )
        if m:
            num, name, addr, tel, deposit = m.groups()
            records.append({
                "no": int(num), "name": name.strip(), "address": addr.strip(),
                "tel": tel.strip(), "deposit": deposit.strip(), "state": current_state,
            })
        elif s.startswith("(") and records:
            records[-1]["name"] += " " + s
        elif records:
            records[-1]["address"] += " " + s

    for r in records:
        r["address"] = " ".join(r["address"].split())
        r["name"] = " ".join(r["name"].split())
        m = re.search(r"(\d{5})\s+([A-Za-z .'\u2019]+?)(?:,|$)", r["address"])
        town = m.group(2).strip() if m else None
        lat, lng = find_coord(town, r["address"])
        r["town"], r["lat"], r["lng"] = town, lat, lng

    return records


# ---------------------------------------------------------------------------
# Step 2b: parse the specialist PDF (plain pdftotext, one row per line)
# ---------------------------------------------------------------------------
def parse_specialists(pdf_path):
    raw = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        capture_output=True, text=True, check=True,
    ).stdout
    lines = raw.split("\n")
    records = []
    for line in lines:
        l = line.rstrip("\n")
        if not l.strip():
            continue
        parts = re.split(r"\s{2,}", l.strip())
        if len(parts) == 6 and parts[0].isdigit():
            _, hosp, name, spec, ptype, gender = parts
            records.append({
                "hospital": hosp.strip(), "name": name.strip(),
                "speciality": spec.strip(), "type": ptype.strip(),
                "gender": gender.strip(),
            })
    return records


# ---------------------------------------------------------------------------
# Step 2c: parse the clinic PDF (pdfplumber table extraction)
# ---------------------------------------------------------------------------
def norm_clinic_state(s):
    mapping = {
        "PULAU PINANG": "Penang",
        "KUALA LUMPUR": "Wilayah Persekutuan (KL)",
        "LABUAN": "Wilayah Persekutuan (Labuan)",
    }
    return mapping.get(s, s.title())


FACILITY_LEGEND = {
    "CXR2": "Chest X-Ray with report", "ECG3": "Electrocardiogram with report",
    "ECO2": "Echo Cardiogram", "KUB2": "KUB X-ray",
    "LME": "Long Medical Examination", "LUF2": "Lung Function Test",
    "MM2": "Mammography (Breast)", "PAP2": "Pap Smear Test",
    "TMX2": "Treadmill/Stress ECG with result report", "ULT2": "Ultrasound of Breast",
}


def parse_clinics(pdf_path):
    records = []
    current_state = None
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for row in table:
                    if not row or row[0] == "Location":
                        continue
                    nonempty = [c for c in row if c]
                    if len(nonempty) <= 1:
                        if row[0]:
                            current_state = row[0].strip()
                        continue
                    if len(row) < 8:
                        continue
                    loc, code, name, addr, contact, hours, doctor, facility = row[:8]
                    if not code:
                        continue
                    records.append({
                        "state": current_state,
                        "location": " ".join((loc or "").split()),
                        "code": code.strip(),
                        "name": " ".join((name or "").split()),
                        "address": " ".join((addr or "").split()),
                        "contact": (contact or "").replace("\n", " / ").strip(),
                        "hours": (hours or "").replace("\n", "; ").strip(),
                        "doctors": [d.strip() for d in (doctor or "").split("\n") if d.strip()],
                        "facility_raw": (facility or ""),
                    })

    for r in records:
        r["state"] = norm_clinic_state(r["state"])
        r["has_tmx2"] = "TMX2" in r["facility_raw"]
        r["has_edocs"] = "e-Docs" in r["facility_raw"]
        fac_clean = r["facility_raw"].replace("(e-Docs)", "").strip().rstrip(",").strip()
        r["facility_codes"] = [x.strip() for x in fac_clean.split(",") if x.strip()]
        del r["facility_raw"]
        lat, lng = find_coord(r["location"])
        r["lat"], r["lng"] = lat, lng

    return records


# ---------------------------------------------------------------------------
# Step 3: link specialists to their canonical hospital name
# ---------------------------------------------------------------------------
def norm_name(n):
    n = re.sub(r"\([^)]*\)", "", n).upper()
    n = re.sub(r"[^A-Z0-9 ]", " ", n)
    return " ".join(n.split())


def link_specialists_to_hospitals(specialists, hospitals):
    hosp_by_norm = {}
    for h in hospitals:
        hosp_by_norm.setdefault(norm_name(h["name"]), []).append(h)

    spec_hosp_names = sorted(set(s["hospital"] for s in specialists))
    mapping = {}
    for name in spec_hosp_names:
        key = norm_name(name)
        if key in hosp_by_norm:
            mapping[name] = hosp_by_norm[key][0]["name"]
        else:
            close = difflib.get_close_matches(key, hosp_by_norm.keys(), n=1, cutoff=0.6)
            mapping[name] = hosp_by_norm[close[0]][0]["name"] if close else None

    hosp_by_name = {h["name"]: h for h in hospitals}
    for s in specialists:
        canon = mapping.get(s["hospital"])
        hr = hosp_by_name.get(canon) if canon else None
        s["hospital_canonical"] = canon
        s["state"] = hr["state"] if hr else None
        del s["hospital"]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("Finding current PDF links on the locator page...")
    links = find_pdf_links()
    for k, v in links.items():
        print(f"  {k}: {v}")

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    print("Downloading PDFs...")
    hosp_pdf = download(links["hospital"], TMP_DIR / "hospital.pdf")
    spec_pdf = download(links["specialist"], TMP_DIR / "specialist.pdf")
    clinic_pdf = download(links["clinic"], TMP_DIR / "clinic.pdf")

    print("Parsing hospitals...")
    hospitals = parse_hospitals(hosp_pdf)
    print(f"  {len(hospitals)} hospitals")

    print("Parsing specialists...")
    specialists = parse_specialists(spec_pdf)
    print(f"  {len(specialists)} specialists")
    link_specialists_to_hospitals(specialists, hospitals)

    print("Parsing clinics...")
    clinics = parse_clinics(clinic_pdf)
    print(f"  {len(clinics)} clinics")

    specialties = sorted(set(
        sp.strip() for s in specialists for sp in s["speciality"].split(";")
    ))
    states = sorted(set(h["state"] for h in hospitals if h["state"]))
    clinic_states = sorted(set(c["state"] for c in clinics if c["state"]))

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # --- Sanity check: refuse to overwrite good data with a bad/partial scrape ---
    # If the PDF format ever changes in a way that breaks parsing without
    # raising an outright error (e.g. a column shuffled), this catches it by
    # comparing against what's already live, instead of silently wiping the site.
    def sanity_check(name, new_count):
        existing_path = DATA_DIR / name
        if not existing_path.exists():
            return  # first run ever, nothing to compare against
        try:
            old_count = len(json.loads(existing_path.read_text(encoding="utf-8")))
        except Exception:
            return  # can't read old file, don't block on that
        if old_count > 0 and new_count < old_count * 0.5:
            raise RuntimeError(
                f"{name}: new data has only {new_count} records, "
                f"down from {old_count} previously. This looks like a parsing "
                f"failure (the PDF format may have changed), not a real drop. "
                f"Refusing to overwrite — the site will keep showing last month's data."
            )

    sanity_check("hospitals.json", len(hospitals))
    sanity_check("specialists.json", len(specialists))
    sanity_check("clinics.json", len(clinics))

    def write_json(name, obj):
        path = DATA_DIR / name
        path.write_text(json.dumps(obj, separators=(",", ":")), encoding="utf-8")
        print(f"  wrote {path} ({path.stat().st_size} bytes)")

    write_json("hospitals.json", hospitals)
    write_json("specialists.json", specialists)
    write_json("meta.json", {"specialties": specialties, "states": states})
    write_json("clinics.json", clinics)
    write_json("clinics-meta.json", {"states": clinic_states, "facility_legend": FACILITY_LEGEND})

    print("Done.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
