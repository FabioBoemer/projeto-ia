-- Metadados de cargas Medallion (opcional; o script também cria via CREATE IF NOT EXISTS)
CREATE TABLE IF NOT EXISTS swiss_pipeline_runs (
    id BIGSERIAL PRIMARY KEY,
    layer VARCHAR(16) NOT NULL,
    version VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_swiss_runs_layer_version ON swiss_pipeline_runs (layer, version);
CREATE INDEX IF NOT EXISTS idx_swiss_runs_created ON swiss_pipeline_runs (created_at DESC);
