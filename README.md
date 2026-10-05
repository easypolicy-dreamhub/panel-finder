# Panel Finder

A simple, mobile-friendly directory of panel hospitals, specialists, and new-business checkup clinics, built for your team and clients to search and find one nearby.

## What's inside
- `index.html` — the whole app (no build step needed)
- `data/hospitals.json` — 129 panel hospitals, extracted from your hospital listing PDF
- `data/specialists.json` — ~10,247 panel specialists, extracted from your specialist listing PDF
- `data/meta.json` — dropdown filter options for hospitals/specialists (states, specialties)
- `data/clinics.json` — 511 panel clinics for new business/underwriting medical checkups, extracted from your clinic listing PDF
- `data/clinics-meta.json` — dropdown filter options for clinics (states) and the medical-facility code legend (e.g. LME, ECG3, PAP2)

## How it works
- **Hospitals tab**: search by name/town, filter by state, tap "Sort by distance from me" to use the phone's GPS. Each hospital card shows address, phone (tap to call), a "Directions" link (opens Google Maps), deposit policy, and an expandable list of panel specialists based there.
- **Specialists tab**: search by doctor name, specialty, or hospital; filter by specialty and state. Each card links back to the hospital it's based at.
- **Checkup Clinics tab**: for new policy applications and upgrades only — where a client goes when underwriting requires a medical exam, not for treatment or claims. The tab carries a banner making this clear. Each card shows the clinic's operating hours, attached doctor(s), which tests it offers (e.g. LME, chest X-ray, ECG, Pap smear — hover/tap a tag for the full name), whether it has Treadmill/Stress ECG (TMX2, flagged in the source PDF), and whether it supports e-Docs (electronic report transfer, meaning the client does not carry a sealed envelope).
- Distance sorting uses the **town/city centre** of each hospital's address, not the exact building — good enough for "which of these is closest to me," not turn-by-turn precision. See "Improving accuracy" below if you want exact pins.

## Deploying to Netlify (2 minutes)
1. Go to [app.netlify.com](https://app.netlify.com) and log in (or sign up free).
2. Drag the whole `panel-finder` folder onto the "Deploys" area of a new site (or use "Add new site → Deploy manually").
3. Netlify gives you a live URL immediately (e.g. `yourname.netlify.app`). Share that link with your team and clients.
4. Optional: in Site settings → Domain management, add a custom domain or change the Netlify subdomain to something branded.

For auto-updating deploys instead of drag-and-drop, connect this folder to a GitHub repo and link that repo in Netlify — every push then redeploys automatically.

## Updating the panel list later
When Great Eastern issues a new PDF (the clinic list is updated monthly):
1. Send me (or re-run the same extraction process on) the new PDF.
2. Replace the matching JSON file(s) — `data/hospitals.json`, `data/specialists.json`, or `data/clinics.json`.
3. Re-deploy (drag the folder in again, or push to GitHub if connected).

No code changes needed for routine list updates — just the two JSON files.

## Improving location accuracy (optional next step)
Right now hospitals are geocoded to their town centre using a built-in lookup table. If you want the "Directions" and distance sorting to use the exact hospital building:
- Get a Google Maps Geocoding API key (free tier covers this easily), and geocode each hospital's full address once — I can generate the exact `lat`/`lng` values to drop into `hospitals.json` if you get the key.
- The "Directions" button already uses the full street address (not the approximate coordinates), so it routes accurately in Google Maps regardless — only the *sort-by-nearest* ordering is town-level.

## Known data notes
- A few hospitals have been renamed (e.g. "Beacon Hospital", formerly "Beacon International Specialist Centre"). Both the old and new names are matched automatically so specialists still show up under the current hospital name.
- One specialist record in the source PDF (Dr. Sivaprakasam a/l Sivalingam at Cengild G.I Medical Centre) was missing its "Resident/Visiting" and gender fields in the original file; it's been filled in to match his listing at other hospitals — worth double-checking against the source if it matters for your use.
