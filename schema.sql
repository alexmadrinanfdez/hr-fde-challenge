-- Loads table
CREATE TABLE loads (
    load_id SERIAL PRIMARY KEY,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    pickup_datetime TIMESTAMPTZ NOT NULL,
    delivery_datetime TIMESTAMPTZ NOT NULL,
    equipment_type TEXT NOT NULL,
    loadboard_rate NUMERIC NOT NULL CHECK (loadboard_rate >= 0),
    notes TEXT,
    weight NUMERIC CHECK (weight IS NULL OR weight >= 0),
    commodity_type TEXT,
    num_of_pieces INTEGER CHECK (num_of_pieces IS NULL OR num_of_pieces >= 0),
    miles NUMERIC CHECK (miles IS NULL OR miles >= 0),
    dimensions TEXT,
    CHECK (delivery_datetime >= pickup_datetime)
);

-- Calls table
CREATE TABLE calls (
    call_id TEXT PRIMARY KEY,
    call_started_at TIMESTAMPTZ NOT NULL,
    call_ended_at TIMESTAMPTZ NOT NULL,
    mc_number TEXT NOT NULL,
    carrier_authorized BOOLEAN NOT NULL,
    requested_origin TEXT,
    requested_destination TEXT,
    requested_equipment TEXT,
    requested_pickup_window TEXT,
    matched_load_id INTEGER REFERENCES loads(load_id),
    agreed_rate NUMERIC CHECK (agreed_rate IS NULL OR agreed_rate >= 0),
    negotiation_turns INTEGER CHECK (negotiation_turns IS NULL OR negotiation_turns >= 0),
    final_outcome TEXT NOT NULL CHECK (
        final_outcome IN (
            'transferred_after_agreement',
            'negotiation_failed',
            'no_matching_load',
            'carrier_not_verified',
            'caller_not_interested',
            'incomplete_call'
        )
    ),
    sentiment TEXT NOT NULL CHECK (
        sentiment IN (
            'positive',
            'neutral',
            'negative'
        )
    ),
    transcript_url TEXT,
    CHECK (call_ended_at >= call_started_at)
);

-- Indexes
CREATE INDEX idx_loads_origin ON loads (LOWER(origin));
CREATE INDEX idx_loads_destination ON loads (LOWER(destination));

CREATE INDEX idx_calls_mc_number ON calls (mc_number);
CREATE INDEX idx_calls_started_at ON calls (call_started_at);