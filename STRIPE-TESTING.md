# 💳 Testing Payments with Stripe (Test Mode)

A complete guide to testing the AgentX subscription flow locally and on Railway — **no real money involved**.

---

## How the Flow Works (read this first)

1. A logged-in user clicks **Choose Starter / Professional / Enterprise** on the pricing page.
2. The frontend calls `POST /api/create-checkout-session` with their JWT.
3. The backend creates a **Stripe Checkout Session** (subscription mode: $99 / $299 / $999 per month) with `metadata: {user_id, plan}` and returns a Stripe-hosted URL.
4. The user pays on Stripe's page (use a test card) and is redirected back to `/dashboard`.
5. Stripe fires a **`checkout.session.completed` webhook** at `POST /api/stripe-webhook`. The backend verifies the signature, then upgrades the user: `plan` set, `tasks_limit` raised (50 / 200 / unlimited), `tasks_used` reset to 0.

> ⚠️ **Key point:** the plan only upgrades when the **webhook arrives**. Completing payment alone does nothing — the webhook is what applies the upgrade. That's why Step 4 below matters.

---

## Step 1 — Get your test keys (2 minutes, free)

1. Create an account at <https://dashboard.stripe.com> (no card required).
2. In the Dashboard, make sure **Test mode** is ON (toggle, top right).
3. Go to **Developers → API keys** and copy the **Secret key** — it starts with `sk_test_`.

## Step 2 — Configure the app locally

```bash
cp .env.example .env
```

Edit `.env` and set:

```
STRIPE_SECRET_KEY=sk_test_your-real-test-key-here
```

> The app loads `.env` at startup (via `python-dotenv`). Real environment variables always take precedence, so this doesn't affect Railway or Docker deployments.

Start the server:

```bash
uvicorn app:app --reload --port 8000
```

The startup banner should now print `Stripe: ✅ Configured`. If it says `❌ Not set`, check `.env` and restart.

## Step 3 — Run a test purchase

1. Open <http://localhost:8000>, create an account (or log in).
2. Go to **Pricing** and click **Choose Professional**.
3. Stripe's checkout page opens. Pay with the classic test card:

| Field | Value |
|---|---|
| Card number | `4242 4242 4242 4242` |
| Expiry | any future date, e.g. `12/34` |
| CVC | any 3 digits |
| Email / name / zip | anything |

4. You'll be redirected back to `/dashboard?session_id=...`.

Other useful test cards:

| Card number | Behavior |
|---|---|
| `4242 4242 4242 4242` | ✅ Succeeds |
| `4000 0000 0000 9995` | ❌ Declined |
| `4000 0025 0000 3155` | 🔐 Requires 3D Secure authentication |

## Step 4 — Receive webhooks (this is what upgrades the plan)

### Locally — Stripe CLI

1. Install the Stripe CLI: <https://docs.stripe.com/stripe-cli> (macOS: `brew install stripe/stripe-cli/stripe-cli`)
2. Authenticate and start forwarding to your local server:

   ```bash
   stripe login
   stripe listen --forward-to localhost:8000/api/stripe-webhook
   ```

3. It prints a webhook signing secret, e.g. `whsec_a1b2c3...` — put it in `.env`:

   ```
   STRIPE_WEBHOOK_SECRET=whsec_a1b2c3...
   ```

   …and restart uvicorn (the secret is read at startup).
4. With `stripe listen` **still running**, repeat the test purchase from Step 3. You'll see the event arrive in the CLI, and your dashboard will refresh to **⚡ Professional** with a 200-task limit.

> 💡 `stripe trigger checkout.session.completed` is handy to test connectivity, but the synthetic event has **no `user_id` metadata**, so it won't upgrade any account. A real upgrade test requires completing a real (test-mode) checkout while `listen` is running.

### On Railway (or any public deployment)

1. Stripe Dashboard (still in **Test mode**) → **Developers → Webhooks → Add endpoint**.
2. Endpoint URL: `https://your-app.up.railway.app/api/stripe-webhook`
3. Select event: **`checkout.session.completed`**.
4. Copy the endpoint's signing secret (`whsec_...`) and set `STRIPE_WEBHOOK_SECRET` in your Railway service variables.
5. In Railway, also set `STRIPE_SECRET_KEY` to your `sk_test_...` key (Railway injects these as real env vars, which override `.env`).
6. Redeploy, then run the same purchase test against your public URL.

When you go live: switch both keys to live mode (`sk_live_...`), create a **new** live webhook endpoint, and make sure a strong `SECRET_KEY` is set.

## Step 5 — Verify the upgrade worked

- Call `GET /api/auth/me` (with your Bearer token) — you should see:

  ```json
  { "plan": "professional", "tasks_limit": 200, "tasks_used": 0 }
  ```

- Or just open `/dashboard`: the badge shows **⚡ Professional Plan** and the usage bar reads `0 / 200 tasks`.

## 🔧 Troubleshooting

| Symptom | Fix |
|---|---|
| "Stripe not configured. Set STRIPE_SECRET_KEY." | `.env` missing/typo'd, or the server was started before you edited it — restart. |
| Checkout fails with an API-key error | You mixed live and test keys, or copied the *publishable* key instead of the *secret* key. |
| Webhook returns 400 "Invalid signature" | `STRIPE_WEBHOOK_SECRET` doesn't match — re-copy the `whsec_` from `stripe listen` and restart. |
| Paid, but plan didn't change | The webhook never arrived. Check `stripe listen` is running and forwarding to the right port; check **Developers → Events** in the Stripe Dashboard to see if it was sent. |
| Webhook reached but nothing upgraded | The event had no `user_id` metadata (synthetic trigger). Do a real checkout while `listen` runs. |
| Redirect after payment goes to localhost | The frontend sends `window.location.origin` automatically, so this only happens if you manually overrode `success_url` — you didn't need to. |

## 📝 Notes

- **Prices** are defined in `price_map` inside `create_checkout_session` (`app.py`): starter $99/mo, professional $299/mo, enterprise $999/mo.
- The **Enterprise** card says "Custom" on the landing page, but the backend charges $999/mo — update `price_map` if you want true custom pricing.
- Plan limits come from `PLAN_LIMITS` in `app.py`: free 5, starter 50, professional 200, enterprise effectively unlimited.
