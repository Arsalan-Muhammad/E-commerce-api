
from fastapi import FastAPI, Depends , APIRouter
import admincations
import models , usersactions , admincations
from starlette.middleware.sessions import SessionMiddleware
from database import Base, get_db, engine
from sqlalchemy.orm import Session
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key="21212121212"
)

app.mount("/static", StaticFiles(directory="static"), name="static")

Base.metadata.create_all(bind=engine)

app.include_router(usersactions.router)
app.include_router(admincations.router)
