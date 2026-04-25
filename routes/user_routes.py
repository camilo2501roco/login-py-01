from fastapi import APIRouter, BackgroundTasks

from controllers.user_controller import register_user
from models.user import UserRegister, UserResponse

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(user_data: UserRegister, background_tasks: BackgroundTasks):
    """Registrar un nuevo usuario con email y password."""
    return await register_user(user_data, background_tasks)
