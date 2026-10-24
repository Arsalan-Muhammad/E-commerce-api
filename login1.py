email = "admin"
password = "admin@512"
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from sympy import false, true

from ultis import verify
from fastapi import APIRouter , FastAPI , Request

router = APIRouter()

templates = Jinja2Templates(directory="templates")


@router.get("/login-page")
def login_page(
    request : Request
):
    return templates.TemplateResponse(
        request,
        "login1.html",
        context= {"email" : email , "password" : password}
    )       
@router.post("/login")
def login(
    Email : str,
    Password : str
):
    if email == Email and password == Password:
        return True
    else:
        return false
