"""
NeuroRelief – Sample Dataset + Dummy Data Generator
Run:  python seed.py
      python seed.py --base-url http://backend:8000   (Docker)
Seeds the database with volunteers and reports, then triggers signal fusion.
"""
import argparse
import asyncio
import random
from datetime import datetime, timezone, timedelta
import httpx

BASE_URL = "http://localhost:8000"

# ─────────────────────────────────────────────
# SAMPLE VOLUNTEERS (Chennai + surrounding, India)
# ─────────────────────────────────────────────
VOLUNTEERS = [
    {"name": "Priya Sharma",    "email": "priya@nr.io",    "skills": ["medical","first_aid","nursing"],       "languages": ["english","tamil","hindi"],  "location_lat": 13.0827, "location_lon": 80.2707, "trust_score": 0.92},
    {"name": "Ravi Kumar",      "email": "ravi@nr.io",     "skills": ["driving","logistics","rescue"],        "languages": ["tamil","telugu"],           "location_lat": 13.0569, "location_lon": 80.2425, "trust_score": 0.85},
    {"name": "Anjali Nair",     "email": "anjali@nr.io",   "skills": ["counseling","social_work","first_aid"],"languages": ["english","malayalam"],      "location_lat": 13.1067, "location_lon": 80.2785, "trust_score": 0.78},
    {"name": "Mohammed Farooq", "email": "farooq@nr.io",   "skills": ["construction","logistics","driving"],  "languages": ["english","urdu","tamil"],   "location_lat": 13.0459, "location_lon": 80.2101, "trust_score": 0.88},
    {"name": "Sunita Reddy",    "email": "sunita@nr.io",   "skills": ["cooking","food","logistics"],          "languages": ["telugu","english"],         "location_lat": 13.1200, "location_lon": 80.2500, "trust_score": 0.73},
    {"name": "Dev Anand",       "email": "dev@nr.io",      "skills": ["rescue","swimming","climbing","driving"],"languages": ["english","hindi"],         "location_lat": 13.0900, "location_lon": 80.2800, "trust_score": 0.95},
    {"name": "Lakshmi Iyer",    "email": "lakshmi@nr.io",  "skills": ["medical","doctor","nursing"],          "languages": ["tamil","english","sanskrit"],"location_lat": 13.0750, "location_lon": 80.2650, "trust_score": 0.90},
    {"name": "Karthik Babu",    "email": "karthik@nr.io",  "skills": ["driving","transport","logistics"],     "languages": ["tamil","kannada"],          "location_lat": 13.0300, "location_lon": 80.2300, "trust_score": 0.68},
    {"name": "Fatima Begum",    "email": "fatima@nr.io",   "skills": ["counseling","psychology"],             "languages": ["urdu","english","tamil"],   "location_lat": 13.0650, "location_lon": 80.2550, "trust_score": 0.82},
    {"name": "Samuel John",     "email": "samuel@nr.io",   "skills": ["construction","shelter","logistics"],  "languages": ["english","tamil"],          "location_lat": 13.0400, "location_lon": 80.2600, "trust_score": 0.76},
]

# ─────────────────────────────────────────────
# SAMPLE REPORTS (simulate community submissions)
# ─────────────────────────────────────────────
REPORTS = [
    # Medical cluster – Adyar area (will fuse into 1 signal)
    {"location_lat": 13.0012, "location_lon": 80.2565, "issue_type": "medical", "description": "Critical – elderly man collapsed, needs urgent medical attention", "reporter_name": "Anbu Selvan"},
    {"location_lat": 13.0018, "location_lon": 80.2570, "issue_type": "medical", "description": "Emergency! Woman having severe chest pain on Anna Salai", "reporter_name": "Meena R"},
    {"location_lat": 13.0009, "location_lon": 80.2560, "issue_type": "medical", "description": "Urgent – child with high fever, no hospital nearby", "reporter_name": "Ramesh T"},

    # Food shortage cluster – T.Nagar area
    {"location_lat": 13.0418, "location_lon": 80.2341, "issue_type": "food", "description": "Severe food shortage at refugee camp, 200 families affected", "reporter_name": "Gopalan M"},
    {"location_lat": 13.0422, "location_lon": 80.2345, "issue_type": "food", "description": "Critical – elderly and children without food for 2 days", "reporter_name": "Vani S"},

    # Shelter – Velachery
    {"location_lat": 12.9815, "location_lon": 80.2180, "issue_type": "shelter", "description": "Urgent shelter needed, 50 families displaced after heavy rains", "reporter_name": "Dinesh P"},
    {"location_lat": 12.9820, "location_lon": 80.2185, "issue_type": "shelter", "description": "Serious – families sleeping on roadside, no temporary shelter", "reporter_name": "Arun B"},

    # Rescue – Besant Nagar
    {"location_lat": 13.0002, "location_lon": 80.2707, "issue_type": "rescue", "description": "Critical! Family trapped in flooded house, immediate rescue needed", "reporter_name": "Rajan K"},

    # Counseling – Tambaram
    {"location_lat": 12.9249, "location_lon": 80.1000, "issue_type": "counseling", "description": "Many children traumatised after flood, need urgent counseling support", "reporter_name": "Leela N"},

    # Transport – Anna Nagar
    {"location_lat": 13.0850, "location_lon": 80.2101, "issue_type": "transport", "description": "Need transport urgently for dialysis patients to hospital", "reporter_name": "Suresh V"},

    # Extra medical report close to cluster (will merge)
    {"location_lat": 13.0015, "location_lon": 80.2568, "issue_type": "medical", "description": "Another patient – severe dehydration, needs immediate care", "reporter_name": "Parveen A"},
]


async def seed():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        print("=" * 60)
        print("  NeuroRelief Seed Script")
        print("=" * 60)

        # ── Seed volunteers ──────────────────────────────────────────
        print("\n[1/2] Registering volunteers...")
        for v in VOLUNTEERS:
            resp = await client.post("/volunteers/", json=v)
            if resp.status_code == 201:
                data = resp.json()
                print(f"  [OK]  {data['name']} (trust: {data['trust_score']})")
            else:
                print(f"  [FAIL]  {v['name']} - {resp.status_code}: {resp.text}")

        # ── Seed reports (triggers signal fusion automatically) ──────
        print("\n[2/2] Submitting community reports (fusion runs automatically)...")
        for r in REPORTS:
            resp = await client.post("/reports/", json=r)
            if resp.status_code == 201:
                data = resp.json()
                print(f"  [OK]  [{data['issue_type'].upper()}] severity={data['severity']} signal_id={str(data['signal_id'])[:8]}...")
            else:
                print(f"  [FAIL]  {r['issue_type']} - {resp.status_code}: {resp.text}")

        # ── Show resulting signals ───────────────────────────────────
        print("\n[INFO] Resulting fused signals (priority ranked):")
        resp = await client.get("/signals/")
        for sig in resp.json():
            print(f"  -> [{sig['issue_type'].upper():12}] priority={sig['priority_score']:.3f}  urgency={sig['urgency_score']:.3f}  reports={sig['report_count']}  status={sig['status']}")

        print("\n[DONE] Seed complete! Visit http://localhost:5173 for dashboard.\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed NeuroRelief database")
    parser.add_argument("--base-url", default=BASE_URL, help="Backend API base URL (default: http://localhost:8000)")
    args = parser.parse_args()
    BASE_URL = args.base_url
    asyncio.run(seed())
