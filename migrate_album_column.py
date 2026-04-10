"""Migra la columna diary_entry_id de INTEGER a VARCHAR(255) para soportar UUIDs."""
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text(
        "ALTER TABLE agent_album_entries ALTER COLUMN diary_entry_id TYPE VARCHAR(255) USING diary_entry_id::VARCHAR"
    ))
    conn.commit()
    print("OK - Columna diary_entry_id migrada a VARCHAR(255)")
