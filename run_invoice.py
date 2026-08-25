from src.invoice_service import InfraiPdfClient, Order, PaymentEvent, create_invoice


order = Order(
    order_id="ord_demo",
    customer="Ada Lovelace",
    currency="USD",
    total_cents=2499,
    payment_events=(PaymentEvent("pay_demo", "payment_succeeded", 2499, "2026-08-25T10:00:00Z"),),
    risk_score=22,
)
print(create_invoice(order, InfraiPdfClient()))
