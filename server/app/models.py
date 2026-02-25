from beanie import Document


class Event(Document):
    """Main database model for tracking user events."""

    type: str
    timestamp: int
    user_id: int
    source_url: str
    metadata: dict
