# YieldNest - Professional Slot-Based Plan Platform

YieldNest is a Flask web app for publishing manager-controlled plans where users can select slots, view expected maturity value, scan a unique QR payment session, submit UPI/PhonePe payment details, and track verification status.

## Default admin login
Set these in `.env` or Railway variables:

- `ADMIN_EMAIL=admin@yieldnest.local`
- `ADMIN_PASSWORD=ChangeMe123!`

Admin panel URL:

- Local: `http://127.0.0.1:5000/admin`
- Railway: `https://your-domain.up.railway.app/admin`

Change the admin email/password before production.

## Important compliance note
This app is software only. Offering pooled funds, fixed returns, interest, maturity payouts, or early withdrawal charges may require SEBI/RBI/legal registration depending on your business model and jurisdiction. Get professional legal review before accepting public money.

## Features
- Professional animated landing page
- User signup/login
- Plan listing with slot value, minimum slots, expected return, maturity date, early-exit charge
- User purchase calculator
- Unique UPI QR generated per purchase request
- QR is valid for 60 seconds
- New QR generation unlocks after 2 minutes
- Payment notification form with payer name, payer UPI ID, PhonePe number, UTR/reference ID, screenshot URL
- Admin dashboard
- Admin create/edit/activate/deactivate plans
- Admin review payments and approve/reject requests
- Terms & conditions page
- Railway-ready Procfile + database support

## Local setup
```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate # Mac/Linux
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Open `http://127.0.0.1:5000`

## Railway deployment
1. Push this folder to GitHub.
2. Create a Railway project from the GitHub repo.
3. Add PostgreSQL in Railway.
4. Set environment variables:
   - `SECRET_KEY`
   - `DATABASE_URL`
   - `ADMIN_EMAIL`
   - `ADMIN_PASSWORD`
   - `BRAND_NAME`
   - `SUPPORT_EMAIL`
5. Railway will use the included Procfile with Gunicorn.

## Payment flow
This starter supports manual UPI/PhonePe verification. Users scan the generated QR and submit transaction details. Admin approves only after verifying the transaction. For fully automatic payment status and callbacks, integrate the official PhonePe Payment Gateway APIs.
