from fastapi import APIRouter, Depends, Request , HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
import models
from database import get_db
import auths
from sqlalchemy.orm import Session
router = APIRouter()

templates = Jinja2Templates(directory="templates")

@router.get("/home")
def home():
    return {"message": "This is home page"}

@router.get("/products")
def products_page(
    request: Request,
    db: Session = Depends(get_db), 

    current_user = Depends(auths.get_current_user)
):
    products = db.query(models.products).all()

    return templates.TemplateResponse(
        request=request,
        name="products.html",
        context={"products": products}
    )
