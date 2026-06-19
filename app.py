import os
from datetime import datetime
from typing import Mapping

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'sample_app')
MONGO_TLS_CA_FILE = os.getenv('MONGO_TLS_CA_FILE')

if MONGO_TLS_CA_FILE:
    mongo_client: MongoClient[Mapping[str, object]] = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000,
        tls=True,
        tlsCAFile=MONGO_TLS_CA_FILE,
    )
else:
    mongo_client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000,
    )

db: Database[Mapping[str, object]] = mongo_client[MONGO_DB_NAME]
items_collection: Collection[Mapping[str, object]] = db['items']

app = FastAPI(title='FastAPI + MongoDB')


class MessageResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str
    database: str


class ItemResponse(BaseModel):
    id: str
    name: str
    description: str
    created_at: str | None


class ItemsResponse(BaseModel):
    items: list[ItemResponse]


def serialize_item(item: Mapping[str, object]) -> ItemResponse:
    created_at = item.get('created_at')

    return ItemResponse(
        id=str(item['_id']),
        name=str(item['name']),
        description=str(item.get('description', '')),
        created_at=created_at.isoformat() if isinstance(created_at, datetime) else None,
    )


@app.get('/', response_model=MessageResponse)
def index() -> MessageResponse:
    return MessageResponse(message='Hello FastAPI + MongoDB')


@app.get('/health', response_model=HealthResponse)
def health() -> HealthResponse | JSONResponse:
    try:
        mongo_client.admin.command('ping')
        return HealthResponse(status='ok', database='connected')
    except PyMongoError as exc:
        return JSONResponse(
            status_code=500,
            content={'status': 'error', 'detail': str(exc)},
        )


@app.get('/items', response_model=ItemsResponse)
def get_items() -> ItemsResponse:
    items = items_collection.find().sort('name', ASCENDING)
    return ItemsResponse(items=[serialize_item(item) for item in items])
