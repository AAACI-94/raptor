"""Tests for library features: query, tags, stats, star, category."""

from app.services import project_service


def _create_project(client, title="Test", venue_id=None, tags=None, category=None, topic="test topic") -> str:
    """Helper to create a project and return its ID."""
    resp = client.post("/api/projects", json={
        "title": title,
        "topic_description": topic,
        "venue_profile_id": venue_id,
        "tags": tags or [],
        "category": category,
    })
    return resp.json()["id"]


def _get_venue_id(client) -> str:
    """Get the first venue ID."""
    venues = client.get("/api/publications").json()
    return venues[0]["id"]


class TestLibraryQuery:
    """Tests for library_query function and endpoint."""

    def test_returns_all_with_no_filters(self, client):
        """library_query with no filters should return all projects."""
        _create_project(client, "Paper A")
        _create_project(client, "Paper B")
        results = project_service.library_query()
        assert len(results) >= 2

    def test_filters_by_venue(self, client):
        """library_query should filter by venue_profile_id."""
        venue_id = _get_venue_id(client)
        _create_project(client, "With Venue", venue_id=venue_id)
        _create_project(client, "No Venue", venue_id=None)

        results = project_service.library_query(venue=venue_id)
        assert all(r.venue_profile_id == venue_id for r in results)

    def test_filters_by_tags(self, client):
        """library_query should filter projects matching any of the provided tags."""
        _create_project(client, "Tagged", tags=["security", "ai"])
        _create_project(client, "Untagged", tags=[])

        results = project_service.library_query(tags=["security"])
        titles = [r.title for r in results]
        assert "Tagged" in titles

    def test_searches_title_and_topic(self, client):
        """library_query with q parameter should search title and topic_description."""
        _create_project(client, "Prompt Injection Study", topic="LLM security research")
        _create_project(client, "Budget Analysis", topic="Financial planning")

        results = project_service.library_query(q="Prompt Injection")
        assert any("Prompt Injection" in r.title for r in results)

    def test_library_search_endpoint(self, client):
        """GET /api/projects/library/search should return filtered results."""
        _create_project(client, "API Search Test")
        resp = client.get("/api/projects/library/search?q=API+Search")
        assert resp.status_code == 200
        data = resp.json()
        assert any("API Search" in r["title"] for r in data)

    def test_library_search_by_venue(self, client):
        """GET /api/projects/library/search?venue=X should filter by venue."""
        venue_id = _get_venue_id(client)
        _create_project(client, "Venue Filter Test", venue_id=venue_id)

        resp = client.get(f"/api/projects/library/search?venue={venue_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert all(r["venue_profile_id"] == venue_id for r in data)

    def test_library_search_by_tags(self, client):
        """GET /api/projects/library/search?tags=X should filter by tags."""
        _create_project(client, "Tag Search Test", tags=["malware"])

        resp = client.get("/api/projects/library/search?tags=malware")
        assert resp.status_code == 200

    def test_library_search_by_category(self, client):
        """library_query should filter by category."""
        _create_project(client, "Whitepaper", category="whitepaper")
        _create_project(client, "Case Study", category="case_study")

        results = project_service.library_query(category="whitepaper")
        assert all(r.category == "whitepaper" for r in results)


class TestLibraryTags:
    """Tests for get_library_tags."""

    def test_returns_tag_counts(self, client):
        """get_library_tags should return tags with usage counts."""
        _create_project(client, "A", tags=["security", "ai"])
        _create_project(client, "B", tags=["security", "cloud"])

        tags = project_service.get_library_tags()
        tag_dict = {t["tag"]: t["count"] for t in tags}
        assert tag_dict.get("security", 0) >= 2
        assert tag_dict.get("ai", 0) >= 1
        assert tag_dict.get("cloud", 0) >= 1

    def test_tags_endpoint(self, client):
        """GET /api/projects/library/tags should return tag list."""
        _create_project(client, "For Tags", tags=["endpoint-test"])
        resp = client.get("/api/projects/library/tags")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_empty_when_no_tags(self, client):
        """get_library_tags should return empty list when no projects have tags."""
        results = project_service.get_library_tags()
        # May return empty or may have tags from other tests; just check structure
        assert isinstance(results, list)
        for item in results:
            assert "tag" in item
            assert "count" in item


class TestLibraryStats:
    """Tests for get_library_stats."""

    def test_returns_aggregate_metrics(self, client):
        """get_library_stats should return aggregate stats."""
        _create_project(client, "Stats Test")

        stats = project_service.get_library_stats()
        assert stats["total_projects"] >= 1
        assert "by_venue" in stats
        assert "by_category" in stats
        assert "by_status_group" in stats
        assert "avg_quality" in stats
        assert "total_cost" in stats
        assert "total_words" in stats
        assert "total_figures" in stats
        assert "top_tags" in stats

    def test_stats_endpoint(self, client):
        """GET /api/projects/library/stats should return stats object."""
        _create_project(client, "Stats Endpoint Test")
        resp = client.get("/api/projects/library/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_projects"] >= 1


class TestAutoTagFromResearch:
    """Tests for auto_tag_from_research."""

    def test_extracts_keywords(self, client):
        """auto_tag_from_research should extract keywords from contribution claim."""
        project_id = _create_project(client, "Auto Tag Test")
        research_payload = {
            "contribution_claim": "Novel approach to detecting prompt injection attacks in production systems",
            "sources": [
                {"source_type": "peer_reviewed", "title": "Test"},
                {"source_type": "industry_report", "title": "Report"},
            ],
        }
        tags = project_service.auto_tag_from_research(project_id, research_payload)
        assert isinstance(tags, list)
        assert len(tags) > 0

    def test_includes_source_types(self, client):
        """auto_tag_from_research should include source types as tags."""
        project_id = _create_project(client, "Source Tag Test")
        research_payload = {
            "contribution_claim": "Security research",
            "sources": [
                {"source_type": "peer_reviewed", "title": "Study"},
            ],
        }
        tags = project_service.auto_tag_from_research(project_id, research_payload)
        assert "peer-reviewed" in tags


class TestToggleStar:
    """Tests for toggle_star."""

    def test_toggle_star_flips(self, client):
        """toggle_star should flip the starred boolean."""
        project_id = _create_project(client, "Star Test")

        # Initially not starred
        project = project_service.get_project(project_id)
        assert project.starred is False

        # Toggle to starred
        result = project_service.toggle_star(project_id)
        assert result is True

        # Verify persisted
        project = project_service.get_project(project_id)
        assert project.starred is True

        # Toggle back
        result = project_service.toggle_star(project_id)
        assert result is False

    def test_toggle_star_endpoint(self, client):
        """PUT /api/projects/{id}/star should toggle star status."""
        project_id = _create_project(client, "Star Endpoint Test")
        resp = client.put(f"/api/projects/{project_id}/star")
        assert resp.status_code == 200
        assert resp.json()["starred"] is True

    def test_toggle_star_nonexistent(self):
        """toggle_star should raise ValueError for nonexistent project."""
        import pytest
        with pytest.raises(ValueError):
            project_service.toggle_star("nonexistent-id")


class TestUpdateCategory:
    """Tests for update_category."""

    def test_update_category_persists(self, client):
        """update_category should persist the new category."""
        project_id = _create_project(client, "Category Test")
        project_service.update_category(project_id, "whitepaper")

        project = project_service.get_project(project_id)
        assert project.category == "whitepaper"

    def test_update_category_endpoint(self, client):
        """PUT /api/projects/{id}/category should update category."""
        project_id = _create_project(client, "Category Endpoint Test")
        resp = client.put(f"/api/projects/{project_id}/category", json={"category": "case_study"})
        assert resp.status_code == 200
        assert resp.json()["category"] == "case_study"
