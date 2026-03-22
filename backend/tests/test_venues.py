"""Venue profile tests."""


def test_list_venues(client):
    """Should return seeded default venues."""
    response = client.get("/api/venues")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 8  # 8 default venues

    # Verify key venues exist
    ids = {v["id"] for v in data}
    assert "sans_reading_room" in ids
    assert "ieee_sp" in ids
    assert "acm_ccs" in ids
    assert "dark_reading" in ids
    assert "linkedin_article" in ids


def test_get_venue(client):
    """Should get a specific venue profile."""
    response = client.get("/api/venues/sans_reading_room")
    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "SANS Reading Room"
    assert data["venue_type"] == "practitioner_repository"
    assert "quality_rubric" in data["profile_data"]
    assert "structural_template" in data["profile_data"]


def test_venue_rubric_dimensions(client):
    """SANS rubric should weight practitioner_utility highest."""
    response = client.get("/api/venues/sans_reading_room")
    rubric = response.json()["profile_data"]["quality_rubric"]
    dims = {d["name"]: d["weight"] for d in rubric["dimensions"]}
    assert dims["practitioner_utility"] >= 0.25  # Highest weight
    assert rubric["passing_threshold"] == 7.0


def test_ieee_different_from_sans(client):
    """IEEE should have different rubric weights than SANS."""
    sans = client.get("/api/venues/sans_reading_room").json()
    ieee = client.get("/api/venues/ieee_sp").json()

    sans_dims = {d["name"]: d["weight"] for d in sans["profile_data"]["quality_rubric"]["dimensions"]}
    ieee_dims = {d["name"]: d["weight"] for d in ieee["profile_data"]["quality_rubric"]["dimensions"]}

    # IEEE should weight novelty higher than SANS
    assert ieee_dims.get("novelty", 0) > sans_dims.get("novelty", 0)


def test_cannot_delete_builtin_venue(client):
    """Should not allow deleting built-in venues."""
    response = client.delete("/api/venues/sans_reading_room")
    assert response.status_code == 400
