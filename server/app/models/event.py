from datetime import datetime
import pymongo
from beanie import Document


class Event(Document):
    """Main database model for tracking user events."""

    type: str
    timestamp: datetime
    user_id: str
    source_url: str
    metadata: dict

    class Settings:
        """Beanie document settings, used only for index definitions currently."""
        indexes = [
            [
                ("type", pymongo.ASCENDING),
                ("timestamp", pymongo.DESCENDING),
            ],
            [
                ("user_id", pymongo.ASCENDING),
                ("timestamp", pymongo.DESCENDING),
            ],
            [
                ("source_url", pymongo.ASCENDING),
                ("timestamp", pymongo.DESCENDING),
            ],
        ]
