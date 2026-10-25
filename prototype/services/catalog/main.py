import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pymongo import MongoClient, ReturnDocument

client = MongoClient(os.getenv("MONGO_URI"))
books = client.get_default_database()["books"]

BOOKS = [
    {"_id": 1, "title": "Преступление и наказание", "available": 3},
    {"_id": 2, "title": "Капитанская дочка", "available": 1},
]

@asynccontextmanager
async def lifespan(app):
    if books.count_documents({})==0:
        books.insert_many(BOOKS)
    yield

app = FastAPI(title="Catalog API", version="1.0", lifespan=lifespan)

@app.get("/books")
def list_books():
    return list(books.find())

@app.get("/books/{book_id}")
def get_book(book_id: int):
    book = books.find_one({"_id": book_id})
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@app.post("/books/{book_id}/checkout")
def checkout_book(book_id: int):
    book = books.find_one_and_update(
        {"_id": book_id, "available": {"$gt": 0}},
        {"$inc": {"available": -1}},
        return_document=ReturnDocument.AFTER,
    )
    if book is not None:
        return book
    if books.count_documents({"_id": book_id}) == 0:
        raise HTTPException(status_code=404, detail="Book not found")
    raise HTTPException(status_code=409, detail="No available books")