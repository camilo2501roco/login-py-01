import uuid
from datetime import datetime, timezone

from fastapi import BackgroundTasks, HTTPException

from database.connection import get_database
from helpers.password_helper import hash_password
from models.user import UserRegister, UserResponse


async def register_user(
    user_data: UserRegister, background_tasks: BackgroundTasks
) -> UserResponse:
    db = get_database()
    users = db["users"]

    # 1. Verificar email duplicado
    existing = await users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email ya registrado")

    # 2. Hashear password
    hashed_pw = hash_password(user_data.password)

    # 3. Generar token de confirmacion
    token = str(uuid.uuid4())

    # 4. Construir documento
    user_doc = {
        "email": user_data.email,
        "hashed_password": hashed_pw,
        "is_confirmed": False,
        "confirmation_token": token,
        "created_at": datetime.now(timezone.utc),
    }

    # 5. Insertar en MongoDB
    result = await users.insert_one(user_doc)

    # 6. Enviar correo en background
    from helpers.email_helper import send_confirmation_email

    background_tasks.add_task(send_confirmation_email, user_data.email, token)

    # 7. Retornar respuesta
    return UserResponse(
        id=str(result.inserted_id),
        email=user_data.email,
        is_confirmed=False,
        created_at=user_doc["created_at"],
    )
