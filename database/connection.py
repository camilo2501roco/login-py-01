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
    print(f"Conectado a MongoDB: {db_name}")


async def close_db():
    global _client
    if _client:
        _client.close()
        print("Conexion MongoDB cerrada")


def get_database():
    if _database is None:
        raise RuntimeError("Database not initialized. Call connect_db() first.")
    return _database
