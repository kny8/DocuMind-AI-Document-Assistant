import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AuthInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    model_config = ConfigDict(from_attributes=True)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    page_count: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AskInput(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    document_ids: list[uuid.UUID] | None = None


class CompareInput(BaseModel):
    document_ids: list[uuid.UUID] = Field(min_length=2, max_length=10)
    prompt: str = Field(default="Compare the key themes, claims, and differences.", min_length=2, max_length=4000)


class SearchInput(BaseModel):
    query: str = Field(min_length=2, max_length=2000)
    document_ids: list[uuid.UUID] | None = None
    limit: int = Field(default=8, ge=1, le=30)
