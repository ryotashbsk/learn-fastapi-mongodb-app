from datetime import UTC, datetime
from typing import Mapping

import pytest
from bson.objectid import ObjectId
from fastapi.testclient import TestClient
from pymongo.errors import PyMongoError

import app as api_app


class FakeAdmin:
    should_fail = False

    def command(self, name: str) -> dict[str, object]:
        if self.should_fail:
            raise PyMongoError('ping failed')

        return {'ok': 1, 'command': name}


class FakeMongoClient:
    def __init__(self) -> None:
        self.admin = FakeAdmin()


class FakeCursor:
    def __init__(self, items: list[Mapping[str, object]]) -> None:
        self.items = items

    def sort(self, field_name: str, direction: int) -> list[Mapping[str, object]]:
        return sorted(self.items, key=lambda item: str(item[field_name]))


class FakeItemsCollection:
    def __init__(self) -> None:
        self.items: list[Mapping[str, object]] = [
            {
                '_id': ObjectId('000000000000000000000001'),
                'name': 'Banana',
                'description': 'Initial banana',
                'created_at': datetime(2026, 1, 2, tzinfo=UTC),
            },
            {
                '_id': ObjectId('000000000000000000000002'),
                'name': 'Apple',
                'description': 'Initial apple',
                'created_at': datetime(2026, 1, 1, tzinfo=UTC),
            },
        ]

    def find(self) -> FakeCursor:
        return FakeCursor(self.items)


@pytest.fixture
def fake_mongo_client() -> FakeMongoClient:
    return FakeMongoClient()


@pytest.fixture
def fake_collection() -> FakeItemsCollection:
    return FakeItemsCollection()


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch,
    fake_mongo_client: FakeMongoClient,
    fake_collection: FakeItemsCollection,
) -> TestClient:
    monkeypatch.setattr(api_app, 'mongo_client', fake_mongo_client)
    monkeypatch.setattr(api_app, 'items_collection', fake_collection)

    return TestClient(api_app.app)


def test_index(client: TestClient) -> None:
    response = client.get('/')

    assert response.status_code == 200
    assert response.json() == {'message': 'Hello FastAPI + MongoDB'}


def test_health(client: TestClient) -> None:
    response = client.get('/health')

    assert response.status_code == 200
    assert response.json() == {'status': 'ok', 'database': 'connected'}


def test_health_error(
    client: TestClient,
    fake_mongo_client: FakeMongoClient,
) -> None:
    fake_mongo_client.admin.should_fail = True

    response = client.get('/health')

    assert response.status_code == 500
    assert response.json() == {'status': 'error', 'detail': 'ping failed'}


def test_get_items(client: TestClient) -> None:
    response = client.get('/items')

    assert response.status_code == 200
    assert response.json() == {
        'items': [
            {
                'id': '000000000000000000000002',
                'name': 'Apple',
                'description': 'Initial apple',
                'created_at': '2026-01-01T00:00:00+00:00',
            },
            {
                'id': '000000000000000000000001',
                'name': 'Banana',
                'description': 'Initial banana',
                'created_at': '2026-01-02T00:00:00+00:00',
            },
        ]
    }
