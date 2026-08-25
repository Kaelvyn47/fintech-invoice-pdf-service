from src.invoice_service import Order, PaymentEvent, approve_invoice, audit_notice


def test_paid_low_risk_order_is_approved_and_audited() -> None:
    order = Order("ord_42", "Mina", "USD", 12500,
                  (PaymentEvent("pay_1", "payment_succeeded", 12500, "2026-08-25T10:00:00Z"),), 18)
    assert approve_invoice(order) is True
    assert audit_notice(order, True)["event"] == "invoice_queued"


def test_high_risk_order_is_rejected_even_when_paid() -> None:
    order = Order("ord_43", "Kai", "USD", 1000,
                  (PaymentEvent("pay_2", "payment_succeeded", 1000, "2026-08-25T10:00:00Z"),), 91)
    assert approve_invoice(order) is False
    assert audit_notice(order, False)["reason"] == "risk_or_payment_review"
