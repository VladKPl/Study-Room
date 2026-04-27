def test_cors_preflight_allows_frontend_origin(client):
    response = client.options(
        "/api/v1/courses",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_does_not_allow_unknown_origin(client):
    response = client.get(
        "/api/v1/courses",
        headers={"Origin": "http://evil.local"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
