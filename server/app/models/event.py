from datetime import datetime
from beanie import Document


class Event(Document):
    """Main database model for tracking user events."""

    type: str
    timestamp: datetime
    user_id: str
    source_url: str
    metadata: dict
