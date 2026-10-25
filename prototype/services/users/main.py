import os
import time
from contextlib import asynccontextmanager

import json
import psycopg
import redis
from fastapi import FastAPI, HTTPException

DB_URL = os.getenv("DB_URL")
cache = redis.Redis(host=os.getenv("REDIS_HOST"), port=6379, decode_responses=True)

def init_db():
    for _ in range(30):
        try:
            with psycopg.connect(DB_URL) as conn:
                conn.execute("CREATE TABLE IF NOT EXISTS users (id INT PRIMARY KEY, name TEXT NOT NULL)")
                conn.execute("INSERT INTO users VALUES (1, 'Anna'), (2, 'Elena'), (3, 'Boris') ON CONFLICT DO NOTHING")
            return
        except psycopg.OperationalError:
            time.sleep(1)
    raise RuntimeError("users-db недоступна")

@asynccontextmanager
async def lifespan(app):
    init_db()
    yield

app = FastAPI(title="Users API", version="1.0", lifespan=lifespan)

@app.get("/users/{user_id}")
def get_user(user_id: int):
    cached = cache.get(f"user:{user_id}")
    if cached:
        return json.loads(cached)

    with psycopg.connect(DB_URL) as conn:
        row = conn.execute("SELECT id, name FROM users WHERE id = %s", (user_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")

    user = {"id": row[0], "name": row[1]}
    cache.set(f"user:{user_id}", json.dumps(user, ensure_ascii=False), ex=60)
    return user