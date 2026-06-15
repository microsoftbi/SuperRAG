def test_health_endpoint(test_client):
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_upload_unsupported_file(test_client):
    response = test_client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.exe", b"fake content", "application/x-msdownload")},
        data={"title": "test"},
    )
    assert response.status_code == 400
