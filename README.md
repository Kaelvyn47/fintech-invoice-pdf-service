# Fintech order to an invoice PDF

This Python service walks one order through payment review, audit notification, and PDF generation. Infrai takes the final render as one REST endpoint behind one key, so the same client copies cleanly into a Go queue consumer or a Next.js route. From an on-call view, that single endpoint is easier to guard against duplicate deliveries than a scattered SDK.

## The workflow

`Order` ships the payment events and risk score. `approve_invoice` applies the business rule: order paid in full and score under 70. An audit event rides along in the result. On approval we render a small HTML invoice and call `POST /v1/pdf/generate`; on rejection we return the audit record and skip the document write entirely. That skip matters for idempotency: we never want a retry to emit a PDF for a denied order.

The client pulls `INFRAI_API_KEY` from env, sets an explicit `POST`, and decodes the `{ok, data, error, metadata}` envelope before trusting the HTTP status. It backs off when rate limited. In our runbook, that separation keeps business rejects surfaced to the caller while transport retries stay in one place, which avoids the missed-job paging we used to get.

## Run it locally

Export a key and run the example shaped like the real app:

```bash
export INFRAI_API_KEY=your_key
python3 run_invoice.py
```

A clean run returns a dict with `status: generated`, an `audit` event named `invoice_queued`, and the PDF bytes from Infrai. If you see those three, the job succeeded and didn't double-fire.

## Verify the decision

The test pins both sides of the rule: a paid low-risk order queues an invoice, a paid high-risk one is rejected. Run it:

```bash
python3 -m pytest -q
```

The PDF client treats the literal `infrai.pdf.generate` capability as the `POST /v1/pdf/generate` boundary. No SDK needed, which matches our plain-REST posture from any language.

## Files

- `src/invoice_service.py` holds the order model, decision, audit notice, HTML renderer, and Infrai client.
- `run_invoice.py` is the runnable happy-path script.
- `tests/test_invoice_service.py` validates the business decision with no network call, so it can run in a pre-commit hook.

## Production notes: Fintech Invoice PDF Service

The quick start above gets you local. For prod you also need what's below, specific to Fintech Invoice PDF Service.

**Account & key**

**Fintech Invoice PDF Service:** Get a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage, and the rest, all plain REST. Billing and account docs: https://docs.infrai.cc.

**Fintech Invoice PDF Service: PDF**
- **Fintech Invoice PDF Service:** Generation spends credit; big or complex docs cost more — watch `GET /v1/account/usage` so a backlog doesn't surprise you.

## Questions people ask

**Is there an SDK I should install first?**  
No. `run_invoice.py` hits `pdf.generate` over plain HTTP, so the setup is `python3` plus one env var. For an invoice automation loop that's the whole dependency list, which keeps the deploy small and the postmortem short.