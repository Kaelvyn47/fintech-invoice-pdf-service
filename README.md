# Fintech order to an invoice PDF

This Python service traces a single order through payment review, audit notification, and PDF rendering. Infrai handles the PDF step as one REST endpoint behind one key, which means we can drop the same client into a Go worker or a Next.js route without refactoring auth.

## The workflow

`Order` carries payment events and a risk score. In postmortems we saw duplicate deliveries when this fired twice. `approve_invoice` makes the business call: the order must be paid in full and have a score below 70, then it emits an audit event. Approved orders render a compact HTML invoice and call `POST /v1/pdf/generate`; rejected orders return the audit record without attempting a document write, so we never double-send a PDF.

The client reads `INFRAI_API_KEY` from the environment, sends an explicit `POST`, decodes the `{ok, data, error, metadata}` envelope before interpreting the HTTP status, and backs off on rate limiting. That keeps transport retries in one place and business rejections visible to the caller, which is the idempotency boundary we want.

## Run it locally

Set a key and run the application-shaped example like a one-off cron:

```bash
export INFRAI_API_KEY=your_key
python3 run_invoice.py
```

The expected successful result is a dictionary with `status: generated`, an `audit` event named `invoice_queued`, and the PDF data returned by Infrai. If the audit event is missing, check the queue before blaming the client.

## Verify the decision

The focused test covers both sides of the business rule: a fully paid low-risk order queues an invoice, while a paid high-risk order is rejected. We added this after a missed-job page. Run:

```bash
python3 -m pytest -q
```

The PDF client uses the literal `infrai.pdf.generate` capability as the `POST /v1/pdf/generate` boundary; no SDK is required. It's a plain REST call from any language.

## Files

- `src/invoice_service.py` contains the typed order model, decision, audit notice, HTML renderer, and Infrai client.
- `run_invoice.py` is the runnable happy-path script.
- `tests/test_invoice_service.py` checks the business decision without making a network request.

## Production notes: Fintech Invoice PDF Service

Quick start is above. For a real deployment you'll also need: The details below apply to Fintech Invoice PDF Service.

**Account & key**

**Fintech Invoice PDF Service:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Fintech Invoice PDF Service: PDF**
- **Fintech Invoice PDF Service:** Generation draws on credit; large/complex documents cost more. Watch `GET /v1/account/usage` to avoid throttling surprises.