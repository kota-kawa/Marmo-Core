"""Moltbook API endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel


router = APIRouter(prefix="/moltbook", tags=["moltbook"])


class MoltbookPost(BaseModel):
    """Moltbook post model."""
    id: str
    author: str
    author_name: str
    author_avatar: Optional[str] = None
    content: str
    url: str
    timestamp: str
    likes: int = 0
    comments: int = 0


class MoltbookPostResponse(BaseModel):
    """Response for fetching a Moltbook post."""
    success: bool
    post: Optional[MoltbookPost] = None
    message: Optional[str] = None


@router.get("/posts/{post_id}", response_model=MoltbookPostResponse)
async def get_moltbook_post(post_id: str) -> MoltbookPostResponse:
    """
    Fetch a Moltbook post by ID for display.
    
    This is used to display the source post on campaign detail pages
    when the campaign was created from a Moltbook mention.
    """
    # TODO: Implement actual Moltbook API integration
    # For now, return a placeholder response
    # The actual integration would use the MoltbookIntegration class
    
    # Placeholder - in production this would call Moltbook API
    return MoltbookPostResponse(
        success=False,
        post=None,
        message="Moltbook API integration not yet configured. Post data is stored in campaign source fields.",
    )


@router.get("/search")
async def search_moltbook_posts(
    query: str,
    limit: int = 20,
) -> dict:
    """
    Search Moltbook for posts (e.g., related to a campaign or agent).
    
    This enables displaying related Moltbook discussions.
    """
    # TODO: Implement actual Moltbook search
    return {
        "success": False,
        "posts": [],
        "message": "Moltbook search not yet configured",
    }
