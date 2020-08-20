import pytest

@pytest.fixture
def client():
    from mflbackend.backend import app

    return app.test_client()
