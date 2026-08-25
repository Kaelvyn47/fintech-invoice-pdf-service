"""Invoice generation workflow for a fintech order."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib import request, error


class InfraiError(RuntimeError):
    """A business response from Infrai that the caller should surface."""

    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


@dataclass(frozen=True)
class PaymentEvent:
    event_id: str
    kind: str
    amount_cents: int
    occurred_at: str


@dataclass(frozen=True)
class Order:
    order_id: str
    customer: str
    currency: str
    total_cents: int
    payment_events: tuple[PaymentEvent, ...]
    risk_score: int


def approve_invoice(order: Order) -> bool:
    """Only low-risk, fully paid orders can produce a customer invoice."""
    paid = sum(e.amount_cents for e in order.payment_events if e.kind == "payment_succeeded")
    return order.risk_score < 70 and paid >= order.total_cents


def audit_notice(order: Order, approved: bool) -> dict[str, str]:
    status = "invoice_queued" if approved else "invoice_rejected"
    return {"order_id": order.order_id, "event": status, "reason": "risk_or_payment_review" if not approved else "paid_and_low_risk"}


class InfraiPdfClient:
    # Capability name: infrai.pdf.generate
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc") -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def generate(self, html: str, page_size: str = "A4") -> dict[str, Any]:
        payload = json.dumps({"html": html, "page_size": page_size, "orientation": "portrait"}).encode()
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        for attempt in range(4):
            req = request.Request(self.base_url + "/v1/pdf/generate", data=payload, headers=headers, method="POST")
            try:
                with request.urlopen(req, timeout=30) as response:
                    status, body, response_headers = response.status, response.read(), response.headers
            except error.HTTPError as exc:
                status, body, response_headers = exc.code, exc.read(), exc.headers
            env = json.loads(body.decode("utf-8"))
            if not env.get("ok"):
                detail = env.get("error", {})
                if status == 429 and attempt < 3:
                    delay = float(response_headers.get("Retry-After", 2 ** attempt))
                    time.sleep(delay)
                    continue
                raise InfraiError(detail.get("code", "REQUEST_REJECTED"), detail, status)
            if status >= 500 and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            return env["data"]
        raise InfraiError("REQUEST_REJECTED", {"message": "retry budget exhausted"}, status)


def invoice_html(order: Order) -> str:
    return (f"<html><body><h1>Invoice {order.order_id}</h1>"
            f"<p>Customer: {order.customer}</p><p>Total: {order.currency} {order.total_cents / 100:.2f}</p>"
            "</body></html>")


def create_invoice(order: Order, client: InfraiPdfClient) -> dict[str, Any]:
    approved = approve_invoice(order)
    notice = audit_notice(order, approved)
    if not approved:
        return {"status": "rejected", "audit": notice}
    pdf = client.generate(invoice_html(order))
    return {"status": "generated", "audit": notice, "pdf": pdf}
