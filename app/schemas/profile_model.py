from pydantic import BaseModel, ConfigDict

from datetime import datetime

class UserModel(BaseModel):
    name: str
    username: str
    bio: str | None = None
    is_active: bool = True

class UserEdit(BaseModel):
    name: str | None = None
    bio: str | None = None
    is_active: bool | None = None

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    username: str
    bio: str | None
    is_active: bool

    created_at: datetime
    updated_at: datetime