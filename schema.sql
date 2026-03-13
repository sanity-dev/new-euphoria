-- ═══════════════════════════════════════════════════════════
-- Sanity Agent – Azure SQL Schema (Database: Euphoria)
-- Server: sanityia.database.windows.net
-- ═══════════════════════════════════════════════════════════

-- Tabla de conversaciones (sesiones de chat)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'agent_conversations')
CREATE TABLE agent_conversations (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    session_id      NVARCHAR(255)   NOT NULL,
    user_id         INT             NULL,
    created_at      DATETIME2       NOT NULL DEFAULT GETDATE(),
    updated_at      DATETIME2       NOT NULL DEFAULT GETDATE(),
    is_active       BIT             NOT NULL DEFAULT 1
);

-- Tabla de mensajes del chat
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'agent_messages')
CREATE TABLE agent_messages (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    conversation_id INT             NOT NULL,
    role            NVARCHAR(20)    NOT NULL,  -- 'usuario' | 'asistente'
    content         NVARCHAR(MAX)   NOT NULL,
    emotions        NVARCHAR(500)   NULL,      -- JSON array de emociones detectadas
    timestamp       DATETIME2       NOT NULL DEFAULT GETDATE(),
    FOREIGN KEY (conversation_id) REFERENCES agent_conversations(id) ON DELETE CASCADE
);

-- Tabla de recordatorios de hábitos saludables
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'agent_reminders')
CREATE TABLE agent_reminders (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    user_id         INT             NOT NULL,
    session_id      NVARCHAR(255)   NOT NULL,
    habit_name      NVARCHAR(200)   NOT NULL,
    description     NVARCHAR(500)   NULL,
    frequency       NVARCHAR(50)    NOT NULL DEFAULT 'diario',  -- diario, semanal, etc.
    reminder_time   NVARCHAR(10)    NULL,     -- HH:MM formato
    is_active       BIT             NOT NULL DEFAULT 1,
    created_at      DATETIME2       NOT NULL DEFAULT GETDATE()
);

-- Tabla de entradas del álbum guardadas desde el chat
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'agent_album_entries')
CREATE TABLE agent_album_entries (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    user_id         INT             NOT NULL,
    session_id      NVARCHAR(255)   NOT NULL,
    content         NVARCHAR(MAX)   NULL,
    image_url       NVARCHAR(500)   NULL,
    entry_type      NVARCHAR(50)    NOT NULL DEFAULT 'texto',  -- texto, foto, momento
    created_at      DATETIME2       NOT NULL DEFAULT GETDATE()
);

-- Índices
CREATE INDEX IX_agent_conversations_session ON agent_conversations(session_id);
CREATE INDEX IX_agent_messages_conversation ON agent_messages(conversation_id);
CREATE INDEX IX_agent_reminders_user ON agent_reminders(user_id);
CREATE INDEX IX_agent_album_user ON agent_album_entries(user_id);
