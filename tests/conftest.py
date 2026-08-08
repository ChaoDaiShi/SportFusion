import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def app():
    from main import app as fastapi_app

    return fastapi_app


@pytest.fixture()
def client(app):
    return TestClient(app, raise_server_exceptions=False)
