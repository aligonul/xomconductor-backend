"""In-memory store for email drafts."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Draft:
    id: str
    case_number: str
    customer_name: str
    subject: str
    body: str
    tone: str
    user_id: str
    channel_id: str
    message_ts: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def full_text(self) -> str:
        return f"Subject: {self.subject}\n\n{self.body}"


class DraftStore:
    """Simple in-memory draft storage."""

    def __init__(self):
        self._drafts: dict[str, Draft] = {}

    def create(
        self,
        case_number: str,
        customer_name: str,
        subject: str,
        body: str,
        tone: str,
        user_id: str,
        channel_id: str,
    ) -> Draft:
        draft_id = str(uuid.uuid4())[:8]
        draft = Draft(
            id=draft_id,
            case_number=case_number,
            customer_name=customer_name,
            subject=subject,
            body=body,
            tone=tone,
            user_id=user_id,
            channel_id=channel_id,
        )
        self._drafts[draft_id] = draft
        return draft

    def get(self, draft_id: str) -> Optional[Draft]:
        return self._drafts.get(draft_id)

    def update(self, draft_id: str, subject: str, body: str) -> Optional[Draft]:
        draft = self._drafts.get(draft_id)
        if draft:
            draft.subject = subject
            draft.body = body
        return draft

    def delete(self, draft_id: str) -> bool:
        if draft_id in self._drafts:
            del self._drafts[draft_id]
            return True
        return False

    def set_message_ts(self, draft_id: str, message_ts: str) -> None:
        draft = self._drafts.get(draft_id)
        if draft:
            draft.message_ts = message_ts


store = DraftStore()
