# Post-use evaluation form — HTML + CSV (no database)

Just three files:

- `form.html` — the form itself, wording matched verbatim to
  `ตัวอย่างแบบฟอร์มสำหรับประเมินผลหลังการใช้งาน_v2.docx` (ฉบับที่ 2.0, 19 ก.พ. 2569).
  You can open this file directly in a browser to see/edit the layout — it
  only needs the server once you actually submit it.
- `app.py` — a ~130-line Flask app: serves `form.html`, and on submit
  appends one row to `evaluations.csv` in the same folder.
- `thanks.html` — the page shown after a successful submission.

## Run it

```bash
pip install flask
python3 app.py
# open http://localhost:8000
```

Each submission adds a row to `evaluations.csv` (created automatically on
first submit, UTF-8 with BOM so Thai text opens correctly straight in Excel).

## Deploy on your server

Same shape as before — gunicorn behind Caddy for HTTPS:

```bash
pip install flask gunicorn
gunicorn -b 0.0.0.0:8000 -w 2 app:app
```

Point Caddy/nginx at `127.0.0.1:8000` the same way you did for the earlier
Mongo-based app. Set real admin credentials before exposing this publicly:

```bash
export ADMIN_USER=youradminname
export ADMIN_PASS='a-strong-password'
```

## Getting the data

- `https://<your-domain>/export` (HTTP Basic Auth, `ADMIN_USER`/`ADMIN_PASS`)
  downloads the current `evaluations.csv`.
- Or just open/copy the file directly if you're on the server:
  `evaluations.csv` sits next to `app.py`.

## Limits of this approach, by design (you asked for "simplest possible")

- No participant-code linking back to an enrollment record — this only
  collects anonymous evaluation responses. If you need to join evaluations
  back to a specific enrolled participant later, say so and I'll add a
  `participant_code` field (same pattern as the Mongo-based app from
  before).
- A single CSV file with no locking beyond a simple in-process lock is
  fine at the scale you described (500 people, one evaluation each) but
  isn't meant to handle many simultaneous writers or get much bigger than
  that without moving to a real database.
- Back the file up periodically once real responses start coming in —
  it's your only copy. `cp evaluations.csv evaluations-backup-$(date +%F).csv`
  on a cron schedule is a reasonable minimum.
