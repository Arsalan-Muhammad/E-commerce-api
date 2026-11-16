from fastapi import Depends, HTTPException, status, Request
from jose import JWTError, jwt
from datetime import datetime, timedelta

import schemas

SECRET_KEY = "arsalan/122"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 240


def create_access_token(data: dict):
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return encoded_jwt


def verify_token(token: str, credentials_exception):

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("user_id")

        if user_id is None:
            raise credentials_exception

        token_data = schemas.TokenData(id=user_id)

    except JWTError:
        raise credentials_exception

    return token_data


def get_current_user(request: Request):

    token = request.cookies.get("access_token")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated"
    )

    if not token:
        raise credentials_exception

    return verify_token(token, credentials_exception)
