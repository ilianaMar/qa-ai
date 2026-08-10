import pytest


@pytest.fixture(scope="session")
def api(playwright):
    context = playwright.request.new_context(base_url="http://127.0.0.1:8002")
    health = context.get("/health")
    if not health.ok:
        context.dispose()
        pytest.exit(
            "API is not running. Start it with: python run.py",
            returncode=1,
        )
    yield context
    context.dispose()


@pytest.fixture(autouse=True)
def reset_store(api):
    response = api.post("/_qa/reset")
    assert response.ok
    yield
