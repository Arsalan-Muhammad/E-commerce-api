from email.policy import HTTP

from fastapi import APIRouter, Depends, HTTPException, Request, Form , status
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import models
from database import get_db
from auths import get_current_user


router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/products")
def add_product_page(request: Request):
    return templates.TemplateResponse(request=request, name="admin.html")


@router.post("/products")
def add_product(
    request: Request,
    name: str = Form(...),
    price: float = Form(...),
    quantity: int = Form(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    product = models.products(      
        name=name,
        price=price,
        stock=quantity
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={"product": product}
    )
