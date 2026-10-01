"""
PostGIS compatibility helper for development environments where
the native PostGIS C extension is not installed (e.g. bare Windows without Docker).
"""

import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

COMPAT_SQL = """
DO $setup$
BEGIN
    BEGIN
        CREATE EXTENSION IF NOT EXISTS postgis;
    EXCEPTION WHEN OTHERS THEN
        -- PostGIS extension not installed in system PG share directory.
        -- Create a standalone geometry type and stubs for local testing.
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'geometry') THEN
            CREATE TYPE geometry;
            CREATE OR REPLACE FUNCTION geometry_in(cstring) RETURNS geometry LANGUAGE internal IMMUTABLE STRICT AS 'textin';
            CREATE OR REPLACE FUNCTION geometry_out(geometry) RETURNS cstring LANGUAGE internal IMMUTABLE STRICT AS 'textout';
            CREATE OR REPLACE FUNCTION geometry_typmod_in(cstring[]) RETURNS integer LANGUAGE plpgsql IMMUTABLE AS $f$ BEGIN RETURN 0; END; $f$;
            CREATE OR REPLACE FUNCTION geometry_typmod_out(integer) RETURNS cstring LANGUAGE internal IMMUTABLE STRICT AS 'varchartypmodout';
            CREATE TYPE geometry (
                INPUT = geometry_in,
                OUTPUT = geometry_out,
                TYPMOD_IN = geometry_typmod_in,
                TYPMOD_OUT = geometry_typmod_out,
                INTERNALLENGTH = VARIABLE,
                STORAGE = extended
            );
        END IF;
    END;
END $setup$;

CREATE OR REPLACE FUNCTION ST_GeomFromEWKT(text) RETURNS geometry LANGUAGE sql IMMUTABLE AS $$ SELECT $1::geometry $$;
CREATE OR REPLACE FUNCTION ST_GeomFromText(text, integer DEFAULT 4326) RETURNS geometry LANGUAGE sql IMMUTABLE AS $$ SELECT ('SRID=' || $2 || ';' || $1)::geometry $$;
CREATE OR REPLACE FUNCTION ST_SetSRID(geometry, integer) RETURNS geometry LANGUAGE sql IMMUTABLE AS $$ SELECT $1 $$;
CREATE OR REPLACE FUNCTION ST_MakePoint(double precision, double precision) RETURNS geometry LANGUAGE sql IMMUTABLE AS $$ SELECT ('SRID=4326;POINT(' || $1 || ' ' || $2 || ')')::geometry $$;
CREATE OR REPLACE FUNCTION ST_AsText(geometry) RETURNS text LANGUAGE sql IMMUTABLE AS $$ SELECT $1::text $$;
CREATE OR REPLACE FUNCTION ST_AsBinary(geometry) RETURNS bytea LANGUAGE sql IMMUTABLE AS $$ SELECT $1::text::bytea $$;
CREATE OR REPLACE FUNCTION ST_AsEWKB(geometry) RETURNS bytea LANGUAGE sql IMMUTABLE AS $$ SELECT $1::text::bytea $$;
CREATE OR REPLACE FUNCTION ST_AsEWKT(geometry) RETURNS text LANGUAGE sql IMMUTABLE AS $$ SELECT $1::text $$;
CREATE OR REPLACE FUNCTION ST_AsGeoJSON(geometry) RETURNS text LANGUAGE sql IMMUTABLE AS $$ SELECT '{}'::text $$;
"""


def ensure_postgis_compat(sync_engine):
    """Ensure PostGIS or fallback functions exist in the database."""
    with sync_engine.connect() as conn:
        with conn.begin():
            conn.execute(text(COMPAT_SQL))
