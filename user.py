from fastapi import APIRouter, HTTPException, status, Depends, Request, Form
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import models, schemas, ultis
from database import get_db

templates = Jinja2Templates(directory="templates")

router = APIRouter(tags=["Users"])


@router.get("/create_user")
def create_user_page(request: Request):
    return templates.TemplateResponse(
        request,
        "create_user.html",
        {"request": request}
    )


@router.post("/users", status_code=status.HTTP_201_CREATED, response_model=schemas.UserOut)
def create_user(
    request:Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):

    hashed_password = ultis.hash_password(password)

    new_user = models.users(
        email=email,
        password=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return templates.TemplateResponse(request , "create_user.html" , context={"id" : new_user.id , "email" : new_user.email , "created_at" : new_user.created_at})


@router.get("/users/{id}", response_model=schemas.UserOut)
def get_user(request:Request , id: int, db: Session = Depends(get_db)):

    user = db.query(models.users).filter(
        models.users.id == id
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return templates.TemplateResponse(request , "get_users.html" , context={"user" : user})