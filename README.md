# YieldNest Premium V4

Professional slot-based plan platform with admin-managed plans, user dashboards, secure timed QR payment sessions, and payment webhook readiness.

## Admin login

Default local login:

- URL: `/admin`
- Email: `admin@yieldnest.local`
- Password: `ChangeMe123!`

Set these in Railway before production:

```env
ADMIN_EMAIL=youradmin@email.com
ADMIN_PASSWORD=yourStrongPassword
```

## Railway environment variables

```env
SECRET_KEY=change-me
DATABASE_URL=<Railway PostgreSQL URL>
BRAND_NAME=YieldNest
SUPPORT_EMAIL=support@yourdomain.com
ADMIN_EMAIL=youradmin@email.com
ADMIN_PASSWORD=yourStrongPassword
PLATFORM_UPI_ID=yourupi@ybl
PLATFORM_PAYEE_NAME=YieldNest
PLATFORM_PHONEPE_NUMBER=hidden
PAYMENT_WEBHOOK_SECRET=use-a-long-random-secret
```

`PLATFORM_UPI_ID` is the real UPI ID where you receive money. It is not shown as text to users. The QR is generated with `PLATFORM_PAYEE_NAME=YieldNest`, so the user sees the branded payee name in their UPI app.

## Payment flow logic

1. User selects a plan and slot count.
2. App creates a slot request with `payment_pending` status.
3. App generates a unique QR token for that request.
4. QR is valid for 60 seconds.
5. A fresh QR can be generated after the 2-minute refresh window.
6. User scans and pays.
7. User clicks **I have completed payment**.
8. Page starts polling payment status.
9. When payment is confirmed, the app redirects to the dashboard and the allocated slots are visible.

## Important automatic payment note

A plain UPI QR cannot reliably tell the website that money was received. For real automatic closing/redirect after payment, connect a real payment provider status API or webhook.

This starter includes a webhook endpoint:

```http
POST /api/payment/webhook
Content-Type: application/json

{
  "secret": "PAYMENT_WEBHOOK_SECRET",
  "investment_id": 1,
  "transaction_ref": "TXN123",
  "status": "SUCCESS"
}
```

When the webhook receives `SUCCESS`, the request is marked approved and the user dashboard shows the allocated slots.

## Local run

```bash
pip install -r requirements.txt
python app.py
```

## Railway deployment

1. Push this folder to GitHub.
2. Create a Railway project from the GitHub repo.
3. Add PostgreSQL.
4. Add environment variables above.
5. Deploy.

The included `Procfile` runs Gunicorn.
