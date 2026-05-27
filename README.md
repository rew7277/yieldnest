# YieldNest - Slot Based Maturity Plan Platform

YieldNest is a Flask + PostgreSQL web app for publishing admin-managed plans/funds where users can select slots, view expected maturity value, submit UPI/PhonePe payment details, and track approval status.

## Important compliance note
This app is software only. Offering pooled funds, fixed returns, interest, maturity payouts, or early withdrawal charges may require SEBI/RBI/legal registration depending on your business model and jurisdiction. Use compliant terms and get professional legal review before accepting public money.

## Features
- Professional landing page
- User signup/login
- Fund/plan listing with slot value, minimum slots, expected return, maturity date, early exit charge
- User purchase calculator
- PhonePe/UPI payment instruction screen
- Payment notification form with payer name, payer UPI ID, PhonePe number, UTR/reference ID, screenshot URL
- Admin dashboard
- Admin create/edit/activate/deactivate plans
- Admin review payments and approve/reject investments
- Terms & conditions page
- Railway-ready Procfile + PostgreSQL support

## Local setup
```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate # Mac/Linux
pip install -r requirements.txt
cp .env.example .env
python app.py
```
Open http://127.0.0.1:5000

Default admin comes from `.env`:
- ADMIN_EMAIL
- ADMIN_PASSWORD

## Railway deployment
1. Push this folder to GitHub.
2. Create a Railway project from GitHub repo.
3. Add PostgreSQL in Railway.
4. Set environment variables:
   - SECRET_KEY
   - DATABASE_URL (Railway usually provides this)
   - ADMIN_EMAIL
   - ADMIN_PASSWORD
   - BRAND_NAME
   - SUPPORT_EMAIL
5. Railway will use the Procfile with Gunicorn.

## PhonePe payment handling
This starter app supports manual UPI/PhonePe payment confirmation. Users pay to the admin's configured PhonePe number/UPI ID and submit transaction details. Admin approves only after verifying the payment. For automatic payment status and callbacks, integrate PhonePe Payment Gateway using official PhonePe merchant docs.
