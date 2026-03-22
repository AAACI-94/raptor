"""Project CRUD tests."""


def test_create_project(client):
    """Should create a project and return it."""
    response = client.post("/api/projects", json={
        "title": "Test Paper",
        "topic_description": "AI agent security assessment",
        "venue_profile_id": None,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Paper"
    assert data["status"] == "TOPIC_SELECTED"
    assert data["id"]


def test_list_projects(client):
    """Should list all projects."""
    client.post("/api/projects", json={"title": "Paper 1"})
    client.post("/api/projects", json={"title": "Paper 2"})

    response = client.get("/api/projects")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_get_project(client):
    """Should get a project by ID."""
    create = client.post("/api/projects", json={"title": "My Paper"})
    project_id = create.json()["id"]

    response = client.get(f"/api/projects/{project_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "My Paper"


def test_get_nonexistent_project(client):
    """Should return 404 for nonexistent project."""
    response = client.get("/api/projects/nonexistent")
    assert response.status_code == 404


def test_update_project(client):
    """Should update project fields."""
    create = client.post("/api/projects", json={"title": "Original"})
    project_id = create.json()["id"]

    response = client.put(f"/api/projects/{project_id}", json={
        "title": "Updated Title",
        "topic_description": "New topic",
    })
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"
    assert response.json()["topic_description"] == "New topic"


def test_delete_project(client):
    """Should delete a project."""
    create = client.post("/api/projects", json={"title": "Delete Me"})
    project_id = create.json()["id"]

    response = client.delete(f"/api/projects/{project_id}")
    assert response.status_code == 200

    response = client.get(f"/api/projects/{project_id}")
    assert response.status_code == 404
