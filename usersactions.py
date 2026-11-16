
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates

from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

import models
import auths

from database import get_db


router = APIRouter()
templates = Jinja2Templates(directory="templates")


# Get the logged-in user, or return None for a guest
def get_optional_user(request: Request, db: Session):

    token = request.cookies.get("access_token")

    if not token:
        return None

    try:
        user_id = auths.verify_token(
            token,
            HTTPException(
                status_code=401,
                detail="Not authenticated"
            )
        )

        return db.query(models.User).filter(
            models.User.id == user_id
        ).first()

    except Exception:
        return None


# Read the guest cart from the browser cookie
def get_guest_cart(request: Request):

    cookie = request.cookies.get("guest_cart")

    if not cookie:
        return []

    try:
        cart = json.loads(cookie)

        if not isinstance(cart, list):
            return []

        return cart

    except (json.JSONDecodeError, TypeError):
        return []


# Save the guest cart in a cookie
def save_guest_cart(response, cart):

    response.set_cookie(
        key="guest_cart",
        value=json.dumps(cart),
        max_age=60 * 60 * 24 * 30,
        httponly=True,
        samesite="lax",
        secure=False
    )


# Merge guest cart items into the logged-in user's database cart
def merge_guest_cart(request: Request, user, db: Session):

    guest_cart = get_guest_cart(request)    

    if not guest_cart:
        return

    cart = db.query(models.Cart).filter(
        models.Cart.user_id == user.id
    ).first()

    if not cart:    
        cart = models.Cart(user_id=user.id)
        db.add(cart)
        db.flush()

    for guest_item in guest_cart:

        try:
            product_id = int(guest_item["id"])
            quantity = int(guest_item["quantity"])
        except (KeyError, TypeError, ValueError):
            continue

        if quantity < 1:
            continue

        product = db.query(models.Product).filter(
            models.Product.id == product_id,
            models.Product.is_active == True
        ).first()

        if not product or product.stock < 1: #pyright:ignore
            continue

        existing = db.query(models.CartItem).filter(
            models.CartItem.cart_id == cart.id,
            models.CartItem.product_id == product_id
        ).first()

        if existing:

            existing.quantity = min(
                existing.quantity + quantity,
                product.stock
            ) 

        else:

            db.add(models.CartItem(
                cart_id=cart.id,
                product_id=product_id,
                quantity=min(quantity, product.stock)
            ))

    db.commit()


# Show all active products
@router.get("/products")
def products_page(
    request: Request,
    db: Session = Depends(get_db)
):

    products = db.query(models.Product).filter(
        models.Product.is_active == True
    ).all()

    user = get_optional_user(request, db)

    return templates.TemplateResponse(
        request=request,
        name="products.html",
        context={
            "products": products,
            "is_logged_in": user is not None
        }
    )


# Add a product to the cart
@router.post("/cart/add/{id}")  
def add_to_cart(
    id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    user = get_optional_user(request, db)

    product = db.query(models.Product).filter(
        models.Product.id == id,
        models.Product.is_active == True
    ).first()

    if not product:
        raise HTTPException(404, "Product not found")

    if product.stock < 1: #pyright:ignore
        raise HTTPException(400, "Out of stock")

    # Guest cart
    if not user:

        cart = get_guest_cart(request)

        existing = next(
            (
                item for item in cart
                if item.get("id") == id
            ),
            None
        )

        if existing:

            if existing["quantity"] >= product.stock:
                raise HTTPException(400, "Not enough stock")

            existing["quantity"] += 1

        else:

            cart.append({
                "id": id,
                "quantity": 1
            })

        response = RedirectResponse(
            "/cart",
            status_code=303
        )

        save_guest_cart(response, cart)

        return response

    # Logged-in user's database cart
    cart = db.query(models.Cart).filter(
        models.Cart.user_id == user.id
    ).first()

    if not cart:

        cart = models.Cart(user_id=user.id)

        db.add(cart)
        db.flush()

    item = db.query(models.CartItem).filter(
        models.CartItem.cart_id == cart.id,
        models.CartItem.product_id == id
    ).first()

    if item:

        if item.quantity >= product.stock: #pyright:ignore
            raise HTTPException(400, "Not enough stock")

        item.quantity += 1 #pyright:ignore

    else:

        db.add(models.CartItem(
            cart_id=cart.id,
            product_id=id,
            quantity=1
        ))

    db.commit()

    return RedirectResponse(
        "/cart",
        status_code=303
    )


# Display the cart page
@router.get("/cart")
def view_cart(
    request: Request,
    db: Session = Depends(get_db)
):

    user = get_optional_user(request, db)

    cart_items = []

    # Guest cart
    if not user:

        guest_cart = get_guest_cart(request)

        for item in guest_cart:

            try:
                product_id = int(item["id"])
                quantity = int(item["quantity"])
            except (KeyError, TypeError, ValueError):
                continue

            if quantity < 1:
                continue

            product = db.query(models.Product).filter(
                models.Product.id == product_id,
                models.Product.is_active == True
            ).first()

            if product and product.stock > 0: #pyright:ignore

                cart_items.append({
                    "id": product.id,
                    "name": product.name,
                    "price": product.price,
                    "image_url": product.image_url,
                    "quantity": min(quantity, product.stock),
                    "stock": product.stock
                })

    # Logged-in user's database cart
    else:

        cart = db.query(models.Cart).filter(
            models.Cart.user_id == user.id
        ).first()

        if cart:

            items = db.query(
                models.CartItem,
                models.Product
            ).join(
                models.Product,
                models.CartItem.product_id == models.Product.id
            ).filter(
                models.CartItem.cart_id == cart.id,
                models.Product.is_active == True
            ).all()

            for item, product in items:

                if product.stock > 0:

                    cart_items.append({
                        "id": product.id,
                        "name": product.name,
                        "price": product.price,
                        "image_url": product.image_url,
                        "quantity": min(item.quantity, product.stock),
                        "stock": product.stock
                    })

    total = sum(
        item["price"] * item["quantity"]
        for item in cart_items
    )

    return templates.TemplateResponse(
        request=request,
        name="cart.html",
        context={
            "cart_items": cart_items,
            "is_logged_in": user is not None,
            "total": total
        }
    )


# Increase or decrease product quantity
@router.post("/cart/update/{id}/{action}")
def update_cart(
    id: int,
    action: str,
    request: Request,
    db: Session = Depends(get_db)
):

    if action not in ["increase", "decrease"]:
        raise HTTPException(400, "Invalid action")

    user = get_optional_user(request, db)

    # Guest cart update
    if not user:

        cart = get_guest_cart(request)

        item = next(
            (
                item for item in cart
                if item.get("id") == id
            ),
            None
        )

        if not item:
            raise HTTPException(404, "Item not found")

        product = db.query(models.Product).filter(
            models.Product.id == id,
            models.Product.is_active == True
        ).first()

        if not product:
            raise HTTPException(404, "Product not found")

        if action == "increase":

            if item["quantity"] < product.stock:
                item["quantity"] += 1

        else:

            item["quantity"] -= 1

            if item["quantity"] <= 0:
                cart.remove(item)

        response = RedirectResponse(
            "/cart",
            status_code=303
        )

        save_guest_cart(response, cart)

        return response

    # Logged-in user's database cart update
    cart = db.query(models.Cart).filter(
        models.Cart.user_id == user.id
    ).first()

    if not cart:
        raise HTTPException(404, "Cart not found")

    item = db.query(models.CartItem).filter(
        models.CartItem.cart_id == cart.id,
        models.CartItem.product_id == id
    ).first()

    if not item:
        raise HTTPException(404, "Item not found")

    if action == "increase":

        product = db.query(models.Product).filter(
            models.Product.id == id,
            models.Product.is_active == True
        ).first()

        if not product:
            raise HTTPException(404, "Product not found")

        if item.quantity < product.stock: #pyright:ignore
            item.quantity += 1 #pyright:ignore

    else:

        item.quantity -= 1 #pyright:ignore

        if item.quantity <= 0: #pyright:ignore
            db.delete(item)

    db.commit()

    return RedirectResponse(
        "/cart",
        status_code=303
    )


# Remove a product from the cart
@router.post("/cart/delete/{id}")
def delete_cart_item(
    id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    user = get_optional_user(request, db)

    # Guest cart
    if not user:

        cart = get_guest_cart(request)

        cart = [
            item for item in cart
            if item.get("id") != id
        ]

        response = RedirectResponse(
            "/cart",
            status_code=303
        )

        save_guest_cart(response, cart)

        return response

    # Logged-in user's database cart
    cart = db.query(models.Cart).filter(
        models.Cart.user_id == user.id
    ).first()

    if cart:

        item = db.query(models.CartItem).filter(
            models.CartItem.cart_id == cart.id,
            models.CartItem.product_id == id
        ).first()

        if item:
            db.delete(item)
            db.commit()

    return RedirectResponse(
        "/cart",
        status_code=303
    )
