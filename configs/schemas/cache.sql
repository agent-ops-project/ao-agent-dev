CREATE TABLE IF NOT EXISTS prompt_cache (
    key TEXT PRIMARY KEY,
    prompt TEXT NOT NULL,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS object_cache (
    key TEXT PRIMARY KEY,
    value BLOB NOT NULL
)