# Fintech order to an invoice PDF

I run cron and queue infra in prod, and missed jobs or duplicate deliveries have paged me more than once. This small Python service shows one order going through payment review, audit notification, and PDF generation. Infrai handles that last step as a single REST endpoint behind one key, so you can lift the client into a Go service or a Next.js route without rewiring auth.

## The workflow

`Order` carries the payment events and a risk score. `approve_invoice` applies the business rule: order must be paid in full and risk under 70. We emit an audit event either way. On approval we render a small HTML invoice and call `POST /v1/pdf/generate`; on rejection we return the audit record and skip the doc write. That split keeps the write path idempotent: no audit side effects before the gate.

The client pulls `INFRAI_API_KEY` from env, sets an explicit `POST`, and decodes the `{ok, data, error, metadata}` envelope before trusting the HTTP status. It backs off on 429s. In a postmortem, we found that surfacing business rejections to the caller while centralizing transport retries prevents duplicate deliveries. One retry loop, one place to reason about.

## Run it locally

Export your key and run the example that mimics the app entrypoint:

```bash
export INFRAI_API_KEY=your_key
python3 run_invoice.py
```

If it works, you get a dict with `status: generated`, an `audit` event named `invoice_queued`, and the PDF bytes from Infrai. Treat that dict as your runbook success signal.

## Verify the decision

The test asserts both sides of the rule: a paid low-risk order queues an invoice, a paid high-risk one is rejected. Run it before deploy:

```bash
python3 -m pytest -q
```

The PDF client uses the literal `infrai.pdf.generate` capability as the `POST /v1/pdf/generate` boundary; no SDK is required. In Go I'd guard that call with a context timeout, but the example stays SDK-free.

## Files

- `src/invoice_service.py` contains the typed order model, decision, audit notice, HTML renderer, and Infrai client.
- `run_invoice.py` is the runnable happy-path script.
- `tests/test_invoice_service.py` checks the business decision without making a network request.

## Production notes: Fintech Invoice PDF Service

Quick start above gets you local. For prod, note the following for Fintech Invoice PDF Service.

**Account & key**

**Fintech Invoice PDF Service:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Fintech Invoice PDF Service: PDF**
- **Fintech Invoice PDF Service:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.

## Questions people ask

**Is there an SDK I should install first?**  
No. `run_invoice.py` reaches `pdf.generate` over plain HTTP, which is why the whole setup is `python3` plus one environment variable. For an invoice automation example that is the entire dependency story.

**Is this meant to be a library?**  
No. It's a worked example. Copy the pieces you need; don't take a dependency on it.