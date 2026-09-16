-- One learner per installation, matching config.learner_* and the session roles.
CREATE TABLE IF NOT EXISTS woche_plan (
 id INTEGER PRIMARY KEY,
 child_key TEXT NOT NULL DEFAULT 'installation' CHECK(child_key='installation'),
 week TEXT NOT NULL CHECK(date(week) IS NOT NULL AND date(week)=week AND strftime('%w',week)='1'),
 goal TEXT NOT NULL DEFAULT '' CHECK(length(goal)<=160),
 step TEXT NOT NULL DEFAULT '' CHECK(length(step)<=240),
 routine TEXT NOT NULL DEFAULT '' CHECK(length(routine)<=160),
 days TEXT NOT NULL DEFAULT '',
 promise TEXT NOT NULL DEFAULT '' CHECK(length(promise)<=240),
 promise_day TEXT NOT NULL DEFAULT '', promise_time TEXT NOT NULL DEFAULT '',
 discussed_at TEXT NOT NULL,
 child_status TEXT NOT NULL DEFAULT 'offen' CHECK(child_status IN ('offen','passt','aendern')),
 paused INTEGER NOT NULL DEFAULT 0 CHECK(paused IN (0,1)),
 achieved INTEGER NOT NULL DEFAULT 0 CHECK(achieved IN (0,1)),
 feeling TEXT NOT NULL DEFAULT '' CHECK(feeling IN ('','gut','mittel','schwierig')),
 wish TEXT NOT NULL DEFAULT '' CHECK(wish IN ('','lassen','leichter','anders')),
 version INTEGER NOT NULL DEFAULT 1, revision INTEGER NOT NULL DEFAULT 1,
 UNIQUE(child_key, week), CHECK(goal!='' OR routine!='' OR promise!=''),
 CHECK(goal!='' OR step=''), CHECK(routine='' OR days!='')
);
CREATE TABLE IF NOT EXISTS woche_feedback (
 plan_id INTEGER NOT NULL REFERENCES woche_plan(id) ON DELETE CASCADE,
 revision INTEGER NOT NULL, activity TEXT NOT NULL CHECK(activity IN ('goal','routine')),
 day TEXT NOT NULL CHECK(date(day) IS NOT NULL AND date(day)=day),
 PRIMARY KEY(plan_id,revision,activity,day)
);
CREATE TABLE IF NOT EXISTS woche_help (
 id INTEGER PRIMARY KEY, plan_id INTEGER NOT NULL REFERENCES woche_plan(id) ON DELETE CASCADE,
 revision INTEGER NOT NULL, activity TEXT NOT NULL CHECK(activity IN ('goal','routine')),
 activity_text TEXT NOT NULL CHECK(length(activity_text)<=240),
 kind TEXT NOT NULL CHECK(kind IN ('erklaeren','zusammen','sprechen')),
 message TEXT NOT NULL DEFAULT '' CHECK(length(message)<=240),
 status TEXT NOT NULL DEFAULT 'angefragt' CHECK(status IN ('angefragt','zugesagt','erledigt','zurueckgenommen')),
 reply TEXT NOT NULL DEFAULT '' CHECK(length(reply)<=240),
 appointment TEXT NOT NULL DEFAULT '', version INTEGER NOT NULL DEFAULT 1
);
CREATE UNIQUE INDEX IF NOT EXISTS woche_one_open_help
 ON woche_help(plan_id,revision,activity) WHERE status IN ('angefragt','zugesagt');
CREATE TABLE IF NOT EXISTS woche_migration (
 version INTEGER PRIMARY KEY, legacy_preserved INTEGER NOT NULL CHECK(legacy_preserved IN (0,1))
);
