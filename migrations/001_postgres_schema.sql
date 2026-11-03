-- ChronoNote PostgreSQL 16 Schema Migration (001_postgres_schema.sql)

CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    slug VARCHAR(140) NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    color VARCHAR(20) NOT NULL DEFAULT '#6366f1',
    icon VARCHAR(40) NOT NULL DEFAULT 'folder',
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
    sidebar_order INTEGER NOT NULL DEFAULT 0,
    start_date DATE NULL,
    target_date DATE NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_projects_slug ON projects (slug);
CREATE INDEX IF NOT EXISTS ix_projects_status ON projects (status);
CREATE INDEX IF NOT EXISTS ix_projects_is_pinned ON projects (is_pinned);
CREATE INDEX IF NOT EXISTS ix_projects_sidebar_order ON projects (sidebar_order);

CREATE TABLE IF NOT EXISTS notes (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NULL REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    slug VARCHAR(220) NOT NULL UNIQUE,
    content_md TEXT NOT NULL DEFAULT '',
    frontmatter_json TEXT NOT NULL DEFAULT '{}',
    tags_json TEXT NOT NULL DEFAULT '[]',
    is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
    is_daily_note BOOLEAN NOT NULL DEFAULT FALSE,
    note_date DATE NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_notes_project_id ON notes (project_id);
CREATE INDEX IF NOT EXISTS ix_notes_slug ON notes (slug);
CREATE INDEX IF NOT EXISTS ix_notes_is_daily_note ON notes (is_daily_note);
CREATE INDEX IF NOT EXISTS ix_notes_note_date ON notes (note_date);

CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source_note_id INTEGER NULL REFERENCES notes(id) ON DELETE SET NULL,
    title VARCHAR(240) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status VARCHAR(30) NOT NULL DEFAULT 'todo',
    priority VARCHAR(20) NOT NULL DEFAULT 'medium',
    color VARCHAR(20) NOT NULL DEFAULT '#0891b2',
    start_date DATE NULL,
    due_date DATE NULL,
    is_milestone BOOLEAN NOT NULL DEFAULT FALSE,
    depends_on_id INTEGER NULL REFERENCES tasks(id) ON DELETE SET NULL,
    progress INTEGER NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_tasks_project_id ON tasks (project_id);
CREATE INDEX IF NOT EXISTS ix_tasks_source_note_id ON tasks (source_note_id);
CREATE INDEX IF NOT EXISTS ix_tasks_status ON tasks (status);
CREATE INDEX IF NOT EXISTS ix_tasks_start_date ON tasks (start_date);
CREATE INDEX IF NOT EXISTS ix_tasks_due_date ON tasks (due_date);

CREATE TABLE IF NOT EXISTS note_links (
    id SERIAL PRIMARY KEY,
    source_note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    target_note_id INTEGER NULL REFERENCES notes(id) ON DELETE SET NULL,
    target_slug VARCHAR(220) NOT NULL,
    display_text VARCHAR(220) NOT NULL,
    context_snippet VARCHAR(300) NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS ix_note_links_source_note_id ON note_links (source_note_id);
CREATE INDEX IF NOT EXISTS ix_note_links_target_note_id ON note_links (target_note_id);
CREATE INDEX IF NOT EXISTS ix_note_links_target_slug ON note_links (target_slug);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(200) NOT NULL UNIQUE,
    name VARCHAR(160) NOT NULL DEFAULT '',
    picture VARCHAR(500) NOT NULL DEFAULT '',
    google_sub VARCHAR(120) UNIQUE,
    password_hash VARCHAR(128) NULL,
    salt VARCHAR(64) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);
CREATE INDEX IF NOT EXISTS ix_users_google_sub ON users (google_sub);

CREATE TABLE IF NOT EXISTS journal_secrets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    password_hash VARCHAR(128) NOT NULL,
    salt VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_journal_secrets_user_id ON journal_secrets (user_id);

CREATE TABLE IF NOT EXISTS habits (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NULL REFERENCES users(id) ON DELETE CASCADE,
    slug VARCHAR(100) NOT NULL,
    name VARCHAR(140) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    icon VARCHAR(40) NOT NULL DEFAULT 'check',
    color VARCHAR(20) NOT NULL DEFAULT '#10b981',
    target_days_per_week INTEGER NOT NULL DEFAULT 7,
    archived BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_habits_slug ON habits (slug);
CREATE INDEX IF NOT EXISTS ix_habits_user_id ON habits (user_id);
CREATE INDEX IF NOT EXISTS ix_habits_archived ON habits (archived);

CREATE TABLE IF NOT EXISTS habit_logs (
    id SERIAL PRIMARY KEY,
    habit_id INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
    user_id INTEGER NULL REFERENCES users(id) ON DELETE CASCADE,
    note_id INTEGER NULL REFERENCES notes(id) ON DELETE SET NULL,
    log_date DATE NOT NULL,
    completed BOOLEAN NOT NULL DEFAULT TRUE,
    value VARCHAR(60) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_habit_logs_habit_id ON habit_logs (habit_id);
CREATE INDEX IF NOT EXISTS ix_habit_logs_user_id ON habit_logs (user_id);
CREATE INDEX IF NOT EXISTS ix_habit_logs_log_date ON habit_logs (log_date);
CREATE INDEX IF NOT EXISTS ix_habit_logs_completed ON habit_logs (completed);

CREATE TABLE IF NOT EXISTS journal_templates (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    description VARCHAR(240) NOT NULL DEFAULT '',
    content_md TEXT NOT NULL DEFAULT '',
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_journal_templates_user_id ON journal_templates (user_id);
CREATE INDEX IF NOT EXISTS ix_journal_templates_is_default ON journal_templates (is_default);

CREATE TABLE IF NOT EXISTS study_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id INTEGER NULL REFERENCES projects(id) ON DELETE CASCADE,
    task_id INTEGER NULL REFERENCES tasks(id) ON DELETE SET NULL,
    note_id INTEGER NULL REFERENCES notes(id) ON DELETE SET NULL,
    duration_minutes INTEGER NOT NULL DEFAULT 25,
    session_type VARCHAR(30) NOT NULL DEFAULT 'focus',
    intention VARCHAR(255) NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    session_date DATE NOT NULL,
    completed BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_study_sessions_user_id ON study_sessions (user_id);
CREATE INDEX IF NOT EXISTS ix_study_sessions_project_id ON study_sessions (project_id);
CREATE INDEX IF NOT EXISTS ix_study_sessions_task_id ON study_sessions (task_id);
CREATE INDEX IF NOT EXISTS ix_study_sessions_session_date ON study_sessions (session_date);
CREATE INDEX IF NOT EXISTS ix_study_sessions_completed ON study_sessions (completed);

CREATE TABLE IF NOT EXISTS stickers (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    category VARCHAR(60) NOT NULL DEFAULT 'custom',
    image_url TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_stickers_user_id ON stickers (user_id);
CREATE INDEX IF NOT EXISTS ix_stickers_category ON stickers (category);

CREATE TABLE IF NOT EXISTS sticker_placements (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NULL REFERENCES users(id) ON DELETE CASCADE,
    sticker_id INTEGER NULL REFERENCES stickers(id) ON DELETE SET NULL,
    sticker_name VARCHAR(120) NOT NULL DEFAULT 'Sticker',
    image_url TEXT NOT NULL,
    target_type VARCHAR(40) NOT NULL,
    target_key VARCHAR(120) NOT NULL,
    pos_x INTEGER NOT NULL DEFAULT 50,
    pos_y INTEGER NOT NULL DEFAULT 50,
    rotation_deg INTEGER NOT NULL DEFAULT 0,
    scale INTEGER NOT NULL DEFAULT 100,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_sticker_placements_user_id ON sticker_placements (user_id);
CREATE INDEX IF NOT EXISTS ix_sticker_placements_sticker_id ON sticker_placements (sticker_id);
CREATE INDEX IF NOT EXISTS ix_sticker_placements_target_type ON sticker_placements (target_type);
CREATE INDEX IF NOT EXISTS ix_sticker_placements_target_key ON sticker_placements (target_key);


