from fastapi import APIRouter, Depends, Request , HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
import models
from database import get_db
from sqlalchemy.orm import Session

router = APIRouter()

templates = Jinja2Templates(directory="templates")

@router.get("/home")
def home():
    return {"message": "This is home page"}

@router.get("/products-page")
def products_page(
    request: Request,
    db: Session = Depends(get_db)
):
    products = db.query(models.products).all()

    return templates.TemplateResponse(
        request=request,
        name="products.html",
        context={"products": products}
    )
@router.post("/cart/add/{product_id}")
def add_to_cart(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    product = db.query(models.products).filter(
        models.products.id == product_id
    ).first()

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    cart = request.session.setdefault("cart", {})
    key = str(product_id)

    if cart.get(key, 0) >= product.stock:
        raise HTTPException(status_code=400, detail="Not enough stock")

    cart[key] = cart.get(key, 0) + 1
    request.session["cart"] = cart

    return RedirectResponse("/cart", status_code=303)


@router.get("/cart")
def view_cart(
    request: Request,
    db: Session = Depends(get_db)
):
    cart = request.session.get("cart", {})
    products = db.query(models.products).filter(
        models.products.id.in_([int(pid) for pid in cart])
    ).all() if cart else []

    items = []
    total = 0

    for product in products:
        quantity = cart[str(product.id)]
        subtotal = product.price * quantity
        total += subtotal

        items.append({
            "product": product,
            "quantity": quantity,
            "subtotal": subtotal
        })

    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory="templates")

    return templates.TemplateResponse(
        request=request,
        name="cart.html",
        context={"items": items, "total": total}
    )