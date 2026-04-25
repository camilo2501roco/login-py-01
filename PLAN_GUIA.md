# Guia de Implementacion: API de Registro con FastAPI + MongoDB Atlas + Gmail SMTP

## Contexto

Crear una API REST en Python para registro de usuarios (email + password). Al registrarse exitosamente, se envia un correo de confirmacion via Gmail SMTP. Base de datos en MongoDB Atlas. Documentacion automatica con Swagger UI (integrado en FastAPI). Estructura de carpetas: controllers, database, helpers, middlewares, models, routes.

**Decisiones:** Framework FastAPI, envio de correo via Gmail SMTP.

---

## Estructura de Carpetas

```
login de python/
|-- main.py                        # Entry point FastAPI
|-- requirements.txt               # Dependencias
|-- .env                           # Variables de entorno (gitignored)
|-- .gitignore
|
|-- database/
|   |-- __init__.py
|   |-- connection.py              # Motor async MongoDB client
|
|-- models/
|   |-- __init__.py
|   |-- user.py                    # Schemas Pydantic (UserRegister, UserResponse, UserInDB)
|
|-- controllers/
|   |-- __init__.py
|   |-- user_controller.py         # Logica de negocio: registro
|
|-- routes/
|   |-- __init__.py
|   |-- user_routes.py             # APIRouter POST /register
|
|-- helpers/
|   |-- __init__.py
|   |-- email_helper.py            # Gmail SMTP envio de correo
|   |-- password_helper.py         # bcrypt hash/verify
|
|-- middlewares/
|   |-- __init__.py
|
|-- public/
|   |-- .gitkeep
|
|-- cron/
|   |-- .gitkeep
```

### Mapeo MVT (Model - View - Template)

| MVT             | Carpeta        | Responsabilidad                                         |
|-----------------|----------------|---------------------------------------------------------|
| Model           | `models/`      | Schemas Pydantic + estructura documento MongoDB         |
| View/Controller | `controllers/` | Logica de negocio: hash, validacion, insercion, email   |
| Template        | `helpers/`     | Plantillas HTML de correo, utilidades                   |
| Routes          | `routes/`      | FastAPI APIRouter (definicion de endpoints)             |
| Database        | `database/`    | Motor async client, ciclo de vida conexion              |
| Middlewares     | `middlewares/` | CORS, logging, manejo de errores                        |

---

## Dependencias (`requirements.txt`)

```
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
motor>=3.6.0
pymongo>=4.10.0
bcrypt>=4.2.0
pydantic[email]>=2.10.0
python-dotenv>=1.1.0
python-multipart>=0.0.18
```

### Por que estas dependencias

- **fastapi** - Framework web async con Swagger automatico
- **uvicorn[standard]** - Servidor ASGI para correr FastAPI
- **motor** - Driver async de MongoDB (envuelve pymongo)
- **pymongo** - Requerido por motor como base
- **bcrypt** - Hash de passwords (implementacion Rust, rapida y segura)
- **pydantic[email]** - Validacion automatica de formato email con `EmailStr`
- **python-dotenv** - Carga variables de `.env` al entorno
- **python-multipart** - Requerido por FastAPI para parsing de form data

---

## Variables de Entorno (`.env`)

```env
# MongoDB Atlas
MONGODB_URI=mongodb+srv://<usuario>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=login_app

# Gmail SMTP
GMAIL_USER=tu_correo@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
GMAIL_FROM_NAME=Login App

# App
APP_NAME=Login Python API
APP_URL=http://localhost:8000
```

### Notas sobre `.env`

- `MONGODB_URI` debe usar el esquema `mongodb+srv://` para Atlas
- `GMAIL_APP_PASSWORD` debe ser un App Password de 16 caracteres (NO tu password real de Gmail)
- Google bloquea logins SMTP con password normal

---

## Fases de Implementacion

### Fase 1: Setup del Proyecto

**Archivos a crear:**

1. **`requirements.txt`** - Lista de dependencias arriba
2. **`.env`** - Variables de entorno con placeholders
3. **`.gitignore`** - Ignorar `__pycache__/`, `.env`, `venv/`
4. **`main.py`** - Skeleton de FastAPI:

```python
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import dotenv

dotenv.load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: conectar base de datos
    from database.connection import connect_db, close_db
    await connect_db()
    yield
    # Shutdown: cerrar conexion
    await close_db()

app = FastAPI(
    title=os.getenv("APP_NAME", "Login Python API"),
    description="API de registro de usuarios con MongoDB Atlas",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Se activara en Fase 4:
# from routes.user_routes import router as user_router
# app.include_router(user_router, prefix="/api/users", tags=["Users"])
```

**Verificacion:** `uvicorn main:app --reload` arranca, `http://localhost:8000/docs` muestra Swagger UI

---

### Fase 2: Conexion MongoDB Atlas

**Archivo: `database/connection.py`**

```python
import os
from motor.motor_asyncio import AsyncIOMotorClient

_client = None
_database = None

async def connect_db():
    global _client, _database
    uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DATABASE", "login_app")
    _client = AsyncIOMotorClient(uri)
    _database = _client[db_name]
    # Verificar conexion
    await _client.admin.command("ping")
    # Crear indice unico en email
    await _database["users"].create_index("email", unique=True)

async def close_db():
    global _client
    if _client:
        _client.close()

def get_database():
    if _database is None:
        raise RuntimeError("Database not initialized")
    return _database
```

**Verificacion:** App arranca sin errores, ping exitoso a Atlas

**Importante:** En MongoDB Atlas, agregar tu IP o `0.0.0.0/0` en Network Access

---

### Fase 3: Modelo de Usuario

**Archivo: `models/user.py`**

```python
import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegister(BaseModel):
    """Schema de entrada para registro."""
    email: EmailStr = Field(..., example="usuario@ejemplo.com")
    password: str = Field(..., example="MiPassword123")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password debe tener al menos 8 caracteres")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password debe tener al menos una mayuscula")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password debe tener al menos una minuscula")
        if not re.search(r"\d", v):
            raise ValueError("Password debe tener al menos un numero")
        return v


class UserResponse(BaseModel):
    """Schema de respuesta (nunca expone password)."""
    id: str = Field(..., example="662a1b2c3d4e5f6a7b8c9d0e")
    email: EmailStr = Field(..., example="usuario@ejemplo.com")
    is_confirmed: bool = Field(False, example=False)
    created_at: datetime = Field(..., example="2026-04-25T12:00:00Z")

    model_config = {"from_attributes": True}


class UserInDB(BaseModel):
    """Representacion interna del documento MongoDB."""
    email: EmailStr
    hashed_password: str
    is_confirmed: bool = False
    confirmation_token: Optional[str] = None
    created_at: datetime = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.created_at is None:
            self.created_at = datetime.utcnow()
```

**Verificacion:** Los schemas aparecen en Swagger UI, validacion rechaza passwords debiles

---

### Fase 4: Endpoint de Registro

**Archivo: `helpers/password_helper.py`**

```python
import bcrypt

def hash_password(plain_password: str) -> str:
    """Hashea un password con bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica un password contra su hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )
```

**Archivo: `controllers/user_controller.py`**

```python
import uuid
from datetime import datetime
from fastapi import HTTPException, BackgroundTasks
from models.user import UserRegister, UserResponse
from helpers.password_helper import hash_password
from database.connection import get_database

async def register_user(user_data: UserRegister, background_tasks: BackgroundTasks) -> UserResponse:
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
        "created_at": datetime.utcnow(),
    }

    # 5. Insertar en MongoDB
    result = await users.insert_one(user_doc)

    # 6. Enviar correo en background (se activa en Fase 5)
    # from helpers.email_helper import send_confirmation_email
    # background_tasks.add_task(send_confirmation_email, user_data.email, token)

    # 7. Retornar respuesta (sin exponer password ni token)
    return UserResponse(
        id=str(result.inserted_id),
        email=user_data.email,
        is_confirmed=False,
        created_at=user_doc["created_at"],
    )
```

**Archivo: `routes/user_routes.py`**

```python
from fastapi import APIRouter, BackgroundTasks
from models.user import UserRegister, UserResponse
from controllers.user_controller import register_user

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=201)
async def register(user_data: UserRegister, background_tasks: BackgroundTasks):
    """Registrar un nuevo usuario con email y password."""
    return await register_user(user_data, background_tasks)
```

**En `main.py` activar el router:**

```python
from routes.user_routes import router as user_router
app.include_router(user_router, prefix="/api/users", tags=["Users"])
```

**Verificacion:** POST `/api/users/register` funciona en Swagger, usuario aparece en Atlas, error 400 si email ya existe

---

### Fase 5: Email de Confirmacion

**Archivo: `helpers/email_helper.py`**

```python
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_confirmation_email(to_email: str, token: str):
    """Envia correo de confirmacion via Gmail SMTP."""
    gmail_user = os.getenv("GMAIL_USER")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")
    from_name = os.getenv("GMAIL_FROM_NAME", "Login App")
    app_url = os.getenv("APP_URL", "http://localhost:8000")

    confirmation_link = f"{app_url}/api/users/confirm/{token}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Confirma tu correo electronico"
    msg["From"] = f"{from_name} <{gmail_user}>"
    msg["To"] = to_email

    html = _build_confirmation_html(confirmation_link)
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, to_email, msg.as_string())
    except Exception as e:
        print(f"Error enviando correo de confirmacion: {e}")


def _build_confirmation_html(confirmation_link: str) -> str:
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: white;
                    padding: 30px; border-radius: 8px;">
            <h2 style="color: #333;">Bienvenido!</h2>
            <p style="color: #555;">
                Gracias por registrarte. Confirma tu correo haciendo clic en el boton:
            </p>
            <a href="{confirmation_link}"
               style="display: inline-block; padding: 12px 24px;
                      background-color: #4CAF50; color: white;
                      text-decoration: none; border-radius: 4px; margin: 10px 0;">
                Confirmar Email
            </a>
            <p style="color: #999; font-size: 12px;">
                Si no creaste esta cuenta, ignora este correo.
            </p>
        </div>
    </body>
    </html>
    """
```

**En `controllers/user_controller.py` descomentar las lineas del email:**

```python
from helpers.email_helper import send_confirmation_email
# ...
background_tasks.add_task(send_confirmation_email, user_data.email, token)
```

**Verificacion:** Registrarse y recibir el correo HTML en el inbox

### Configurar Gmail App Password

1. Ir a Google Account > Seguridad > Verificacion en 2 pasos (activar si no esta)
2. Buscar "Contrasenas de aplicacion" en la configuracion de la cuenta
3. Generar nueva App Password para "Correo" en "Computadora Windows"
4. Copiar el password de 16 caracteres al `.env`

---

### Fase 6: Pruebas Finales en Swagger

FastAPI genera documentacion automatica en:
- **Swagger UI:** `http://localhost:8000/docs` (interactivo, prueba endpoints)
- **ReDoc:** `http://localhost:8000/redoc` (solo lectura, documentacion limpia)

**Casos de prueba:**

| Caso                           | Input                                     | Esperado                    |
|--------------------------------|-------------------------------------------|-----------------------------|
| Registro exitoso               | email valido, password valido             | 201, UserResponse, email enviado |
| Email duplicado                | email ya registrado                       | 400 "Email ya registrado"   |
| Password muy corto             | "abc"                                     | 422 con detalle de validacion |
| Password sin mayuscula         | "password123"                             | 422                         |
| Password sin numero            | "Password"                                | 422                         |
| Email formato invalido         | "no-es-email"                             | 422                         |

---

## Como Ejecutar

```bash
# Navegar al proyecto
cd "C:\Users\USUARIO\Desktop\login de python"

# Crear entorno virtual
python -m venv venv
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar .env con tus credenciales reales

# Ejecutar servidor
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Abrir en navegador: http://localhost:8000/docs
```

---

## Posibles Problemas y Soluciones

| Problema                                | Solucion                                                      |
|-----------------------------------------|---------------------------------------------------------------|
| Timeout conexion Atlas                  | Agregar IP en Network Access de Atlas (o `0.0.0.0/0` para dev) |
| Gmail rechaza login SMTP                | Usar App Password (no password real), tener 2FA activado      |
| bcrypt falla al instalar en Windows     | Usar `pip install bcrypt` (wheels pre-built disponibles)       |
| Error "Database not initialized"        | Verificar que el lifespan esta conectado correctamente         |
| Email duplicado en requests concurrentes| El indice unico de MongoDB atrapa el race condition           |
