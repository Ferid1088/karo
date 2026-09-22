-- Zeitbasierte Ziele. Die Tabellen des frueheren Wochen-Piloten bleiben erhalten.
CREATE TABLE IF NOT EXISTS plan_goal (
 id INTEGER PRIMARY KEY,
 child_key TEXT NOT NULL DEFAULT 'installation' CHECK(child_key='installation'),
 statement TEXT NOT NULL CHECK(length(statement) BETWEEN 1 AND 180),
 start_date TEXT NOT NULL CHECK(date(start_date)=start_date),
 end_date TEXT NOT NULL CHECK(date(end_date)=end_date AND end_date>=start_date),
 planned_minutes INTEGER NOT NULL CHECK(planned_minutes BETWEEN 1 AND 60),
 weekdays TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','paused','completed','archived')),
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 completed_at TEXT,
 archived_at TEXT
);

CREATE TABLE IF NOT EXISTS plan_session (
 id INTEGER PRIMARY KEY,
 goal_id INTEGER NOT NULL REFERENCES plan_goal(id) ON DELETE CASCADE,
 scheduled_date TEXT NOT NULL CHECK(date(scheduled_date)=scheduled_date),
 planned_minutes INTEGER NOT NULL CHECK(planned_minutes BETWEEN 1 AND 60),
 status TEXT NOT NULL DEFAULT 'planned' CHECK(status IN ('planned','completed','missed','made_up','cancelled')),
 created_at TEXT NOT NULL,
 UNIQUE(goal_id, scheduled_date)
);

CREATE TABLE IF NOT EXISTS plan_completion (
 id INTEGER PRIMARY KEY,
 planned_session_id INTEGER NOT NULL UNIQUE REFERENCES plan_session(id) ON DELETE CASCADE,
 actual_minutes INTEGER NOT NULL CHECK(actual_minutes BETWEEN 0 AND 60),
 focus_percent INTEGER NOT NULL CHECK(focus_percent BETWEEN 0 AND 100),
 completed_at TEXT NOT NULL,
 is_makeup INTEGER NOT NULL DEFAULT 0 CHECK(is_makeup IN (0,1))
);

CREATE INDEX IF NOT EXISTS plan_session_date ON plan_session(scheduled_date, status);
CREATE INDEX IF NOT EXISTS plan_session_goal ON plan_session(goal_id, scheduled_date);
