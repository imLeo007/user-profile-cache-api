from fastapi import APIRouter, HTTPException, Depends

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from app.models.user import Profile

from fastapi.encoders import jsonable_encoder

import json

from typing import Annotated

from app.core.database import get_db

from app.core.redis_client import redis_client

from app.schemas.profile_model import UserModel, UserResponse, UserEdit

# Router

router = APIRouter(prefix="/users", tags=["Users"])

# DB dependency

SessionDB = Annotated[AsyncSession, Depends(get_db)]

# Time limit for cache

CACHE_TTL = 240

# Add a user

@router.post("/users", response_model=UserResponse)
async def add_user(data:UserModel, db: SessionDB) -> UserResponse:
    result = await db.execute(select(Profile).where(Profile.username == data.username))

    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    user = Profile(
        name=data.name,
        username=data.username,
        bio=data.bio,
        is_active=data.is_active
    )

    db.add(user)

    await db.commit()

    await db.refresh(user)

    return user

# Get all users

@router.get("/users", response_model=list[UserResponse])
async def get_all(db: SessionDB) -> list[UserResponse]:
    result = await db.execute(select(Profile))

    users = result.scalars().all()

    if not users:
        raise HTTPException(status_code=404, detail="No users were found at this moment")
    
    return users

# Get user, if available in cache get from redis

@router.get("/users/{username}", response_model=UserResponse)
async def get_one(username: str, db: SessionDB) -> UserResponse:
    cache_key = f"username:{username.lower()}"

    cached_user = await redis_client.get(cache_key)

    if cached_user:
        print("CACHE HIT")
        return json.loads(cached_user)
    
    result = await db.execute(select(Profile).where(Profile.username == username))

    user = result.scalar_one_or_none()

    print("CACHE MISS")

    if user is None:
        raise HTTPException(status_code=404, detail="User was not found")
    
    user_data = jsonable_encoder(UserResponse.model_validate(user))

    await redis_client.setex(
        cache_key,
        CACHE_TTL,
        json.dumps(user_data)
    )

    return user

# Edit user: name and bio, is_active

@router.patch("/users/{username}/profile", response_model=UserResponse)
async def edit_user(username: str, data: UserEdit, db: SessionDB) -> UserResponse:
    cache_key = f"user:{username.lower()}"

    result = await db.execute(select(Profile).where(Profile.username == username))

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="User was not found")

    updated_data = data.model_dump(exclude_unset=True)

    for field, value in updated_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    await redis_client.delete(cache_key)

    return user

# Delete user from db, cache as well

@router.delete("/users/{username}", response_model=UserResponse)
async def delete_user(username: str, db: SessionDB) -> UserResponse:
    cache_key = f"username:{username.lower()}"

    result = await db.execute(select(Profile).where(Profile.username == username))

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="User was not found")
    
    db.delete(user)

    await db.commit()

    await redis_client.delete(cache_key)

    return user

# Delete user cache

@router.delete("/users/{username}/cache")
async def delete_cache(username: str) -> dict:
    cache_key = f"username:{username}"

    await redis_client.delete(cache_key)

    return {
        "message": "user cache was deleted",
        "username": username
    }