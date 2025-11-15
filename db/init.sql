CREATE TABLE IF NOT EXISTS weather_logs (
id BIGSERIAL PRIMARY KEY,
station_id TEXT NOT NULL,
ts TIMESTAMPTZ NOT NULL,
temperature NUMERIC,
humidity NUMERIC,
wind_speed NUMERIC,
status TEXT NOT NULL DEFAULT 'ok',
raw JSONB,
created_at TIMESTAMPTZ DEFAULT now()
);


CREATE TABLE IF NOT EXISTS weather_deadletters (
id BIGSERIAL PRIMARY KEY,
raw JSONB,
reason TEXT,
created_at TIMESTAMPTZ DEFAULT now()
);