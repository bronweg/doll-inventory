"""
Pydantic schemas for search suggestions.
"""
from typing import Optional, List
from pydantic import BaseModel


class SuggestionItem(BaseModel):
    """A single suggestion item."""
    id: int
    name: str
    primary_photo_url: Optional[str] = None
    location: str
    bag_number: Optional[int] = None

    class Config:
        from_attributes = True


class SuggestionsResponse(BaseModel):
    """Response for suggestions endpoint."""
    q: str
    suggestions: List[SuggestionItem]

