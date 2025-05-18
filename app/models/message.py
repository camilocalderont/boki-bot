from pydantic import BaseModel, Field
from typing import List, Dict, Any

class Message(BaseModel):
    from_: str = Field(alias="from")      # “from” es palabra reservada
    id: str
    timestamp: str
    type: str
    text: Dict[str, Any] | None = None    # para este ejemplo sólo texto

class Contact(BaseModel):
    wa_id: str | None = None
    profile: Dict[str, Any] | None = None

class Value(BaseModel):
    messages: List[Message] = Field(default_factory=list)
    contacts: List[Contact] = Field(default_factory=list)

class Change(BaseModel):
    value: Value

class WhatsAppEntry(BaseModel):
    changes: List[Change]

class WebhookPayload(BaseModel):
    entry: List[WhatsAppEntry] = Field(default_factory=list)
