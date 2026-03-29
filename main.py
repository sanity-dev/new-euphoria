"""
Sanity Agent – Entry Point
Inicializa la base de datos y ejecuta el servidor FastAPI.
"""

import uvicorn
from database import init_db


def main():
    print("🧠 Sanity Agent – EuphorIA v1.0")
    print("=" * 50)

    # Inicializar base de datos (crear tablas si no existen)
    print("📦 Inicializando base de datos Azure SQL...")
    try:
        init_db()
    except Exception as e:
        print(f"⚠️ No se pudo conectar a Azure SQL: {e}")
        print("   El agente funcionará sin persistencia hasta que se resuelva.")

    # Iniciar servidor FastAPI
    print("🚀 Iniciando servidor en http://localhost:8000")
    print("   Documentación: http://localhost:8000/docs")
    print("=" * 50)

    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
