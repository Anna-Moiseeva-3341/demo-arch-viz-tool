import os
import time
from contextlib import asynccontextmanager

import json
import httpx
import pika
import psycopg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

CATALOG = "http://catalog:8000"
AMQP_URL = os.getenv("AMQP_URL")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")

def db():
    return psycopg.connect(host=DB_HOST, dbname=DB_NAME, user="holds", password="pass")

def init_db():
    for _ in range(30):
        try:
            with db() as conn:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS holds ("
                    "id SERIAL PRIMARY KEY, user_id INT NOT NULL, book_id INT NOT NULL)"
                )
            return
        except psycopg.OperationalError:
            time.sleep(1)
    raise RuntimeError("holds-db недоступна")

def publish(event):
    connection = pika.BlockingConnection(pika.URLParameters(AMQP_URL))
    channel = connection.channel()
    channel.queue_declare(queue="hold_created", durable=True)
    channel.basic_publish(exchange="", routing_key="hold_created", body=json.dumps(event))
    connection.close()

@asynccontextmanager
async def lifespan(app):
    init_db()
    yield

app = FastAPI(title="Holds API", version="1.0", lifespan=lifespan)

class HoldIn(BaseModel):
    user_id: int
    book_id: int

@app.post("/holds")
def create_hold(hold: HoldIn):
    response = httpx.post(f"{CATALOG}/books/{hold.book_id}/checkout")
    if not response.is_success:
        raise HTTPException(status_code=response.status_code, detail=response.json().get("detail"))
    book = response.json()

    with db() as conn:
        hold_id = conn.execute(
            "INSERT INTO holds (user_id, book_id) VALUES (%s, %s) RETURNING id",
            (hold.user_id, hold.book_id),
        ).fetchone()[0]

    publish({"hold_id": hold_id, "user_id": hold.user_id, "title": book["title"]})
    return {"id": hold_id, "book": book["title"], "available": book["available"]}

@app.get("/holds/{hold_id}")
def get_hold(hold_id: int):
    with db() as conn:
        row = conn.execute(
            "SELECT id, user_id, book_id FROM holds WHERE id = %s", (hold_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Hold not found")
    return {"id": row[0], "user_id": row[1], "book_id": row[2]}