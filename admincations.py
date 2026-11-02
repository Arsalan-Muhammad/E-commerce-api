from fastapi import APIRouter, Form, HTTPException, Request, status, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import models
from database import get_db
router = APIRouter()
templates = Jinja2Templates(directory="templates")

ADMIN_EMAIL = "admin@gmail.com"
ADMIN_PASSWORD = "admin@512"

@router.get("/admin-login-page")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login1.html", {"request": request})

@router.post("/adminlogin")
def login(Email: str = Form(...), Password: str = Form(...)):
    if Email == ADMIN_EMAIL and Password == ADMIN_PASSWORD:
        response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="admin_session", value="authenticated", httponly=True)
        return response
    else:
        return RedirectResponse(url="/admin-login-page?error=1", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/dashboard")
def show_dashboard(request: Request):
    session = request.cookies.get("admin_session")
    if session != "authenticated":
        return RedirectResponse(url="/admin-login-page", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "dashboard.html", {"request": request})

@router.post("/admin/products/add")
def add_product(
    request: Request,
    name: str = Form(...),
    price: float = Form(...),
    quantity: int = Form(...),
    db: Session = Depends(get_db)
):
    session = request.cookies.get("admin_session")
    if session != "authenticated":
        return RedirectResponse(url="/admin-login-page", status_code=status.HTTP_303_SEE_OTHER)
    
    new_product = models.products(name=name, price=price, stock=quantity)
    db.add(new_product)
    db.commit()
    
    return templates.TemplateResponse(request, "dashboard.html", {
        "request": request, 
        "msg": "🎉 Product added successfully!"
    })

@router.get("/admin/products/view")
def view_products_page(request: Request, db: Session = Depends(get_db)):
    session = request.cookies.get("admin_session")
    if session != "authenticated":
        return RedirectResponse(url="/admin-login-page", status_code=status.HTTP_303_SEE_OTHER)
    
    all_products = db.query(models.products).all()
    return templates.TemplateResponse(request, "view_products.html", {
        "request": request, 
        "products": all_products
    })

@router.get("/admin/products/update-page")
def update_products_page(request: Request):
    session = request.cookies.get("admin_session")
    if session != "authenticated":
        return RedirectResponse(url="/admin-login-page", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "update_product.html", {"request": request})

@router.post("/admin/update/products")
def update_product_action(
    request: Request,
    id: int = Form(...),
    name: str = Form(...),
    price: float = Form(...),
    quantity: int = Form(...),
    db: Session = Depends(get_db)
):
    session = request.cookies.get("admin_session")
    if session != "authenticated":
        return RedirectResponse(url="/admin-login-page", status_code=status.HTTP_303_SEE_OTHER)

    product = db.query(models.products).filter(models.products.id == id).first()
    if not product:
        return templates.TemplateResponse(request, "update_product.html", {
            "request": request,
            "msg": f"Product with id {id} does not exist."
        })

    product.name = name #pyright:ignore
    product.price = price #pyright:ignore
    product.stock = quantity #pyright:ignore
    db.commit()

    return templates.TemplateResponse(request, "update_product.html", {
        "request": request,
        "msg": f"Product {id} updated successfully!"
    })

@router.get("/admin/delete/products-page")
def delete_products_page(request: Request):
    session = request.cookies.get("admin_session")
    if session != "authenticated":
        return RedirectResponse(url="/admin-login-page", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "delete_products.html", {"request": request})

@router.post("/admin/delete/products")
def delete_product(
    request: Request, 
    id: int = Form(...), 
    db: Session = Depends(get_db)
):
    session = request.cookies.get("admin_session")
    if session != "authenticated":
        return RedirectResponse(url="/admin-login-page", status_code=status.HTTP_303_SEE_OTHER)

    product = db.query(models.products).filter(models.products.id == id).first()
    
    if not product:
        return templates.TemplateResponse(request, "delete_products.html", {
            "request": request, 
            "msg": f"Product with id {id} does not exist."
        })
    
    db.delete(product) 
    db.commit()
    
    return templates.TemplateResponse(request, "delete_products.html", {
        "request": request, 
        "msg": f"Product {id} deleted successfully!" 
    })
