from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class InteractiveButtonReply(BaseModel):
    id: str
    title: str

class InteractiveListReply(BaseModel):
    id: str
    title: str
    description: Optional[str] = None

class Interactive(BaseModel):
    type: str  # "button_reply" o "list_reply"
    button_reply: Optional[InteractiveButtonReply] = None
    list_reply: Optional[InteractiveListReply] = None

class Message(BaseModel):
    from_: str = Field(alias="from")      # "from" es palabra reservada
    id: str
    timestamp: str
    type: str
    text: Optional[Dict[str, Any]] = None    # para mensajes de texto
    interactive: Optional[Interactive] = None  # para mensajes interactivos

class Contact(BaseModel):
    wa_id: Optional[str] = None
    profile: Optional[Dict[str, Any]] = None

class Status(BaseModel):
    id: str
    status: str
    timestamp: str
    recipient_id: Optional[str] = None

class Value(BaseModel):
    messages: List[Message] = Field(default_factory=list)
    contacts: List[Contact] = Field(default_factory=list)
    statuses: List[Status] = Field(default_factory=list)  # Para estados de mensajes

class Change(BaseModel):
    value: Value

class WhatsAppEntry(BaseModel):
    changes: List[Change]

class WebhookPayload(BaseModel):
    entry: List[WhatsAppEntry] = Field(default_factory=list)
