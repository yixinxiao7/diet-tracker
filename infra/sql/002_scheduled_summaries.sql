-- Pre-computed daily summaries
CREATE TABLE IF NOT EXISTS daily_summaries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  total_calories NUMERIC NOT NULL DEFAULT 0,
  meal_count INT NOT NULL DEFAULT 0,
  computed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, date)
);

-- Weekly aggregate reports
CREATE TABLE IF NOT EXISTS weekly_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  week_start DATE NOT NULL,
  week_end DATE NOT NULL,
  avg_daily_calories NUMERIC,
  min_daily_calories NUMERIC,
  max_daily_calories NUMERIC,
  total_meals INT NOT NULL DEFAULT 0,
  computed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, week_start)
);

-- Anomaly tracking for calorie spikes
CREATE TABLE IF NOT EXISTS nutrition_anomalies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  daily_calories NUMERIC NOT NULL,
  rolling_avg_calories NUMERIC NOT NULL,
  deviation_percent NUMERIC NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_daily_summaries_user_date ON daily_summaries(user_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_weekly_reports_user_week ON weekly_reports(user_id, week_start DESC);
CREATE INDEX IF NOT EXISTS idx_nutrition_anomalies_user_date ON nutrition_anomalies(user_id, date DESC);
