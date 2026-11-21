import json
import os
import stripe
from decimal import Decimal
from typing import Any
from dotenv import load_dotenv
from fastapi import (
    APIRouter, Request, Header, HTTPException, status, Form, Depends
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
import models
from database import get_db
from auths import get_current_user

load_dotenv()

router = APIRouter()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
ENDPOINT_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


@router.post("/create/checkout")
def create_checkout_session(
    product_id: int = Form(...),
    quantity: int = Form(...),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user)
):
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="Stripe API key is missing")

    product = db.query(models.Product).filter(
        models.Product.id == product_id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if quantity < 1 or quantity > product.stock:
        raise HTTPException(status_code=400, detail="Invalid quantity selected")

    unit_amount = int(Decimal(str(product.price)) * 100)
    if unit_amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid product price")

    try:
        domain_url = "http://localhost:8000"
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    "price_data": {
                        "currency": "pkr",
                        "unit_amount": unit_amount,
                        "product_data": {
                            "name": product.name
                        }
                    },
                    "quantity": quantity
                }
            ],
            mode="payment",
            shipping_address_collection={
                "allowed_countries": ["PK"],
            },
            phone_number_collection={
                "enabled": True,
            },
            success_url=f"{domain_url}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{domain_url}/cancel",
            metadata={
                "product_id": str(product.id),
                "product_name": str(product.name),
                "unit_price": str(product.price),
                "quantity": str(quantity),
                "user_id": str(current_user.id),
            }
        )

        if not checkout_session.url:
            raise HTTPException(
                status_code=500, detail="Stripe did not return a checkout URL"
            )

        return RedirectResponse(
            url=checkout_session.url, status_code=status.HTTP_303_SEE_OTHER
        )
    except stripe.StripeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/success", response_class=HTMLResponse)
def success(session_id: str | None = None):
    return f"""
    <h1>Payment Successful!</h1>
    <p>Checkout Session ID: {session_id}</p>
    <p>Your payment is being verified.</p>
    """


@router.get("/cancel", response_class=HTMLResponse)
def cancel():
    return """
    <h1>Payment Cancelled</h1>
    <p>You can try again anytime.</p>
    """


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(
        default=None, alias="Stripe-Signature"
    ),
    db: Session = Depends(get_db)
):
    if not ENDPOINT_SECRET:
        raise HTTPException(
            status_code=500, detail="Webhook secret is missing"
        )

    payload = await request.body()

    try:
        stripe.Webhook.construct_event(
            payload, stripe_signature, ENDPOINT_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event: dict[str, Any] = json.loads(payload)

    if event["type"] == "checkout.session.completed":
        session: dict[str, Any] = event["data"]["object"]
        session_id = session["id"]

        existing_order = db.query(models.Order).filter(
            models.Order.stripe_session_id == session_id
        ).first()
        if existing_order:
            return {"status": "already_processed"}

        if session.get("payment_status") != "paid":
            return {"status": "payment_not_completed"}

        metadata = session.get("metadata") or {}
        required_keys = {"product_id", "quantity", "user_id", "product_name", "unit_price"}
        if not required_keys.issubset(metadata.keys()):
            return {"status": "ignored_missing_metadata"}

        product_id = int(metadata["product_id"])
        quantity = int(metadata["quantity"])
        user_id = int(metadata["user_id"])
        product_name = metadata["product_name"]
        unit_price = Decimal(metadata["unit_price"])

        customer_details = session.get("customer_details") or {}
        phone_number = customer_details.get("phone") or ""

        shipping_details = session.get("shipping_details") or {}
        address_obj = (
            shipping_details.get("address")
            or customer_details.get("address")
            or {}
        )
        address_parts = [
            address_obj.get("line1"),
            address_obj.get("line2"),
            address_obj.get("city"),
            address_obj.get("state"),
            address_obj.get("postal_code"),
            address_obj.get("country"),
        ]
        shipping_address = ", ".join(part for part in address_parts if part)

        product = db.query(models.Product).filter(
            models.Product.id == product_id
        ).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        total_amount = unit_price * quantity
        payment_intent_id = session.get("payment_intent")
        if isinstance(payment_intent_id, dict):
            payment_intent_id = payment_intent_id.get("id")

        try:
            order = models.Order(
                user_id=user_id,
                total_amount=total_amount,
                status="processing",
                payment_status="paid",
                shipping_address=shipping_address,
                phone_number=phone_number,
                stripe_session_id=session_id
            )
            db.add(order)
            db.flush()

            order_item = models.OrderItem(
                order_id=order.id,
                product_id=product_id,
                product_name=product_name,
                quantity=quantity,
                unit_price=unit_price,
                subtotal=total_amount
            )

            payment = models.Payment(
                user_id=user_id,
                order_id=order.id,
                stripe_session_id=session_id,
                stripe_payment_intent_id=payment_intent_id,
                amount=int(total_amount),
                currency="PKR",
                status="paid",
                payment_method="stripe_checkout"
            )

            db.add(order_item)
            db.add(payment)

            if product.stock >= quantity:
                product.stock -= quantity
            else:
                order.status = "stock_review"

            db.commit()
            print(f"Order created successfully: {order.id}")
            print(f"Payment received: {session_id}")
        except Exception:
            db.rollback()
            raise

    elif event["type"] == "payment_intent.payment_failed":
        payment_intent: dict[str, Any] = event["data"]["object"]
        last_error = payment_intent.get("last_payment_error") or {}
        print("Payment Failed:", last_error.get("message"))

    return {"status": "success"}
