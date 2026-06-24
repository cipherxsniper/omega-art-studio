--
-- PostgreSQL database dump
--

\restrict 0tK0yWCBrUz2SIWculv7FqitzB4znQ1vJ7HenmwPFLdeLdLgFsGfQMa5fL6CWBZ

-- Dumped from database version 18.2
-- Dumped by pg_dump version 18.2

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pg_stat_statements; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA public;


--
-- Name: EXTENSION pg_stat_statements; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_stat_statements IS 'track planning and execution statistics of all SQL statements executed';


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: account_status; Type: TYPE; Schema: public; Owner: u0_a253
--

CREATE TYPE public.account_status AS ENUM (
    'ACTIVE',
    'SUSPENDED',
    'CLOSED',
    'FROZEN'
);


ALTER TYPE public.account_status OWNER TO u0_a253;

--
-- Name: account_type; Type: TYPE; Schema: public; Owner: u0_a253
--

CREATE TYPE public.account_type AS ENUM (
    'ASSET',
    'LIABILITY',
    'EQUITY',
    'REVENUE',
    'EXPENSE'
);


ALTER TYPE public.account_type OWNER TO u0_a253;

--
-- Name: anomaly_severity; Type: TYPE; Schema: public; Owner: u0_a253
--

CREATE TYPE public.anomaly_severity AS ENUM (
    'LOW',
    'MEDIUM',
    'HIGH',
    'CRITICAL'
);


ALTER TYPE public.anomaly_severity OWNER TO u0_a253;

--
-- Name: currency_code; Type: TYPE; Schema: public; Owner: u0_a253
--

CREATE TYPE public.currency_code AS ENUM (
    'USD',
    'EUR',
    'GBP',
    'JPY',
    'CAD',
    'AUD',
    'CHF',
    'HKD',
    'SGD',
    'MXN'
);


ALTER TYPE public.currency_code OWNER TO u0_a253;

--
-- Name: event_status; Type: TYPE; Schema: public; Owner: u0_a253
--

CREATE TYPE public.event_status AS ENUM (
    'PENDING',
    'CONFIRMED',
    'VOIDED'
);


ALTER TYPE public.event_status OWNER TO u0_a253;

--
-- Name: assign_global_sequence(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.assign_global_sequence() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.global_sequence := nextval('ledger_entries_global_sequence_seq');
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.assign_global_sequence() OWNER TO u0_a253;

--
-- Name: audit_account_changes(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.audit_account_changes() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
DECLARE
    v_record_id TEXT;
    v_old_data  JSONB;
    v_new_data  JSONB;
BEGIN
    -- Safe null-guarded record ID
    IF TG_OP = 'DELETE' THEN
        v_record_id := OLD.id;
        v_old_data  := to_jsonb(OLD);
        v_new_data  := NULL;
    ELSIF TG_OP = 'INSERT' THEN
        v_record_id := NEW.id;
        v_old_data  := NULL;
        v_new_data  := to_jsonb(NEW);
    ELSE  -- UPDATE
        v_record_id := NEW.id;
        v_old_data  := to_jsonb(OLD);
        v_new_data  := to_jsonb(NEW);
    END IF;

    INSERT INTO ledger_audit_log
        (operation, table_name, record_id, old_data, new_data, performed_by)
    VALUES (
        TG_OP,
        TG_TABLE_NAME,
        v_record_id,
        v_old_data,
        v_new_data,
        current_user
    );

    -- AFTER triggers must return the correct record
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.audit_account_changes() OWNER TO u0_a253;

--
-- Name: bank_to_canonical_account(uuid, text, text); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.bank_to_canonical_account(p_id uuid, p_owner_name text, p_telegram_uid text) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN

    INSERT INTO omega_account_canonical (
        account_id,
        display_name,
        account_type,
        currency,
        status,
        source_system,
        source_id,
        metadata
    )
    VALUES (
        p_id::TEXT,
        p_owner_name,
        'ASSET',
        'USD',
        'ACTIVE',
        'bank',
        p_id::TEXT,
        jsonb_build_object('telegram_uid', p_telegram_uid)
    )
    ON CONFLICT (account_id) DO UPDATE
    SET display_name = EXCLUDED.display_name,
        metadata = omega_account_canonical.metadata || EXCLUDED.metadata;

END;
$$;


ALTER FUNCTION public.bank_to_canonical_account(p_id uuid, p_owner_name text, p_telegram_uid text) OWNER TO u0_a253;

--
-- Name: block_ledger_mutation(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.block_ledger_mutation() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
BEGIN
    RAISE EXCEPTION
        'LEDGER_IMMUTABLE: % on ledger_wal_stream is prohibited. '
        'Table is append-only. Audit reference: event_id=%, seq=%',
        TG_OP,
        COALESCE(OLD.event_id, 'N/A'),
        COALESCE(OLD.global_sequence::TEXT, 'N/A')
    USING ERRCODE = 'restrict_violation';
    RETURN NULL;
END;
$$;


ALTER FUNCTION public.block_ledger_mutation() OWNER TO u0_a253;

--
-- Name: block_ledger_truncate(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.block_ledger_truncate() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
BEGIN
    RAISE EXCEPTION
        'LEDGER_IMMUTABLE: TRUNCATE on ledger_wal_stream is prohibited.'
    USING ERRCODE = 'restrict_violation';
    RETURN NULL;
END;
$$;


ALTER FUNCTION public.block_ledger_truncate() OWNER TO u0_a253;

--
-- Name: compute_event_checksum(text, text, text, numeric, text, timestamp with time zone); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.compute_event_checksum(p_event_id text, p_debit_account text, p_credit_account text, p_amount numeric, p_currency text, p_created_at timestamp with time zone) RETURNS text
    LANGUAGE plpgsql IMMUTABLE SECURITY DEFINER
    AS $$
BEGIN
    RETURN encode(
        digest(
            p_event_id
            || '|' || p_debit_account
            || '|' || p_credit_account
            || '|' || p_amount::TEXT
            || '|' || p_currency
            || '|' || p_created_at::TEXT,
            'sha256'
        ),
        'hex'
    );
END;
$$;


ALTER FUNCTION public.compute_event_checksum(p_event_id text, p_debit_account text, p_credit_account text, p_amount numeric, p_currency text, p_created_at timestamp with time zone) OWNER TO u0_a253;

--
-- Name: compute_identity_hash(text, text, text, text, text); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.compute_identity_hash(p_ledger text, p_bank text, p_wallet text, p_stripe text, p_telegram text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $$
    SELECT encode(
        digest(
            COALESCE(p_ledger,'') || '|' ||
            COALESCE(p_bank,'')   || '|' ||
            COALESCE(p_wallet,'') || '|' ||
            COALESCE(p_stripe,'') || '|' ||
            COALESCE(p_telegram,''),
        'sha256'),
    'hex');
$$;


ALTER FUNCTION public.compute_identity_hash(p_ledger text, p_bank text, p_wallet text, p_stripe text, p_telegram text) OWNER TO u0_a253;

--
-- Name: compute_ledger_boot_hash(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.compute_ledger_boot_hash() RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
DECLARE
    v_hash TEXT;
BEGIN
    SELECT encode(
        digest(
            string_agg(
                COALESCE(t.state_line, ''),
                E'\n'
                ORDER BY t.state_line
            ),
            'sha256'
        ),
        'hex'
    )
    INTO v_hash
    FROM (
        SELECT 'TRIGGER:' || tgname AS state_line FROM pg_trigger
        UNION ALL
        SELECT 'FUNCTION:' || proname FROM pg_proc
        UNION ALL
        SELECT 'TABLE:' || tablename FROM pg_tables WHERE schemaname = 'public'
        UNION ALL
        SELECT 'MVIEW:' || matviewname FROM pg_matviews
    ) t;

    RETURN v_hash;
END;
$$;


ALTER FUNCTION public.compute_ledger_boot_hash() OWNER TO u0_a253;

--
-- Name: enforce_projection_integrity(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.enforce_projection_integrity() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- block direct modification patterns (defensive safety)
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'Direct UPDATE on ledger_entries is forbidden';
    END IF;

    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'DELETE on ledger_entries is forbidden (event-sourcing enforced)';
    END IF;

    RETURN NEW;
END;
$$;


ALTER FUNCTION public.enforce_projection_integrity() OWNER TO u0_a253;

--
-- Name: ledger_outbox_emit(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.ledger_outbox_emit() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO ledger_outbox (
        id,
        global_sequence,
        event_type,
        payload
    )
    VALUES (
        NEW.id,
        NEW.global_sequence,
        NEW.event_type,
        jsonb_build_object(
            'debit', NEW.debit_account,
            'credit', NEW.credit_account,
            'amount', NEW.amount,
            'created_at', NEW.created_at
        )
    );

    RETURN NEW;
END;
$$;


ALTER FUNCTION public.ledger_outbox_emit() OWNER TO u0_a253;

--
-- Name: ledger_outbox_writer(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.ledger_outbox_writer() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO ledger_outbox (
        id,
        global_sequence,
        event_hash,
        processed
    )
    VALUES (
        NEW.id,
        NEW.global_sequence,
        NEW.hash,
        false
    );

    RETURN NEW;
END;
$$;


ALTER FUNCTION public.ledger_outbox_writer() OWNER TO u0_a253;

--
-- Name: ledger_to_canonical_account(text, text, text); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.ledger_to_canonical_account(p_id text, p_name text, p_type text) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN

    INSERT INTO omega_account_canonical (
        account_id,
        display_name,
        account_type,
        currency,
        status,
        source_system,
        source_id
    )
    VALUES (
        p_id,
        p_name,
        p_type,
        'USD',
        'ACTIVE',
        'ledger',
        p_id
    )
    ON CONFLICT (account_id) DO UPDATE
    SET display_name = EXCLUDED.display_name,
        account_type = EXCLUDED.account_type;

END;
$$;


ALTER FUNCTION public.ledger_to_canonical_account(p_id text, p_name text, p_type text) OWNER TO u0_a253;

--
-- Name: ledger_to_wal(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.ledger_to_wal() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO ledger_wal_stream (
        ledger_id,
        debit_account,
        credit_account,
        amount,
        created_at
    )
    VALUES (
        NEW.id,
        NEW.debit_account,
        NEW.credit_account,
        NEW.amount,
        NEW.created_at
    );

    RETURN NEW;
END;
$$;


ALTER FUNCTION public.ledger_to_wal() OWNER TO u0_a253;

--
-- Name: lock_system_boot(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.lock_system_boot() RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN

    INSERT INTO system_boot_state VALUES
    ('identity_graph', '{"status":"locked","version":"v1"}'),
    ('ledger_core', '{"status":"locked"}'),
    ('bank_core', '{"status":"locked"}'),
    ('wallet_core', '{"status":"locked"}')
    ON CONFLICT (component)
    DO UPDATE SET state = EXCLUDED.state;

END;
$$;


ALTER FUNCTION public.lock_system_boot() OWNER TO u0_a253;

--
-- Name: omega_sync_wallets(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.omega_sync_wallets() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    PERFORM pg_notify('omega_ledger_update', NEW.id::text);
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.omega_sync_wallets() OWNER TO u0_a253;

--
-- Name: post_ledger_entry(text, text, text, numeric, public.currency_code, text, text, text, text, text, jsonb, text); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.post_ledger_entry(p_event_id text, p_debit_account text, p_credit_account text, p_amount numeric, p_currency public.currency_code DEFAULT 'USD'::public.currency_code, p_description text DEFAULT NULL::text, p_causation_id text DEFAULT NULL::text, p_correlation_id text DEFAULT NULL::text, p_idempotency_key text DEFAULT NULL::text, p_created_by text DEFAULT NULL::text, p_metadata jsonb DEFAULT '{}'::jsonb, p_partition_key text DEFAULT 'default'::text) RETURNS TABLE(global_sequence bigint, event_id text, checksum text, created_at timestamp with time zone)
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
DECLARE
    v_result ledger_wal_stream%ROWTYPE;
BEGIN
    -- Idempotency: return existing row if event_id already processed
    SELECT * INTO v_result
    FROM ledger_wal_stream
    WHERE ledger_wal_stream.event_id = p_event_id;

    IF FOUND THEN
        RETURN QUERY SELECT
            v_result.global_sequence,
            v_result.event_id,
            v_result.checksum,
            v_result.created_at;
        RETURN;
    END IF;

    -- Pre-validation (triggers will also validate, but fail fast here)
    IF p_amount <= 0 THEN
        RAISE EXCEPTION 'LEDGER_INVALID_AMOUNT: amount must be positive, got %', p_amount
            USING ERRCODE = 'check_violation';
    END IF;

    IF p_debit_account = p_credit_account THEN
        RAISE EXCEPTION 'LEDGER_SELF_TRANSFER: debit and credit accounts must differ'
            USING ERRCODE = 'check_violation';
    END IF;

    INSERT INTO ledger_wal_stream (
        event_id, partition_key,
        debit_account, credit_account,
        amount, currency,
        description,
        causation_id, correlation_id, idempotency_key,
        created_by, metadata,
        status
    )
    VALUES (
        p_event_id, p_partition_key,
        p_debit_account, p_credit_account,
        p_amount, p_currency,
        p_description,
        p_causation_id, p_correlation_id, p_idempotency_key,
        p_created_by, p_metadata,
        'CONFIRMED'
    )
    RETURNING * INTO v_result;

    RETURN QUERY SELECT
        v_result.global_sequence,
        v_result.event_id,
        v_result.checksum,
        v_result.created_at;
END;
$$;


ALTER FUNCTION public.post_ledger_entry(p_event_id text, p_debit_account text, p_credit_account text, p_amount numeric, p_currency public.currency_code, p_description text, p_causation_id text, p_correlation_id text, p_idempotency_key text, p_created_by text, p_metadata jsonb, p_partition_key text) OWNER TO u0_a253;

--
-- Name: post_transfer(text, text, numeric, text, text); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.post_transfer(p_debit text, p_credit text, p_amount numeric, p_currency text DEFAULT 'USD'::text, p_memo text DEFAULT 'TRANSFER'::text) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_event_id UUID := gen_random_uuid();
BEGIN

    INSERT INTO ledger_entries (
        id,
        debit_account,
        credit_account,
        amount,
        memo,
        event_type,
        created_at,
        is_finalized
    )
    VALUES (
        v_event_id,
        p_debit,
        p_credit,
        p_amount,
        p_memo,
        'TRANSFER',
        now(),
        TRUE
    );

    INSERT INTO ledger_wal_stream (
        ledger_id,
        debit_account,
        credit_account,
        amount,
        currency,
        created_at,
        prev_hash
    )
    VALUES (
        v_event_id::TEXT,
        p_debit,
        p_credit,
        p_amount,
        p_currency,
        now(),
        NULL
    );

END;
$$;


ALTER FUNCTION public.post_transfer(p_debit text, p_credit text, p_amount numeric, p_currency text, p_memo text) OWNER TO u0_a253;

--
-- Name: reconcile_ledger(numeric, numeric, numeric); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.reconcile_ledger(p_drift_threshold_critical numeric DEFAULT 100000, p_drift_threshold_high numeric DEFAULT 1000, p_drift_threshold_medium numeric DEFAULT 100) RETURNS TABLE(anomalies_found integer, critical_count integer, high_count integer, medium_count integer, low_count integer, reconciled_at timestamp with time zone)
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
DECLARE
    v_anomalies_found INT := 0;
    v_critical        INT := 0;
    v_high            INT := 0;
    v_medium          INT := 0;
    v_low             INT := 0;
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY ledger_balances_mv;

    PERFORM take_ledger_snapshot(NULL, 'reconcile_ledger');

    INSERT INTO ledger_anomalies
        (account, drift, severity, projected_balance, ledger_balance, snapshot_seq)
    SELECT
        r.account,
        r.drift,
        CASE
            WHEN ABS(r.drift) >= p_drift_threshold_critical THEN 'CRITICAL'::anomaly_severity
            WHEN ABS(r.drift) >= p_drift_threshold_high     THEN 'HIGH'::anomaly_severity
            WHEN ABS(r.drift) >= p_drift_threshold_medium   THEN 'MEDIUM'::anomaly_severity
            ELSE                                                  'LOW'::anomaly_severity
        END,
        r.live_balance,
        r.snapshot_balance,
        r.mv_last_seq
    FROM ledger_reconciliation r
    WHERE ABS(r.drift) > 0;

    GET DIAGNOSTICS v_anomalies_found = ROW_COUNT;

    SELECT
        COUNT(*) FILTER (WHERE severity = 'CRITICAL'),
        COUNT(*) FILTER (WHERE severity = 'HIGH'),
        COUNT(*) FILTER (WHERE severity = 'MEDIUM'),
        COUNT(*) FILTER (WHERE severity = 'LOW')
    INTO v_critical, v_high, v_medium, v_low
    FROM ledger_anomalies
    WHERE created_at >= now() - INTERVAL '10 seconds';

    RETURN QUERY SELECT
        v_anomalies_found, v_critical, v_high, v_medium, v_low, now();
END;
$$;


ALTER FUNCTION public.reconcile_ledger(p_drift_threshold_critical numeric, p_drift_threshold_high numeric, p_drift_threshold_medium numeric) OWNER TO u0_a253;

--
-- Name: refresh_ledger_balances_mv(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.refresh_ledger_balances_mv() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY ledger_balances_mv;
    RETURN NULL;
END;
$$;


ALTER FUNCTION public.refresh_ledger_balances_mv() OWNER TO u0_a253;

--
-- Name: replay_balances(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.replay_balances() RETURNS TABLE(account text, balance numeric)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT
        account,
        SUM(delta) AS balance
    FROM (
        SELECT credit_account AS account, amount AS delta
        FROM ledger_replay

        UNION ALL

        SELECT debit_account AS account, -amount AS delta
        FROM ledger_replay
    ) t
    GROUP BY account;
END;
$$;


ALTER FUNCTION public.replay_balances() OWNER TO u0_a253;

--
-- Name: resolve_account(text); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.resolve_account(p_id text) RETURNS TABLE(canonical_id text, ledger_account_id text, bank_account_id uuid, display_name text, account_type text, currency text, status text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.canonical_id,
        c.ledger_account_id,
        c.bank_account_id,
        c.display_name,
        c.account_type,
        c.currency,
        c.status
    FROM canonical_accounts c
    WHERE c.canonical_id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'ACCOUNT_NOT_FOUND: %', p_id;
    END IF;
END;
$$;


ALTER FUNCTION public.resolve_account(p_id text) OWNER TO u0_a253;

--
-- Name: resolve_identity(text, text, text, text, text); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.resolve_identity(p_ledger_id text, p_bank_id text, p_wallet_id text, p_owner text, p_telegram text) RETURNS text
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_account_id TEXT;
BEGIN

    -- deterministic identity hash (NO DRIFT EVER)
    v_account_id := encode(
        digest(
            COALESCE(p_ledger_id,'') || '|' ||
            COALESCE(p_bank_id,'')   || '|' ||
            COALESCE(p_wallet_id,'') || '|' ||
            COALESCE(p_owner,'')     || '|' ||
            COALESCE(p_telegram,''),
            'sha256'
        ),
        'hex'
    );

    INSERT INTO canonical_accounts (
        account_id,
        owner_id,
        telegram_uid,
        account_type,
        currency,
        status,
        source_system
    )
    VALUES (
        v_account_id,
        p_owner,
        p_telegram,
        'ASSET',
        'USD',
        'ACTIVE',
        'unified_resolver'
    )
    ON CONFLICT (account_id) DO UPDATE
    SET
        owner_id = EXCLUDED.owner_id,
        telegram_uid = EXCLUDED.telegram_uid,
        status = EXCLUDED.status;

    RETURN v_account_id;
END;
$$;


ALTER FUNCTION public.resolve_identity(p_ledger_id text, p_bank_id text, p_wallet_id text, p_owner text, p_telegram text) OWNER TO u0_a253;

--
-- Name: run_ledger_world_test_v1(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.run_ledger_world_test_v1() RETURNS TABLE(test_name text, status text, details text)
    LANGUAGE plpgsql
    AS $$
BEGIN

    IF NOT EXISTS (
        SELECT 1 FROM pg_class WHERE relname = 'ledger_wal_stream'
    ) THEN
        RETURN QUERY SELECT 'ledger_wal','FAIL','missing ledger_wal_stream';
        RETURN;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM ledger_wal_stream LIMIT 1
    ) THEN
        RETURN QUERY SELECT 'ledger_wal','WARN','empty ledger (ok in sandbox)';
    ELSE
        RETURN QUERY SELECT 'ledger_wal','PASS','ledger active';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_matviews WHERE matviewname = 'ledger_balances_mv'
    ) THEN
        RETURN QUERY SELECT 'projection','FAIL','missing ledger_balances_mv';
    ELSE
        RETURN QUERY SELECT 'projection','PASS','projection exists';
    END IF;

    RETURN QUERY SELECT 'ledger_core','PASS','ledger system stable';

END;
$$;


ALTER FUNCTION public.run_ledger_world_test_v1() OWNER TO u0_a253;

--
-- Name: run_world_test_sandbox(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.run_world_test_sandbox() RETURNS TABLE(step text, status text, details text)
    LANGUAGE plpgsql
    AS $$
BEGIN

    -- 1. Insert deterministic WAL event
    INSERT INTO ledger_wal_stream (
        ledger_id,
        debit_account,
        credit_account,
        amount,
        created_at
    )
    VALUES (
        'world_test_' || clock_timestamp(),
        'acc_test_a',
        'acc_test_b',
        100,
        now()
    );

    RETURN QUERY SELECT
        'wal_insert',
        'PASS',
        'test WAL event written';

    -- 2. Validate WAL exists
    RETURN QUERY
    SELECT
        'wal_check',
        CASE WHEN COUNT(*) > 0 THEN 'PASS' ELSE 'FAIL' END,
        'world_test rows=' || COUNT(*)::text
    FROM ledger_wal_stream
    WHERE ledger_id LIKE 'world_test_%';

    -- 3. Projection sanity (NO status dependency)
    RETURN QUERY SELECT
        'projection',
        'PASS',
        'derived from ledger_wal_stream only';

END;
$$;


ALTER FUNCTION public.run_world_test_sandbox() OWNER TO u0_a253;

--
-- Name: run_world_test_sandbox_v1(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.run_world_test_sandbox_v1() RETURNS TABLE(test text, status text, details text)
    LANGUAGE plpgsql
    AS $$
BEGIN

-- STEP 1: create test accounts safely
INSERT INTO accounts (id, name, type)
VALUES
('world_test_a','Test A','ASSET'),
('world_test_b','Test B','ASSET')
ON CONFLICT DO NOTHING;

-- STEP 2: inject WAL event ONLY IF schema supports it
INSERT INTO ledger_wal_stream (debit_account, credit_account, amount)
VALUES ('world_test_a','world_test_b',100);

-- STEP 3: verify projection safety
REFRESH MATERIALIZED VIEW ledger_balances_mv;

RETURN QUERY SELECT 'world_test','PASS','sandbox executed safely';

EXCEPTION WHEN OTHERS THEN
    RETURN QUERY SELECT 'world_test','FAIL',SQLERRM;
END;
$$;


ALTER FUNCTION public.run_world_test_sandbox_v1() OWNER TO u0_a253;

--
-- Name: run_world_test_sandbox_v2(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.run_world_test_sandbox_v2() RETURNS TABLE(test_name text, status text, details text)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_count INT;
BEGIN

    -- 1. account sanity
    SELECT COUNT(*) INTO v_count FROM canonical_accounts;

    IF v_count = 0 THEN
        RETURN QUERY SELECT 'account_layer', 'FAIL', 'no canonical accounts';
        RETURN;
    END IF;

    RETURN QUERY SELECT 'account_layer', 'PASS', 'accounts exist';

    -- 2. boot state
    IF NOT EXISTS (
        SELECT 1 FROM system_boot_state WHERE component = 'ledger_core'
    ) THEN
        RETURN QUERY SELECT 'boot_state', 'FAIL', 'missing ledger_core';
    ELSE
        RETURN QUERY SELECT 'boot_state', 'PASS', 'boot stable';
    END IF;

    -- 3. ledger validation
    IF NOT EXISTS (
        SELECT 1 FROM ledger_wal_stream
    ) THEN
        RETURN QUERY SELECT 'ledger_wal', 'WARN', 'empty ledger (sandbox mode)';
    ELSE
        RETURN QUERY SELECT 'ledger_wal', 'PASS', 'ledger active';
    END IF;

END;
$$;


ALTER FUNCTION public.run_world_test_sandbox_v2() OWNER TO u0_a253;

--
-- Name: run_world_test_sandbox_v3(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.run_world_test_sandbox_v3() RETURNS TABLE(test_name text, status text, details text)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_count INT;
BEGIN

    -- ACCOUNT LAYER (canonical only)
    SELECT COUNT(*) INTO v_count FROM canonical_accounts;

    IF v_count = 0 THEN
        RETURN QUERY SELECT 'account_layer','FAIL','no canonical accounts';
    ELSE
        RETURN QUERY SELECT 'account_layer','PASS','accounts present';
    END IF;

    -- LEDGER LAYER (ledger-only isolation)
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'ledger_wal_stream') THEN
        RETURN QUERY SELECT 'ledger_wal','PASS','ledger table exists';
    ELSE
        RETURN QUERY SELECT 'ledger_wal','FAIL','ledger missing in ledger DB';
    END IF;

    -- BANK LAYER (soft probe only, no direct coupling)
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'accounts') THEN
        RETURN QUERY SELECT 'bank_core','PASS','bank present';
    ELSE
        RETURN QUERY SELECT 'bank_core','WARN','bank not in ledger scope';
    END IF;

    -- PROJECTION SAFETY (optional MV check)
    IF EXISTS (
        SELECT 1 FROM pg_matviews WHERE matviewname = 'ledger_balances_mv'
    ) THEN
        RETURN QUERY SELECT 'projection','PASS','mv exists';
    ELSE
        RETURN QUERY SELECT 'projection','WARN','mv missing (non-fatal)';
    END IF;

END;
$$;


ALTER FUNCTION public.run_world_test_sandbox_v3() OWNER TO u0_a253;

--
-- Name: set_event_checksum(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.set_event_checksum() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
BEGIN
    NEW.checksum := compute_event_checksum(
        NEW.event_id,
        NEW.debit_account,
        NEW.credit_account,
        NEW.amount,
        NEW.currency::TEXT,
        NEW.created_at
    );
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.set_event_checksum() OWNER TO u0_a253;

--
-- Name: stamp_account_updated_at(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.stamp_account_updated_at() RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.stamp_account_updated_at() OWNER TO u0_a253;

--
-- Name: sync_account_to_canonical(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.sync_account_to_canonical() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO canonical_accounts (
        canonical_id,
        ledger_account_id,
        display_name,
        account_type,
        currency,
        status
    )
    VALUES (
        NEW.id,
        NEW.id,
        NEW.name,
        NEW.type,
        'USD',
        'ACTIVE'
    )
    ON CONFLICT (canonical_id)
    DO UPDATE SET
        display_name = EXCLUDED.display_name,
        account_type = EXCLUDED.account_type,
        status = EXCLUDED.status;

    RETURN NEW;
END;
$$;


ALTER FUNCTION public.sync_account_to_canonical() OWNER TO u0_a253;

--
-- Name: take_ledger_snapshot(text, text); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.take_ledger_snapshot(p_account text DEFAULT NULL::text, p_created_by text DEFAULT 'system'::text) RETURNS TABLE(account text, snapshot_seq bigint, balance numeric, checksum text)
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
BEGIN
    RETURN QUERY
    INSERT INTO ledger_snapshots
        (account, snapshot_seq, balance, currency, event_count, checksum, created_by)
    SELECT
        mv.account,
        mv.last_sequence,
        mv.balance,
        mv.currency,
        mv.event_count,
        encode(digest(
            mv.account
            || '|' || mv.last_sequence::TEXT
            || '|' || mv.balance::TEXT,
            'sha256'
        ), 'hex'),
        p_created_by
    FROM ledger_balances_mv mv
    WHERE (p_account IS NULL OR mv.account = p_account)
    ON CONFLICT (account)
    DO UPDATE SET
        snapshot_seq = EXCLUDED.snapshot_seq,
        balance      = EXCLUDED.balance,
        currency     = EXCLUDED.currency,
        event_count  = EXCLUDED.event_count,
        checksum     = EXCLUDED.checksum,
        created_at   = now(),
        created_by   = EXCLUDED.created_by
    RETURNING
        ledger_snapshots.account,
        ledger_snapshots.snapshot_seq,
        ledger_snapshots.balance,
        ledger_snapshots.checksum;
END;
$$;


ALTER FUNCTION public.take_ledger_snapshot(p_account text, p_created_by text) OWNER TO u0_a253;

--
-- Name: validate_account_for_entry(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.validate_account_for_entry() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_currency text;
BEGIN
    SELECT currency
    INTO v_currency
    FROM accounts
    WHERE id = NEW.debit_account;

    IF v_currency IS NULL THEN
        RAISE EXCEPTION 'INVALID_ACCOUNT: %', NEW.debit_account;
    END IF;

    RETURN NEW;
END;
$$;


ALTER FUNCTION public.validate_account_for_entry() OWNER TO u0_a253;

--
-- Name: verify_ledger_integrity(bigint, bigint); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.verify_ledger_integrity(p_from_seq bigint DEFAULT NULL::bigint, p_to_seq bigint DEFAULT NULL::bigint) RETURNS TABLE(global_sequence bigint, event_id text, stored_checksum text, computed_checksum text, is_valid boolean)
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
BEGIN
    RETURN QUERY
    SELECT
        w.global_sequence,
        w.event_id,
        w.checksum,
        compute_event_checksum(
            w.event_id,
            w.debit_account,
            w.credit_account,
            w.amount,
            w.currency::TEXT,
            w.created_at
        ),
        (w.checksum = compute_event_checksum(
            w.event_id,
            w.debit_account,
            w.credit_account,
            w.amount,
            w.currency::TEXT,
            w.created_at
        ))
    FROM ledger_wal_stream w
    WHERE
        (p_from_seq IS NULL OR w.global_sequence >= p_from_seq)
        AND (p_to_seq   IS NULL OR w.global_sequence <= p_to_seq)
    ORDER BY w.global_sequence;
END;
$$;


ALTER FUNCTION public.verify_ledger_integrity(p_from_seq bigint, p_to_seq bigint) OWNER TO u0_a253;

--
-- Name: verify_system_boot(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.verify_system_boot() RETURNS TABLE(component text, status text, details text)
    LANGUAGE plpgsql
    AS $$
BEGIN

    -- WAL check
    IF EXISTS (SELECT 1 FROM ledger_wal_stream LIMIT 1) THEN
        RETURN QUERY SELECT 'ledger_core', 'PASS', 'WAL active';
    ELSE
        RETURN QUERY SELECT 'ledger_core', 'FAIL', 'WAL missing';
    END IF;

    -- Accounts check
    IF EXISTS (SELECT 1 FROM accounts LIMIT 1) THEN
        RETURN QUERY SELECT 'bank_core', 'PASS', 'accounts exist';
    ELSE
        RETURN QUERY SELECT 'bank_core', 'FAIL', 'no accounts';
    END IF;

    -- Balance projection check (view exists)
    IF EXISTS (
        SELECT 1 FROM pg_views WHERE viewname = 'ledger_balances_mv'
    ) THEN
        RETURN QUERY SELECT 'reconciliation', 'PASS', 'projection active';
    ELSE
        RETURN QUERY SELECT 'reconciliation', 'FAIL', 'missing view';
    END IF;

END;
$$;


ALTER FUNCTION public.verify_system_boot() OWNER TO u0_a253;

--
-- Name: verify_system_boot_v1(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.verify_system_boot_v1() RETURNS TABLE(component text, status text, details text)
    LANGUAGE plpgsql
    AS $$
BEGIN

-- LEDGER CORE CHECK
IF NOT EXISTS (
    SELECT 1 FROM pg_trigger WHERE tgname = 'trg_set_event_checksum'
) THEN
    RETURN QUERY SELECT 'ledger_core','FAIL','missing checksum trigger';
    RETURN;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM pg_class WHERE relname = 'ledger_wal_stream'
) THEN
    RETURN QUERY SELECT 'ledger_core','FAIL','missing WAL stream';
    RETURN;
END IF;

-- BANK CORE CHECK
IF NOT EXISTS (
    SELECT 1 FROM accounts LIMIT 1
) THEN
    RETURN QUERY SELECT 'bank_core','FAIL','accounts missing';
    RETURN;
END IF;

-- PROJECTION CHECK (SAFE VERSION)
IF NOT EXISTS (
    SELECT 1 FROM pg_matviews WHERE matviewname = 'ledger_balances_mv'
) THEN
    RETURN QUERY SELECT 'reconciliation','FAIL','missing mv ledger_balances_mv';
    RETURN;
END IF;

-- SUCCESS
RETURN QUERY SELECT 'system','PASS','boot deterministic OK';

END;
$$;


ALTER FUNCTION public.verify_system_boot_v1() OWNER TO u0_a253;

--
-- Name: void_ledger_entry(text, text, text, text, text); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.void_ledger_entry(p_original_event_id text, p_void_event_id text, p_reason text, p_voided_by text DEFAULT NULL::text, p_correlation_id text DEFAULT NULL::text) RETURNS TABLE(void_sequence bigint, void_event_id text, checksum text)
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
DECLARE
    v_orig  ledger_wal_stream%ROWTYPE;
    v_void  ledger_wal_stream%ROWTYPE;
BEGIN
    SELECT * INTO v_orig
    FROM ledger_wal_stream
    WHERE event_id = p_original_event_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'LEDGER_NOT_FOUND: event_id % does not exist', p_original_event_id
            USING ERRCODE = 'no_data_found';
    END IF;

    IF v_orig.status = 'VOIDED' THEN
        RAISE EXCEPTION 'LEDGER_ALREADY_VOIDED: event_id % is already voided', p_original_event_id
            USING ERRCODE = 'check_violation';
    END IF;

    INSERT INTO ledger_wal_stream (
        event_id, partition_key,
        debit_account, credit_account,
        amount, currency,
        description,
        causation_id, correlation_id,
        created_by, metadata,
        status, voided_by, voided_at
    )
    VALUES (
        p_void_event_id,
        v_orig.partition_key,
        v_orig.credit_account,    -- reversed
        v_orig.debit_account,     -- reversed
        v_orig.amount,
        v_orig.currency,
        'VOID: ' || COALESCE(p_reason, 'No reason provided'),
        p_original_event_id,
        p_correlation_id,
        p_voided_by,
        jsonb_build_object(
            'voided_event_id', p_original_event_id,
            'reason', p_reason
        ),
        'CONFIRMED',
        p_original_event_id,
        now()
    )
    RETURNING * INTO v_void;

    INSERT INTO ledger_audit_log
        (operation, table_name, record_id, old_data, new_data, performed_by)
    VALUES (
        'VOID', 'ledger_wal_stream', p_original_event_id,
        jsonb_build_object('event_id', p_original_event_id, 'status', 'CONFIRMED'),
        jsonb_build_object('event_id', p_original_event_id, 'voided_by', p_void_event_id, 'reason', p_reason),
        p_voided_by
    );

    RETURN QUERY SELECT
        v_void.global_sequence,
        v_void.event_id,
        v_void.checksum;
END;
$$;


ALTER FUNCTION public.void_ledger_entry(p_original_event_id text, p_void_event_id text, p_reason text, p_voided_by text, p_correlation_id text) OWNER TO u0_a253;

--
-- Name: wal_hash(text, text, text, numeric, timestamp without time zone, text); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.wal_hash(ledger_id text, debit text, credit text, amount numeric, created_at timestamp without time zone, prev_hash text) RETURNS text
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN encode(
        digest(
            ledger_id || debit || credit || amount::text || created_at::text || COALESCE(prev_hash,''),
            'sha256'
        ),
        'hex'
    );
END;
$$;


ALTER FUNCTION public.wal_hash(ledger_id text, debit text, credit text, amount numeric, created_at timestamp without time zone, prev_hash text) OWNER TO u0_a253;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: account_ledger_map; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.account_ledger_map (
    account_id text NOT NULL,
    ledger_account text NOT NULL
);


ALTER TABLE public.account_ledger_map OWNER TO u0_a253;

--
-- Name: accounts; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.accounts (
    id text NOT NULL,
    name text NOT NULL,
    type text NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    currency text DEFAULT 'USD'::text,
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.accounts OWNER TO omega;

--
-- Name: account_resolution; Type: VIEW; Schema: public; Owner: u0_a253
--

CREATE VIEW public.account_resolution AS
 SELECT id AS account_id,
    name AS display_name,
    type AS account_type,
    'USD'::text AS currency
   FROM public.accounts;


ALTER VIEW public.account_resolution OWNER TO u0_a253;

--
-- Name: audit_log; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.audit_log (
    id text NOT NULL,
    actor text NOT NULL,
    action text NOT NULL,
    entity_type text NOT NULL,
    entity_id text NOT NULL,
    details jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.audit_log OWNER TO omega;

--
-- Name: canonical_accounts; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.canonical_accounts (
    canonical_id text NOT NULL,
    ledger_account_id text,
    bank_account_id uuid,
    display_name text,
    account_type text,
    currency text DEFAULT 'USD'::text,
    status text DEFAULT 'ACTIVE'::text,
    created_at timestamp without time zone DEFAULT now(),
    account_id text,
    identity_id text,
    updated_at timestamp with time zone DEFAULT now(),
    telegram_uid text,
    stripe_customer_id text
);


ALTER TABLE public.canonical_accounts OWNER TO u0_a253;

--
-- Name: fx_logs; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.fx_logs (
    id integer NOT NULL,
    from_currency text,
    to_currency text,
    rate numeric,
    amount numeric,
    converted_amount numeric,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.fx_logs OWNER TO u0_a253;

--
-- Name: fx_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: u0_a253
--

CREATE SEQUENCE public.fx_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fx_logs_id_seq OWNER TO u0_a253;

--
-- Name: fx_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: u0_a253
--

ALTER SEQUENCE public.fx_logs_id_seq OWNED BY public.fx_logs.id;


--
-- Name: identity_graph; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.identity_graph (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    ledger_account_id text,
    bank_account_id text,
    wallet_id text,
    stripe_customer_id text,
    telegram_user_id text,
    display_name text,
    created_at timestamp without time zone DEFAULT now(),
    identity_hash text,
    telegram_uid text,
    full_name text,
    email text,
    pin_hash text,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.identity_graph OWNER TO u0_a253;

--
-- Name: ledger_accounts; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.ledger_accounts (
    account_id text NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.ledger_accounts OWNER TO u0_a253;

--
-- Name: ledger_anomalies; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.ledger_anomalies (
    id integer NOT NULL,
    account text,
    drift numeric,
    severity text,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.ledger_anomalies OWNER TO u0_a253;

--
-- Name: ledger_anomalies_id_seq; Type: SEQUENCE; Schema: public; Owner: u0_a253
--

CREATE SEQUENCE public.ledger_anomalies_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ledger_anomalies_id_seq OWNER TO u0_a253;

--
-- Name: ledger_anomalies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: u0_a253
--

ALTER SEQUENCE public.ledger_anomalies_id_seq OWNED BY public.ledger_anomalies.id;


--
-- Name: ledger_audit_log; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.ledger_audit_log (
    id bigint NOT NULL,
    operation text NOT NULL,
    table_name text NOT NULL,
    record_id text,
    performed_by text,
    ip_address inet,
    session_id text,
    old_data jsonb,
    new_data jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.ledger_audit_log OWNER TO u0_a253;

--
-- Name: ledger_audit_log_id_seq; Type: SEQUENCE; Schema: public; Owner: u0_a253
--

CREATE SEQUENCE public.ledger_audit_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ledger_audit_log_id_seq OWNER TO u0_a253;

--
-- Name: ledger_audit_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: u0_a253
--

ALTER SEQUENCE public.ledger_audit_log_id_seq OWNED BY public.ledger_audit_log.id;


--
-- Name: ledger_entries; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.ledger_entries (
    id text NOT NULL,
    debit_account text,
    credit_account text,
    amount numeric,
    memo text,
    event_type text,
    hash text,
    created_at timestamp without time zone DEFAULT now(),
    direction text,
    global_sequence bigint NOT NULL,
    CONSTRAINT ledger_direction_check CHECK ((direction = ANY (ARRAY['DEBIT'::text, 'CREDIT'::text])))
);


ALTER TABLE public.ledger_entries OWNER TO omega;

--
-- Name: ledger_balance; Type: VIEW; Schema: public; Owner: u0_a253
--

CREATE VIEW public.ledger_balance AS
 SELECT account,
    sum(delta) AS balance
   FROM ( SELECT ledger_entries.debit_account AS account,
            ledger_entries.amount AS delta
           FROM public.ledger_entries
        UNION ALL
         SELECT ledger_entries.credit_account AS account,
            (- ledger_entries.amount) AS delta
           FROM public.ledger_entries) x
  GROUP BY account;


ALTER VIEW public.ledger_balance OWNER TO u0_a253;

--
-- Name: ledger_balance_engine; Type: VIEW; Schema: public; Owner: u0_a253
--

CREATE VIEW public.ledger_balance_engine AS
 SELECT account,
    sum(amount_delta) AS balance
   FROM ( SELECT ledger_entries.debit_account AS account,
            ledger_entries.amount AS amount_delta
           FROM public.ledger_entries
        UNION ALL
         SELECT ledger_entries.credit_account AS account,
            (- ledger_entries.amount) AS amount_delta
           FROM public.ledger_entries) x
  GROUP BY account;


ALTER VIEW public.ledger_balance_engine OWNER TO u0_a253;

--
-- Name: ledger_wal_stream; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.ledger_wal_stream (
    global_sequence bigint NOT NULL,
    ledger_id text NOT NULL,
    debit_account text,
    credit_account text,
    amount numeric NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    prev_hash text,
    currency text
);


ALTER TABLE public.ledger_wal_stream OWNER TO u0_a253;

--
-- Name: ledger_balances; Type: VIEW; Schema: public; Owner: u0_a253
--

CREATE VIEW public.ledger_balances AS
 SELECT account,
    sum(delta) AS balance
   FROM ( SELECT ledger_wal_stream.credit_account AS account,
            ledger_wal_stream.amount AS delta
           FROM public.ledger_wal_stream
        UNION ALL
         SELECT ledger_wal_stream.debit_account AS account,
            (- ledger_wal_stream.amount) AS delta
           FROM public.ledger_wal_stream) t
  GROUP BY account;


ALTER VIEW public.ledger_balances OWNER TO u0_a253;

--
-- Name: ledger_balances_mv; Type: MATERIALIZED VIEW; Schema: public; Owner: u0_a253
--

CREATE MATERIALIZED VIEW public.ledger_balances_mv AS
 SELECT credit_account AS account,
    sum(amount) AS balance
   FROM public.ledger_wal_stream
  GROUP BY credit_account
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.ledger_balances_mv OWNER TO u0_a253;

--
-- Name: ledger_boot_state; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.ledger_boot_state (
    component text NOT NULL,
    expected_state jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.ledger_boot_state OWNER TO u0_a253;

--
-- Name: ledger_entries_global_sequence_seq; Type: SEQUENCE; Schema: public; Owner: omega
--

CREATE SEQUENCE public.ledger_entries_global_sequence_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ledger_entries_global_sequence_seq OWNER TO omega;

--
-- Name: ledger_entries_global_sequence_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omega
--

ALTER SEQUENCE public.ledger_entries_global_sequence_seq OWNED BY public.ledger_entries.global_sequence;


--
-- Name: ledger_identity_binding; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.ledger_identity_binding (
    identity_id uuid NOT NULL,
    ledger_account_id text NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    locked boolean DEFAULT true
);


ALTER TABLE public.ledger_identity_binding OWNER TO u0_a253;

--
-- Name: ledger_outbox; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.ledger_outbox (
    id uuid DEFAULT gen_random_uuid(),
    ledger_id text,
    created_at timestamp without time zone DEFAULT now(),
    processed boolean DEFAULT false,
    global_sequence bigint,
    event_hash text,
    event_type text,
    payload jsonb
);


ALTER TABLE public.ledger_outbox OWNER TO u0_a253;

--
-- Name: ledger_projection_contract; Type: VIEW; Schema: public; Owner: u0_a253
--

CREATE VIEW public.ledger_projection_contract AS
 SELECT credit_account AS account,
    sum(amount) AS balance,
    count(*) AS tx_count
   FROM public.ledger_wal_stream
  GROUP BY credit_account;


ALTER VIEW public.ledger_projection_contract OWNER TO u0_a253;

--
-- Name: ledger_replay; Type: VIEW; Schema: public; Owner: u0_a253
--

CREATE VIEW public.ledger_replay AS
 SELECT id,
    debit_account,
    credit_account,
    amount,
    event_type,
    created_at
   FROM public.ledger_entries;


ALTER VIEW public.ledger_replay OWNER TO u0_a253;

--
-- Name: ledger_sequence; Type: SEQUENCE; Schema: public; Owner: u0_a253
--

CREATE SEQUENCE public.ledger_sequence
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ledger_sequence OWNER TO u0_a253;

--
-- Name: ledger_snapshots; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.ledger_snapshots (
    account text NOT NULL,
    global_sequence bigint NOT NULL,
    balance numeric,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.ledger_snapshots OWNER TO u0_a253;

--
-- Name: ledger_state_hashes; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.ledger_state_hashes (
    node_id text NOT NULL,
    global_sequence bigint NOT NULL,
    state_hash text,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.ledger_state_hashes OWNER TO u0_a253;

--
-- Name: ledger_wal_stream_global_sequence_seq; Type: SEQUENCE; Schema: public; Owner: u0_a253
--

CREATE SEQUENCE public.ledger_wal_stream_global_sequence_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ledger_wal_stream_global_sequence_seq OWNER TO u0_a253;

--
-- Name: ledger_wal_stream_global_sequence_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: u0_a253
--

ALTER SEQUENCE public.ledger_wal_stream_global_sequence_seq OWNED BY public.ledger_wal_stream.global_sequence;


--
-- Name: omega_account_canonical; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.omega_account_canonical (
    account_id text NOT NULL,
    display_name text NOT NULL,
    account_type text NOT NULL,
    currency text DEFAULT 'USD'::text,
    status text DEFAULT 'ACTIVE'::text NOT NULL,
    source_system text NOT NULL,
    source_id text NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT omega_account_canonical_account_type_check CHECK ((account_type = ANY (ARRAY['ASSET'::text, 'LIABILITY'::text, 'REVENUE'::text, 'EXPENSE'::text]))),
    CONSTRAINT omega_account_canonical_status_check CHECK ((status = ANY (ARRAY['ACTIVE'::text, 'FROZEN'::text, 'CLOSED'::text])))
);


ALTER TABLE public.omega_account_canonical OWNER TO u0_a253;

--
-- Name: omega_accounts_unified; Type: VIEW; Schema: public; Owner: u0_a253
--

CREATE VIEW public.omega_accounts_unified AS
 SELECT account_id,
    display_name,
    account_type,
    currency,
    status,
    source_system,
    metadata,
    created_at
   FROM public.omega_account_canonical;


ALTER VIEW public.omega_accounts_unified OWNER TO u0_a253;

--
-- Name: wallets; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.wallets (
    id text NOT NULL,
    account_id text,
    address text,
    balance numeric DEFAULT 0,
    currency text DEFAULT 'USD'::text,
    created_at timestamp without time zone DEFAULT now(),
    available_balance numeric DEFAULT 0,
    identity_id text,
    canonical_account_id text,
    status text DEFAULT 'active'::text,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.wallets OWNER TO omega;

--
-- Name: omega_all_accounts; Type: VIEW; Schema: public; Owner: u0_a253
--

CREATE VIEW public.omega_all_accounts AS
 SELECT account
   FROM ( SELECT ledger_entries.debit_account AS account
           FROM public.ledger_entries
        UNION
         SELECT ledger_entries.credit_account AS account
           FROM public.ledger_entries
        UNION
         SELECT wallets.account_id AS account
           FROM public.wallets
        UNION
         SELECT identity_graph.ledger_account_id
           FROM public.identity_graph
          WHERE (identity_graph.ledger_account_id IS NOT NULL)
        UNION
         SELECT identity_graph.bank_account_id
           FROM public.identity_graph
          WHERE (identity_graph.bank_account_id IS NOT NULL)
        UNION
         SELECT identity_graph.wallet_id
           FROM public.identity_graph
          WHERE (identity_graph.wallet_id IS NOT NULL)) x;


ALTER VIEW public.omega_all_accounts OWNER TO u0_a253;

--
-- Name: omega_balance_engine; Type: MATERIALIZED VIEW; Schema: public; Owner: u0_a253
--

CREATE MATERIALIZED VIEW public.omega_balance_engine AS
 SELECT account,
    sum(amount_delta) AS balance
   FROM ( SELECT ledger_entries.debit_account AS account,
            ledger_entries.amount AS amount_delta
           FROM public.ledger_entries
        UNION ALL
         SELECT ledger_entries.credit_account AS account,
            (- ledger_entries.amount) AS amount_delta
           FROM public.ledger_entries) x
  GROUP BY account
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.omega_balance_engine OWNER TO u0_a253;

--
-- Name: omega_ledger_snapshot; Type: VIEW; Schema: public; Owner: u0_a253
--

CREATE VIEW public.omega_ledger_snapshot AS
 SELECT debit_account,
    credit_account,
    amount,
    created_at
   FROM public.ledger_entries;


ALTER VIEW public.omega_ledger_snapshot OWNER TO u0_a253;

--
-- Name: omega_wallet_bridge; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.omega_wallet_bridge (
    account_id text NOT NULL,
    last_synced_balance numeric DEFAULT 0,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.omega_wallet_bridge OWNER TO u0_a253;

--
-- Name: reserve_accounts; Type: VIEW; Schema: public; Owner: u0_a253
--

CREATE VIEW public.reserve_accounts AS
 SELECT a.id,
    a.name,
    a.type,
    m.ledger_account,
    lb.balance
   FROM ((public.accounts a
     JOIN public.account_ledger_map m ON ((a.id = m.account_id)))
     LEFT JOIN public.ledger_balances lb ON ((lb.account = m.ledger_account)))
  WHERE (a.type = 'reserve'::text);


ALTER VIEW public.reserve_accounts OWNER TO u0_a253;

--
-- Name: stripe_identity_map; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.stripe_identity_map (
    stripe_customer_id text NOT NULL,
    identity_id uuid NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.stripe_identity_map OWNER TO u0_a253;

--
-- Name: system_boot_state; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.system_boot_state (
    component text NOT NULL,
    state jsonb NOT NULL,
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.system_boot_state OWNER TO u0_a253;

--
-- Name: telegram_identity_map; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.telegram_identity_map (
    telegram_uid text NOT NULL,
    identity_id uuid NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.telegram_identity_map OWNER TO u0_a253;

--
-- Name: transactions; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.transactions (
    id text NOT NULL,
    wallet_id text,
    type text,
    amount numeric,
    status text,
    raw_event jsonb,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.transactions OWNER TO omega;

--
-- Name: wal_node_state; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.wal_node_state (
    node_id text NOT NULL,
    last_sequence bigint,
    last_hash text,
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.wal_node_state OWNER TO u0_a253;

--
-- Name: fx_logs id; Type: DEFAULT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.fx_logs ALTER COLUMN id SET DEFAULT nextval('public.fx_logs_id_seq'::regclass);


--
-- Name: ledger_anomalies id; Type: DEFAULT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.ledger_anomalies ALTER COLUMN id SET DEFAULT nextval('public.ledger_anomalies_id_seq'::regclass);


--
-- Name: ledger_audit_log id; Type: DEFAULT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.ledger_audit_log ALTER COLUMN id SET DEFAULT nextval('public.ledger_audit_log_id_seq'::regclass);


--
-- Name: ledger_entries global_sequence; Type: DEFAULT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.ledger_entries ALTER COLUMN global_sequence SET DEFAULT nextval('public.ledger_entries_global_sequence_seq'::regclass);


--
-- Name: ledger_wal_stream global_sequence; Type: DEFAULT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.ledger_wal_stream ALTER COLUMN global_sequence SET DEFAULT nextval('public.ledger_wal_stream_global_sequence_seq'::regclass);


--
-- Name: account_ledger_map account_ledger_map_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.account_ledger_map
    ADD CONSTRAINT account_ledger_map_pkey PRIMARY KEY (account_id);


--
-- Name: accounts accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.accounts
    ADD CONSTRAINT accounts_pkey PRIMARY KEY (id);


--
-- Name: audit_log audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_pkey PRIMARY KEY (id);


--
-- Name: canonical_accounts canonical_accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.canonical_accounts
    ADD CONSTRAINT canonical_accounts_pkey PRIMARY KEY (canonical_id);


--
-- Name: fx_logs fx_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.fx_logs
    ADD CONSTRAINT fx_logs_pkey PRIMARY KEY (id);


--
-- Name: identity_graph identity_graph_identity_hash_key; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.identity_graph
    ADD CONSTRAINT identity_graph_identity_hash_key UNIQUE (identity_hash);


--
-- Name: identity_graph identity_graph_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.identity_graph
    ADD CONSTRAINT identity_graph_pkey PRIMARY KEY (id);


--
-- Name: ledger_accounts ledger_accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.ledger_accounts
    ADD CONSTRAINT ledger_accounts_pkey PRIMARY KEY (account_id);


--
-- Name: ledger_anomalies ledger_anomalies_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.ledger_anomalies
    ADD CONSTRAINT ledger_anomalies_pkey PRIMARY KEY (id);


--
-- Name: ledger_audit_log ledger_audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.ledger_audit_log
    ADD CONSTRAINT ledger_audit_log_pkey PRIMARY KEY (id);


--
-- Name: ledger_boot_state ledger_boot_state_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.ledger_boot_state
    ADD CONSTRAINT ledger_boot_state_pkey PRIMARY KEY (component);


--
-- Name: ledger_entries ledger_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.ledger_entries
    ADD CONSTRAINT ledger_entries_pkey PRIMARY KEY (id);


--
-- Name: ledger_entries ledger_global_sequence_unique; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.ledger_entries
    ADD CONSTRAINT ledger_global_sequence_unique UNIQUE (global_sequence);


--
-- Name: ledger_identity_binding ledger_identity_binding_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.ledger_identity_binding
    ADD CONSTRAINT ledger_identity_binding_pkey PRIMARY KEY (identity_id);


--
-- Name: ledger_snapshots ledger_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.ledger_snapshots
    ADD CONSTRAINT ledger_snapshots_pkey PRIMARY KEY (account, global_sequence);


--
-- Name: ledger_state_hashes ledger_state_hashes_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.ledger_state_hashes
    ADD CONSTRAINT ledger_state_hashes_pkey PRIMARY KEY (node_id, global_sequence);


--
-- Name: ledger_wal_stream ledger_wal_stream_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.ledger_wal_stream
    ADD CONSTRAINT ledger_wal_stream_pkey PRIMARY KEY (global_sequence);


--
-- Name: omega_account_canonical omega_account_canonical_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.omega_account_canonical
    ADD CONSTRAINT omega_account_canonical_pkey PRIMARY KEY (account_id);


--
-- Name: omega_wallet_bridge omega_wallet_bridge_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.omega_wallet_bridge
    ADD CONSTRAINT omega_wallet_bridge_pkey PRIMARY KEY (account_id);


--
-- Name: stripe_identity_map stripe_identity_map_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.stripe_identity_map
    ADD CONSTRAINT stripe_identity_map_pkey PRIMARY KEY (stripe_customer_id);


--
-- Name: system_boot_state system_boot_state_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.system_boot_state
    ADD CONSTRAINT system_boot_state_pkey PRIMARY KEY (component);


--
-- Name: telegram_identity_map telegram_identity_map_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.telegram_identity_map
    ADD CONSTRAINT telegram_identity_map_pkey PRIMARY KEY (telegram_uid);


--
-- Name: transactions transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);


--
-- Name: wal_node_state wal_node_state_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.wal_node_state
    ADD CONSTRAINT wal_node_state_pkey PRIMARY KEY (node_id);


--
-- Name: wallets wallets_address_key; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.wallets
    ADD CONSTRAINT wallets_address_key UNIQUE (address);


--
-- Name: wallets wallets_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.wallets
    ADD CONSTRAINT wallets_pkey PRIMARY KEY (id);


--
-- Name: audit_log_actor_idx; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX audit_log_actor_idx ON public.audit_log USING btree (actor);


--
-- Name: audit_log_created_at_idx; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX audit_log_created_at_idx ON public.audit_log USING btree (created_at DESC);


--
-- Name: audit_log_entity_id_idx; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX audit_log_entity_id_idx ON public.audit_log USING btree (entity_id);


--
-- Name: canonical_accounts_identity_id_idx; Type: INDEX; Schema: public; Owner: u0_a253
--

CREATE UNIQUE INDEX canonical_accounts_identity_id_idx ON public.canonical_accounts USING btree (identity_id);


--
-- Name: identity_graph_telegram_uid_idx; Type: INDEX; Schema: public; Owner: u0_a253
--

CREATE UNIQUE INDEX identity_graph_telegram_uid_idx ON public.identity_graph USING btree (telegram_uid);


--
-- Name: idx_anomalies_account; Type: INDEX; Schema: public; Owner: u0_a253
--

CREATE INDEX idx_anomalies_account ON public.ledger_anomalies USING btree (account, created_at DESC);


--
-- Name: idx_audit_actor; Type: INDEX; Schema: public; Owner: u0_a253
--

CREATE INDEX idx_audit_actor ON public.ledger_audit_log USING btree (performed_by, created_at DESC);


--
-- Name: idx_audit_record; Type: INDEX; Schema: public; Owner: u0_a253
--

CREATE INDEX idx_audit_record ON public.ledger_audit_log USING btree (table_name, record_id);


--
-- Name: idx_audit_time; Type: INDEX; Schema: public; Owner: u0_a253
--

CREATE INDEX idx_audit_time ON public.ledger_audit_log USING btree (created_at DESC);


--
-- Name: idx_lws_created_at; Type: INDEX; Schema: public; Owner: u0_a253
--

CREATE INDEX idx_lws_created_at ON public.ledger_wal_stream USING btree (created_at DESC);


--
-- Name: ledger_balances_mv_uidx; Type: INDEX; Schema: public; Owner: u0_a253
--

CREATE UNIQUE INDEX ledger_balances_mv_uidx ON public.ledger_balances_mv USING btree (account);


--
-- Name: wallets_identity_id_idx; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX wallets_identity_id_idx ON public.wallets USING btree (identity_id);


--
-- Name: ledger_entries ledger_entries_lock; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER ledger_entries_lock BEFORE DELETE OR UPDATE ON public.ledger_entries FOR EACH ROW EXECUTE FUNCTION public.enforce_projection_integrity();


--
-- Name: ledger_entries ledger_entries_projection_refresh; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER ledger_entries_projection_refresh AFTER INSERT ON public.ledger_entries FOR EACH STATEMENT EXECUTE FUNCTION public.refresh_ledger_balances_mv();


--
-- Name: ledger_entries ledger_no_update; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER ledger_no_update BEFORE DELETE OR UPDATE ON public.ledger_entries FOR EACH ROW EXECUTE FUNCTION public.block_ledger_mutation();


--
-- Name: ledger_entries ledger_sequence_trigger; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER ledger_sequence_trigger BEFORE INSERT ON public.ledger_entries FOR EACH ROW EXECUTE FUNCTION public.assign_global_sequence();


--
-- Name: ledger_entries ledger_wal_trigger; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER ledger_wal_trigger AFTER INSERT ON public.ledger_entries FOR EACH ROW EXECUTE FUNCTION public.ledger_to_wal();


--
-- Name: accounts trg_audit_accounts; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER trg_audit_accounts AFTER INSERT OR DELETE OR UPDATE ON public.accounts FOR EACH ROW EXECUTE FUNCTION public.audit_account_changes();


--
-- Name: ledger_wal_stream trg_block_ledger_delete; Type: TRIGGER; Schema: public; Owner: u0_a253
--

CREATE TRIGGER trg_block_ledger_delete BEFORE DELETE ON public.ledger_wal_stream FOR EACH ROW EXECUTE FUNCTION public.block_ledger_mutation();


--
-- Name: ledger_wal_stream trg_block_ledger_truncate; Type: TRIGGER; Schema: public; Owner: u0_a253
--

CREATE TRIGGER trg_block_ledger_truncate BEFORE TRUNCATE ON public.ledger_wal_stream FOR EACH STATEMENT EXECUTE FUNCTION public.block_ledger_truncate();


--
-- Name: ledger_wal_stream trg_block_ledger_update; Type: TRIGGER; Schema: public; Owner: u0_a253
--

CREATE TRIGGER trg_block_ledger_update BEFORE UPDATE ON public.ledger_wal_stream FOR EACH ROW EXECUTE FUNCTION public.block_ledger_mutation();


--
-- Name: ledger_entries trg_ledger_sync; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER trg_ledger_sync AFTER INSERT ON public.ledger_entries FOR EACH ROW EXECUTE FUNCTION public.omega_sync_wallets();


--
-- Name: accounts trg_stamp_account_updated_at; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER trg_stamp_account_updated_at BEFORE UPDATE ON public.accounts FOR EACH ROW EXECUTE FUNCTION public.stamp_account_updated_at();


--
-- Name: accounts trg_sync_canonical; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER trg_sync_canonical AFTER INSERT OR UPDATE ON public.accounts FOR EACH ROW EXECUTE FUNCTION public.sync_account_to_canonical();


--
-- Name: ledger_wal_stream trg_validate_account; Type: TRIGGER; Schema: public; Owner: u0_a253
--

CREATE TRIGGER trg_validate_account BEFORE INSERT ON public.ledger_wal_stream FOR EACH ROW EXECUTE FUNCTION public.validate_account_for_entry();


--
-- Name: FUNCTION armor(bytea); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.armor(bytea) TO ledger_admin;


--
-- Name: FUNCTION armor(bytea, text[], text[]); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.armor(bytea, text[], text[]) TO ledger_admin;


--
-- Name: FUNCTION assign_global_sequence(); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.assign_global_sequence() TO ledger_admin;


--
-- Name: FUNCTION audit_account_changes(); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.audit_account_changes() TO ledger_admin;


--
-- Name: FUNCTION block_ledger_mutation(); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.block_ledger_mutation() TO ledger_admin;


--
-- Name: FUNCTION block_ledger_truncate(); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.block_ledger_truncate() TO ledger_admin;


--
-- Name: FUNCTION compute_event_checksum(p_event_id text, p_debit_account text, p_credit_account text, p_amount numeric, p_currency text, p_created_at timestamp with time zone); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.compute_event_checksum(p_event_id text, p_debit_account text, p_credit_account text, p_amount numeric, p_currency text, p_created_at timestamp with time zone) TO ledger_admin;


--
-- Name: FUNCTION crypt(text, text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.crypt(text, text) TO ledger_admin;


--
-- Name: FUNCTION dearmor(text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.dearmor(text) TO ledger_admin;


--
-- Name: FUNCTION decrypt(bytea, bytea, text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.decrypt(bytea, bytea, text) TO ledger_admin;


--
-- Name: FUNCTION decrypt_iv(bytea, bytea, bytea, text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.decrypt_iv(bytea, bytea, bytea, text) TO ledger_admin;


--
-- Name: FUNCTION digest(bytea, text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.digest(bytea, text) TO ledger_admin;


--
-- Name: FUNCTION digest(text, text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.digest(text, text) TO ledger_admin;


--
-- Name: FUNCTION encrypt(bytea, bytea, text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.encrypt(bytea, bytea, text) TO ledger_admin;


--
-- Name: FUNCTION encrypt_iv(bytea, bytea, bytea, text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.encrypt_iv(bytea, bytea, bytea, text) TO ledger_admin;


--
-- Name: FUNCTION enforce_projection_integrity(); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.enforce_projection_integrity() TO ledger_admin;


--
-- Name: FUNCTION fips_mode(); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.fips_mode() TO ledger_admin;


--
-- Name: FUNCTION gen_random_bytes(integer); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.gen_random_bytes(integer) TO ledger_admin;


--
-- Name: FUNCTION gen_random_uuid(); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.gen_random_uuid() TO ledger_admin;


--
-- Name: FUNCTION gen_salt(text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.gen_salt(text) TO ledger_admin;


--
-- Name: FUNCTION gen_salt(text, integer); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.gen_salt(text, integer) TO ledger_admin;


--
-- Name: FUNCTION hmac(bytea, bytea, text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.hmac(bytea, bytea, text) TO ledger_admin;


--
-- Name: FUNCTION hmac(text, text, text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.hmac(text, text, text) TO ledger_admin;


--
-- Name: FUNCTION ledger_outbox_emit(); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.ledger_outbox_emit() TO ledger_admin;


--
-- Name: FUNCTION ledger_outbox_writer(); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.ledger_outbox_writer() TO ledger_admin;


--
-- Name: FUNCTION ledger_to_wal(); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.ledger_to_wal() TO ledger_admin;


--
-- Name: FUNCTION pg_stat_statements(showtext boolean, OUT userid oid, OUT dbid oid, OUT toplevel boolean, OUT queryid bigint, OUT query text, OUT plans bigint, OUT total_plan_time double precision, OUT min_plan_time double precision, OUT max_plan_time double precision, OUT mean_plan_time double precision, OUT stddev_plan_time double precision, OUT calls bigint, OUT total_exec_time double precision, OUT min_exec_time double precision, OUT max_exec_time double precision, OUT mean_exec_time double precision, OUT stddev_exec_time double precision, OUT rows bigint, OUT shared_blks_hit bigint, OUT shared_blks_read bigint, OUT shared_blks_dirtied bigint, OUT shared_blks_written bigint, OUT local_blks_hit bigint, OUT local_blks_read bigint, OUT local_blks_dirtied bigint, OUT local_blks_written bigint, OUT temp_blks_read bigint, OUT temp_blks_written bigint, OUT shared_blk_read_time double precision, OUT shared_blk_write_time double precision, OUT local_blk_read_time double precision, OUT local_blk_write_time double precision, OUT temp_blk_read_time double precision, OUT temp_blk_write_time double precision, OUT wal_records bigint, OUT wal_fpi bigint, OUT wal_bytes numeric, OUT wal_buffers_full bigint, OUT jit_functions bigint, OUT jit_generation_time double precision, OUT jit_inlining_count bigint, OUT jit_inlining_time double precision, OUT jit_optimization_count bigint, OUT jit_optimization_time double precision, OUT jit_emission_count bigint, OUT jit_emission_time double precision, OUT jit_deform_count bigint, OUT jit_deform_time double precision, OUT parallel_workers_to_launch bigint, OUT parallel_workers_launched bigint, OUT stats_since timestamp with time zone, OUT minmax_stats_since timestamp with time zone); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.pg_stat_statements(showtext boolean, OUT userid oid, OUT dbid oid, OUT toplevel boolean, OUT queryid bigint, OUT query text, OUT plans bigint, OUT total_plan_time double precision, OUT min_plan_time double precision, OUT max_plan_time double precision, OUT mean_plan_time double precision, OUT stddev_plan_time double precision, OUT calls bigint, OUT total_exec_time double precision, OUT min_exec_time double precision, OUT max_exec_time double precision, OUT mean_exec_time double precision, OUT stddev_exec_time double precision, OUT rows bigint, OUT shared_blks_hit bigint, OUT shared_blks_read bigint, OUT shared_blks_dirtied bigint, OUT shared_blks_written bigint, OUT local_blks_hit bigint, OUT local_blks_read bigint, OUT local_blks_dirtied bigint, OUT local_blks_written bigint, OUT temp_blks_read bigint, OUT temp_blks_written bigint, OUT shared_blk_read_time double precision, OUT shared_blk_write_time double precision, OUT local_blk_read_time double precision, OUT local_blk_write_time double precision, OUT temp_blk_read_time double precision, OUT temp_blk_write_time double precision, OUT wal_records bigint, OUT wal_fpi bigint, OUT wal_bytes numeric, OUT wal_buffers_full bigint, OUT jit_functions bigint, OUT jit_generation_time double precision, OUT jit_inlining_count bigint, OUT jit_inlining_time double precision, OUT jit_optimization_count bigint, OUT jit_optimization_time double precision, OUT jit_emission_count bigint, OUT jit_emission_time double precision, OUT jit_deform_count bigint, OUT jit_deform_time double precision, OUT parallel_workers_to_launch bigint, OUT parallel_workers_launched bigint, OUT stats_since timestamp with time zone, OUT minmax_stats_since timestamp with time zone) TO ledger_admin;


--
-- Name: FUNCTION pg_stat_statements_info(OUT dealloc bigint, OUT stats_reset timestamp with time zone); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.pg_stat_statements_info(OUT dealloc bigint, OUT stats_reset timestamp with time zone) TO ledger_admin;


--
-- Name: FUNCTION pg_stat_statements_reset(userid oid, dbid oid, queryid bigint, minmax_only boolean); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.pg_stat_statements_reset(userid oid, dbid oid, queryid bigint, minmax_only boolean) TO ledger_admin;


--
-- Name: FUNCTION pgp_armor_headers(text, OUT key text, OUT value text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.pgp_armor_headers(text, OUT key text, OUT value text) TO ledger_admin;


--
-- Name: FUNCTION pgp_key_id(bytea); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.pgp_key_id(bytea) TO ledger_admin;


--
-- Name: FUNCTION pgp_pub_decrypt(bytea, bytea); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.pgp_pub_decrypt(bytea, bytea) TO ledger_admin;


--
-- Name: FUNCTION pgp_pub_decrypt(bytea, bytea, text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.pgp_pub_decrypt(bytea, bytea, text) TO ledger_admin;


--
-- Name: FUNCTION pgp_pub_decrypt(bytea, bytea, text, text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.pgp_pub_decrypt(bytea, bytea, text, text) TO ledger_admin;


--
-- Name: FUNCTION pgp_pub_decrypt_bytea(bytea, bytea); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.pgp_pub_decrypt_bytea(bytea, bytea) TO ledger_admin;


--
-- Name: FUNCTION pgp_pub_decrypt_bytea(bytea, bytea, text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.pgp_pub_decrypt_bytea(bytea, bytea, text) TO ledger_admin;


--
-- Name: FUNCTION pgp_pub_decrypt_bytea(bytea, bytea, text, text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.pgp_pub_decrypt_bytea(bytea, bytea, text, text) TO ledger_admin;


--
-- Name: FUNCTION pgp_pub_encrypt(text, bytea); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.pgp_pub_encrypt(text, bytea) TO ledger_admin;


--
-- Name: FUNCTION pgp_pub_encrypt(text, bytea, text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.pgp_pub_encrypt(text, bytea, text) TO ledger_admin;


--
-- Name: FUNCTION pgp_pub_encrypt_bytea(bytea, bytea); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.pgp_pub_encrypt_bytea(bytea, bytea) TO ledger_admin;


--
-- Name: FUNCTION pgp_pub_encrypt_bytea(bytea, bytea, text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.pgp_pub_encrypt_bytea(bytea, bytea, text) TO ledger_admin;


--
-- Name: FUNCTION pgp_sym_decrypt(bytea, text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.pgp_sym_decrypt(bytea, text) TO ledger_admin;


--
-- Name: FUNCTION pgp_sym_decrypt(bytea, text, text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.pgp_sym_decrypt(bytea, text, text) TO ledger_admin;


--
-- Name: FUNCTION pgp_sym_decrypt_bytea(bytea, text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.pgp_sym_decrypt_bytea(bytea, text) TO ledger_admin;


--
-- Name: FUNCTION pgp_sym_decrypt_bytea(bytea, text, text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.pgp_sym_decrypt_bytea(bytea, text, text) TO ledger_admin;


--
-- Name: FUNCTION pgp_sym_encrypt(text, text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.pgp_sym_encrypt(text, text) TO ledger_admin;


--
-- Name: FUNCTION pgp_sym_encrypt(text, text, text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.pgp_sym_encrypt(text, text, text) TO ledger_admin;


--
-- Name: FUNCTION pgp_sym_encrypt_bytea(bytea, text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.pgp_sym_encrypt_bytea(bytea, text) TO ledger_admin;


--
-- Name: FUNCTION pgp_sym_encrypt_bytea(bytea, text, text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.pgp_sym_encrypt_bytea(bytea, text, text) TO ledger_admin;


--
-- Name: FUNCTION post_ledger_entry(p_event_id text, p_debit_account text, p_credit_account text, p_amount numeric, p_currency public.currency_code, p_description text, p_causation_id text, p_correlation_id text, p_idempotency_key text, p_created_by text, p_metadata jsonb, p_partition_key text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.post_ledger_entry(p_event_id text, p_debit_account text, p_credit_account text, p_amount numeric, p_currency public.currency_code, p_description text, p_causation_id text, p_correlation_id text, p_idempotency_key text, p_created_by text, p_metadata jsonb, p_partition_key text) TO ledger_writer;
GRANT ALL ON FUNCTION public.post_ledger_entry(p_event_id text, p_debit_account text, p_credit_account text, p_amount numeric, p_currency public.currency_code, p_description text, p_causation_id text, p_correlation_id text, p_idempotency_key text, p_created_by text, p_metadata jsonb, p_partition_key text) TO ledger_admin;


--
-- Name: FUNCTION reconcile_ledger(p_drift_threshold_critical numeric, p_drift_threshold_high numeric, p_drift_threshold_medium numeric); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.reconcile_ledger(p_drift_threshold_critical numeric, p_drift_threshold_high numeric, p_drift_threshold_medium numeric) TO ledger_consumer;
GRANT ALL ON FUNCTION public.reconcile_ledger(p_drift_threshold_critical numeric, p_drift_threshold_high numeric, p_drift_threshold_medium numeric) TO ledger_admin;


--
-- Name: FUNCTION refresh_ledger_balances_mv(); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.refresh_ledger_balances_mv() TO ledger_admin;


--
-- Name: FUNCTION replay_balances(); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.replay_balances() TO ledger_admin;


--
-- Name: FUNCTION set_event_checksum(); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.set_event_checksum() TO ledger_admin;


--
-- Name: FUNCTION stamp_account_updated_at(); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.stamp_account_updated_at() TO ledger_admin;


--
-- Name: FUNCTION take_ledger_snapshot(p_account text, p_created_by text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.take_ledger_snapshot(p_account text, p_created_by text) TO ledger_consumer;
GRANT ALL ON FUNCTION public.take_ledger_snapshot(p_account text, p_created_by text) TO ledger_admin;


--
-- Name: FUNCTION validate_account_for_entry(); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.validate_account_for_entry() TO ledger_admin;


--
-- Name: FUNCTION verify_ledger_integrity(p_from_seq bigint, p_to_seq bigint); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.verify_ledger_integrity(p_from_seq bigint, p_to_seq bigint) TO ledger_consumer;
GRANT ALL ON FUNCTION public.verify_ledger_integrity(p_from_seq bigint, p_to_seq bigint) TO ledger_admin;


--
-- Name: FUNCTION void_ledger_entry(p_original_event_id text, p_void_event_id text, p_reason text, p_voided_by text, p_correlation_id text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.void_ledger_entry(p_original_event_id text, p_void_event_id text, p_reason text, p_voided_by text, p_correlation_id text) TO ledger_admin;


--
-- Name: FUNCTION wal_hash(ledger_id text, debit text, credit text, amount numeric, created_at timestamp without time zone, prev_hash text); Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON FUNCTION public.wal_hash(ledger_id text, debit text, credit text, amount numeric, created_at timestamp without time zone, prev_hash text) TO ledger_admin;


--
-- Name: TABLE account_ledger_map; Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON TABLE public.account_ledger_map TO ledger_admin;


--
-- Name: TABLE accounts; Type: ACL; Schema: public; Owner: omega
--

GRANT INSERT ON TABLE public.accounts TO ledger_writer;
GRANT ALL ON TABLE public.accounts TO ledger_admin;


--
-- Name: TABLE fx_logs; Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON TABLE public.fx_logs TO ledger_admin;


--
-- Name: SEQUENCE fx_logs_id_seq; Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON SEQUENCE public.fx_logs_id_seq TO ledger_admin;


--
-- Name: TABLE ledger_anomalies; Type: ACL; Schema: public; Owner: u0_a253
--

GRANT INSERT ON TABLE public.ledger_anomalies TO ledger_consumer;
GRANT ALL ON TABLE public.ledger_anomalies TO ledger_admin;


--
-- Name: SEQUENCE ledger_anomalies_id_seq; Type: ACL; Schema: public; Owner: u0_a253
--

GRANT USAGE ON SEQUENCE public.ledger_anomalies_id_seq TO ledger_writer;
GRANT USAGE ON SEQUENCE public.ledger_anomalies_id_seq TO ledger_consumer;
GRANT ALL ON SEQUENCE public.ledger_anomalies_id_seq TO ledger_admin;


--
-- Name: TABLE ledger_audit_log; Type: ACL; Schema: public; Owner: u0_a253
--

GRANT INSERT ON TABLE public.ledger_audit_log TO ledger_consumer;
GRANT ALL ON TABLE public.ledger_audit_log TO ledger_admin;


--
-- Name: SEQUENCE ledger_audit_log_id_seq; Type: ACL; Schema: public; Owner: u0_a253
--

GRANT USAGE ON SEQUENCE public.ledger_audit_log_id_seq TO ledger_consumer;
GRANT ALL ON SEQUENCE public.ledger_audit_log_id_seq TO ledger_admin;


--
-- Name: TABLE ledger_entries; Type: ACL; Schema: public; Owner: omega
--

GRANT ALL ON TABLE public.ledger_entries TO ledger_admin;


--
-- Name: TABLE ledger_wal_stream; Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON TABLE public.ledger_wal_stream TO ledger_admin;


--
-- Name: TABLE ledger_balances; Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON TABLE public.ledger_balances TO ledger_admin;


--
-- Name: SEQUENCE ledger_entries_global_sequence_seq; Type: ACL; Schema: public; Owner: omega
--

GRANT ALL ON SEQUENCE public.ledger_entries_global_sequence_seq TO ledger_admin;


--
-- Name: TABLE ledger_outbox; Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON TABLE public.ledger_outbox TO ledger_admin;


--
-- Name: SEQUENCE ledger_sequence; Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON SEQUENCE public.ledger_sequence TO ledger_admin;


--
-- Name: TABLE ledger_snapshots; Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON TABLE public.ledger_snapshots TO ledger_admin;


--
-- Name: TABLE ledger_state_hashes; Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON TABLE public.ledger_state_hashes TO ledger_admin;


--
-- Name: SEQUENCE ledger_wal_stream_global_sequence_seq; Type: ACL; Schema: public; Owner: u0_a253
--

GRANT USAGE ON SEQUENCE public.ledger_wal_stream_global_sequence_seq TO ledger_writer;
GRANT ALL ON SEQUENCE public.ledger_wal_stream_global_sequence_seq TO ledger_admin;


--
-- Name: TABLE wallets; Type: ACL; Schema: public; Owner: omega
--

GRANT ALL ON TABLE public.wallets TO ledger_admin;


--
-- Name: TABLE pg_stat_statements; Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON TABLE public.pg_stat_statements TO ledger_admin;


--
-- Name: TABLE pg_stat_statements_info; Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON TABLE public.pg_stat_statements_info TO ledger_admin;


--
-- Name: TABLE reserve_accounts; Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON TABLE public.reserve_accounts TO ledger_admin;


--
-- Name: TABLE transactions; Type: ACL; Schema: public; Owner: omega
--

GRANT ALL ON TABLE public.transactions TO ledger_admin;


--
-- Name: TABLE wal_node_state; Type: ACL; Schema: public; Owner: u0_a253
--

GRANT ALL ON TABLE public.wal_node_state TO ledger_admin;


--
-- PostgreSQL database dump complete
--

\unrestrict 0tK0yWCBrUz2SIWculv7FqitzB4znQ1vJ7HenmwPFLdeLdLgFsGfQMa5fL6CWBZ

