-- PostgreSQL Schema for Handwerk ML
-- GoBD-compliant database design

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable JSON extension
CREATE EXTENSION IF NOT EXISTS "json";

-- Create schema
CREATE SCHEMA IF NOT EXISTS handwerk;

-- Set search path
SET search_path TO public;

-- Create audit trail table (IMMUTABLE)
CREATE TABLE IF NOT EXISTS calculator_accountingaudit (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(100) NOT NULL,
    record_id UUID NOT NULL,
    action_type VARCHAR(20) NOT NULL CHECK (action_type IN ('INSERT', 'UPDATE', 'DELETE')),
    user_id INTEGER NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    old_values JSONB,
    new_values JSONB,

    CONSTRAINT audit_immutable_pk UNIQUE(id)
);

CREATE INDEX idx_audit_table_record ON calculator_accountingaudit(table_name, record_id);
CREATE INDEX idx_audit_timestamp ON calculator_accountingaudit(timestamp);

-- Create projects table
CREATE TABLE IF NOT EXISTS calculator_project (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    project_type VARCHAR(100) NOT NULL,
    region VARCHAR(50) NOT NULL,
    total_area_sqm DECIMAL(10, 2),
    wood_type VARCHAR(50) NOT NULL,
    complexity INTEGER NOT NULL CHECK (complexity IN (1, 2, 3)),
    final_price DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    project_date DATE NOT NULL,
    description_embedding JSONB,
    is_finalized BOOLEAN NOT NULL DEFAULT FALSE,
    finalized_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT project_pk PRIMARY KEY (id),
    CONSTRAINT final_price_positive CHECK (final_price > 0)
);

CREATE INDEX idx_project_wood_type ON calculator_project(wood_type, project_type);
CREATE INDEX idx_project_date ON calculator_project(project_date);
CREATE INDEX idx_project_finalized ON calculator_project(is_finalized);

-- Create materials table
CREATE TABLE IF NOT EXISTS calculator_material (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    category VARCHAR(100) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    datanorm_id VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT material_pk PRIMARY KEY (id)
);

CREATE INDEX idx_material_category ON calculator_material(category);
CREATE INDEX idx_material_datanorm ON calculator_material(datanorm_id);

-- Create material prices table (time-series)
CREATE TABLE IF NOT EXISTS calculator_materialprice (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    material_id UUID NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    region VARCHAR(50) NOT NULL,
    valid_from DATE NOT NULL,
    valid_to DATE,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT material_price_pk PRIMARY KEY (id),
    CONSTRAINT material_price_fk FOREIGN KEY (material_id) REFERENCES calculator_material(id) ON DELETE CASCADE,
    CONSTRAINT price_positive CHECK (price > 0)
);

CREATE INDEX idx_material_price_recorded ON calculator_materialprice(material_id, recorded_at);
CREATE INDEX idx_material_price_validity ON calculator_materialprice(valid_from, valid_to);

-- Create project_material junction table
CREATE TABLE IF NOT EXISTS calculator_projectmaterial (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL,
    material_id UUID NOT NULL,
    quantity DECIMAL(10, 2) NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    total_cost DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT project_material_pk PRIMARY KEY (id),
    CONSTRAINT project_material_project_fk FOREIGN KEY (project_id) REFERENCES calculator_project(id) ON DELETE CASCADE,
    CONSTRAINT project_material_material_fk FOREIGN KEY (material_id) REFERENCES calculator_material(id) ON DELETE RESTRICT,
    CONSTRAINT project_material_unique UNIQUE(project_id, material_id),
    CONSTRAINT quantity_positive CHECK (quantity > 0),
    CONSTRAINT unit_price_positive CHECK (unit_price > 0),
    CONSTRAINT total_cost_positive CHECK (total_cost > 0)
);

-- Create price predictions table
CREATE TABLE IF NOT EXISTS calculator_priceprediction (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    project_features JSONB NOT NULL,
    predicted_price DECIMAL(10, 2) NOT NULL,
    confidence_score FLOAT NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    similar_projects_count INTEGER NOT NULL DEFAULT 0,
    model_version VARCHAR(50) NOT NULL,
    actual_price DECIMAL(10, 2),
    was_accepted BOOLEAN,
    user_modified_price DECIMAL(10, 2),
    prediction_error FLOAT,

    CONSTRAINT prediction_pk PRIMARY KEY (id),
    CONSTRAINT predicted_price_positive CHECK (predicted_price > 0)
);

CREATE INDEX idx_prediction_timestamp ON calculator_priceprediction(timestamp);
CREATE INDEX idx_prediction_model_version ON calculator_priceprediction(model_version);

-- Create audit trigger for GoBD compliance
CREATE OR REPLACE FUNCTION log_audit_trail()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'DELETE') THEN
        INSERT INTO calculator_accountingaudit (
            id, table_name, record_id, action_type, user_id, timestamp, old_values
        ) VALUES (
            uuid_generate_v4(),
            TG_TABLE_NAME,
            OLD.id,
            'DELETE',
            COALESCE(current_setting('app.current_user_id', true)::integer, 0),
            CURRENT_TIMESTAMP,
            row_to_json(OLD)
        );
        RETURN OLD;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO calculator_accountingaudit (
            id, table_name, record_id, action_type, user_id, timestamp, old_values, new_values
        ) VALUES (
            uuid_generate_v4(),
            TG_TABLE_NAME,
            NEW.id,
            'UPDATE',
            COALESCE(current_setting('app.current_user_id', true)::integer, 0),
            CURRENT_TIMESTAMP,
            row_to_json(OLD),
            row_to_json(NEW)
        );
        RETURN NEW;
    ELSIF (TG_OP = 'INSERT') THEN
        INSERT INTO calculator_accountingaudit (
            id, table_name, record_id, action_type, user_id, timestamp, new_values
        ) VALUES (
            uuid_generate_v4(),
            TG_TABLE_NAME,
            NEW.id,
            'INSERT',
            COALESCE(current_setting('app.current_user_id', true)::integer, 0),
            CURRENT_TIMESTAMP,
            row_to_json(NEW)
        );
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Attach triggers to tables for audit logging
CREATE TRIGGER audit_project_trigger
    AFTER INSERT OR UPDATE OR DELETE ON calculator_project
    FOR EACH ROW EXECUTE FUNCTION log_audit_trail();

CREATE TRIGGER audit_material_trigger
    AFTER INSERT OR UPDATE OR DELETE ON calculator_material
    FOR EACH ROW EXECUTE FUNCTION log_audit_trail();

CREATE TRIGGER audit_project_material_trigger
    AFTER INSERT OR UPDATE OR DELETE ON calculator_projectmaterial
    FOR EACH ROW EXECUTE FUNCTION log_audit_trail();

-- Create materialized view for project statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS project_statistics AS
SELECT
    project_type,
    COUNT(*) as total_projects,
    COUNT(CASE WHEN is_finalized THEN 1 END) as finalized_projects,
    AVG(final_price) as avg_price,
    MIN(final_price) as min_price,
    MAX(final_price) as max_price,
    STDDEV(final_price) as price_stddev
FROM calculator_project
GROUP BY project_type;

CREATE INDEX idx_project_statistics ON project_statistics(project_type);

-- Create function to refresh statistics
CREATE OR REPLACE FUNCTION refresh_project_statistics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY project_statistics;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT CONNECT ON DATABASE handwerk_ml TO django;
GRANT USAGE ON SCHEMA public TO django;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO django;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO django;
