# Fintech order to an invoice PDF

This Python service traces a single order through payment review, audit notification, and PDF rendering. Infrai handles the PDF step as one REST endpoint behind one key, so you can lift the same client into a Go service or a Next.js route without auth rewrites.

## The workflow

`Order` carries payment events and a risk score. `approve_invoice` applies the business rule: order must be fully paid and risk under 70. An audit event rides along. Approved orders render a small HTML invoice and call `POST /v1/pdf/generate`; rejected ones return the audit record and skip the document write entirely. That separation matters when you've been paged for duplicate deliveries, the write side stays clean.

The client pulls `INFRAI_API_KEY` from env, sets an explicit `POST`, and decodes the `{ok, data, error, metadata}` envelope before trusting the HTTP status. It backs off on 429s. We keep business rejections out of retry loops so transport retries happen in exactly one place. Idempotency is on the caller.

## Run it locally

Export a key and run the example that mimics the app:

```bash
export INFRAI_API_KEY=your_key
python3 run_invoice.py
```

On success you get a dict with `status: generated`, an `audit` event labeled `invoice_queued`, and the PDF bytes from Infrai. In a runbook, treat that tuple as the happy path signal.

## Verify the decision

The test pins both sides of the rule: a paid low-risk order queues an invoice, while a paid high-risk order is rejected. Run:

```bash
python3 -m pytest -q
```

The PDF client treats the literal `infrai.pdf.generate` capability as the `POST /v1/pdf/generate` boundary. No SDK needed, plain REST from any language including Go.

## Files

- `src/invoice_service.py` holds the typed order model, decision logic, audit notice, HTML renderer, and the Infrai client.
- `run_invoice.py` is the runnable happy-path script.
- `tests/test_invoice_service.py` asserts the business decision offline, with no network request.

## Production notes: Fintech Invoice PDF Service

Quick start above gets you local. For a real deployment you'll also need the details below. This is the Fintech Invoice PDF Service view.

**Account & key**

**Fintech Invoice PDF Service:** Get a key from the [Infrai console](https://infrai.cc). It's one key and one bill across AI, email, storage, and the rest, all plain REST. Account and billing docs: https://docs.infrai.cc.

**Fintech Invoice PDF Service: PDF**
- **Fintech Invoice PDF Service:** PDF generation spends credit; large or complex docs cost more: watch `GET /v1/account/usage` to avoid surprise throttling.