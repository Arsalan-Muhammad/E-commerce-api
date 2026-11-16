import os
import stripe
from fastapi import Request, Header, HTTPException, status, APIRouter, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import models
from database import get_db

load_dotenv()

router = APIRouter()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
ENDPOINT_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

@router.post("/create/checkout")
def create_checkout_session(
    product_id: int = Form(...),
    quantity: int = Form(...),
    db: Session = Depends(get_db)
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if quantity < 1 or quantity > product.stock: #pyright:ignore
        raise HTTPException(status_code=400, detail="Invalid quantity selected")

    try:
        domain_url = "http://localhost:8000"
        unit_amount = int(round(product.price * 100))

        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    "price_data": {
                        "currency": "pkr",
                        "unit_amount": unit_amount,
                        "product_data": {
                            "name": product.name,
                        },
                    },
                    "quantity": quantity,
                },
            ],
            mode="payment",
            success_url=f"{domain_url}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{domain_url}/cancel",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return RedirectResponse(url=checkout_session.url, status_code=status.HTTP_303_SEE_OTHER)

@router.get("/success", response_class=HTMLResponse)
def success(session_id: str = None):
    return f"<h1>Payment Successful!</h1><p>Session ID: {session_id}</p>"

@router.get("/cancel", response_class=HTMLResponse)
def cancel():
    return "<h1>Payment Cancelled</h1><p>You can try again anytime.</p>"

@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, ENDPOINT_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        session_id = session["id"]
        customer_email = session.get("customer_details", {}).get("email")
        print(f"Success! Checkout Session ID: {session_id}")
        print(f"Customer Email: {customer_email}")
    elif event["type"] == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        print(f"Payment Failed: {payment_intent.get('last_payment_error', {}).get('message')}")

    return {"status": "success"}
