from fastapi import Depends, HTTPException, status, APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import database, schemas, models, ultis, auths

router = APIRouter(tags=["Authentication"])
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
def get_login_page(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {"request": request}
    )


@router.post("/login")
def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(database.get_db)
):

    user = db.query(models.User).filter(
        models.User.email == email
    ).first()

    if not user:
        raise HTTPException(
            status_code=403,
            detail="Invalid Credentials"
        )

    if not ultis.verify(password, user.password):
        raise HTTPException(
            status_code=403,
            detail="Invalid Credentials"
        )

    access_token = auths.create_access_token(
        data={"user_id": user.id}
    )

    response = RedirectResponse(
        url=f"/products",
        status_code=303
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=14400
    )

    return response
