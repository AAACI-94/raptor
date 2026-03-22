"""Venue profile CRUD endpoints."""

import logging

from fastapi import APIRouter, HTTPException

from app.models.venue import VenueCreate, VenueUpdate
from app.services import venue_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("")
def list_venues():
    """List all venue profiles."""
    venues = venue_service.list_venues()
    return [v.model_dump() for v in venues]


@router.get("/{venue_id}")
def get_venue(venue_id: str):
    """Get a venue profile by ID."""
    try:
        venue = venue_service.get_venue(venue_id)
        return venue.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("")
def create_venue(data: VenueCreate):
    """Create a custom venue profile."""
    venue = venue_service.create_venue(data)
    return venue.model_dump()


@router.put("/{venue_id}")
def update_venue(venue_id: str, data: VenueUpdate):
    """Update a venue profile."""
    try:
        venue = venue_service.update_venue(venue_id, data)
        return venue.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{venue_id}")
def delete_venue(venue_id: str):
    """Delete a custom venue profile."""
    try:
        venue_service.delete_venue(venue_id)
        return {"status": "deleted", "id": venue_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
