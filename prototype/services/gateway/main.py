import os

import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

USERS_URL = os.getenv("USERS_URL")
CATALOG_URL = os.getenv("CATALOG_URL")
HOLDS_URL = os.getenv("HOLDS_URL")

app = FastAPI(title="Gateway API", version="1.0")

class HoldIn(BaseModel):
    user_id: int
    book_id: int

def relay(response):
    return JSONResponse(response.json(), status_code=response.status_code)

@app.get("/api/users/{user_id}")
def get_user(user_id: int):
    return relay(httpx.get(f"{USERS_URL}/users/{user_id}"))

@app.get("/api/books")
def list_books():
    return relay(httpx.get(f"{CATALOG_URL}/books"))

@app.get("/api/books/{book_id}")
def get_book(book_id: int):
    return relay(httpx.get(f"{CATALOG_URL}/books/{book_id}"))

@app.post("/api/holds")
def create_hold(hold: HoldIn):
    return relay(httpx.post(f"{HOLDS_URL}/holds", json=hold.model_dump(), timeout=10))

@app.get("/api/holds/{hold_id}")
def get_hold(hold_id: int):
    return relay(httpx.get(f"{HOLDS_URL}/holds/{hold_id}"))