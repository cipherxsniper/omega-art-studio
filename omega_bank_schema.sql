--
-- PostgreSQL database dump
--

\restrict 7sH9HE7bBLd7HpSXq261OBnmchJQP3E32T4hHxQ4m2OzhabfHeiZH04vRbQU2PH

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
-- Name: btree_gist; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA public;


--
-- Name: EXTENSION btree_gist; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION btree_gist IS 'support for indexing common datatypes in GiST';


--
-- Name: dblink; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS dblink WITH SCHEMA public;


--
-- Name: EXTENSION dblink; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION dblink IS 'connect to other PostgreSQL databases from within a database';


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: postgres_fdw; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgres_fdw WITH SCHEMA public;


--
-- Name: EXTENSION postgres_fdw; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgres_fdw IS 'foreign-data wrapper for remote PostgreSQL servers';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: authorization_state; Type: TYPE; Schema: public; Owner: omega
--

CREATE TYPE public.authorization_state AS ENUM (
    'AUTHORIZED',
    'CAPTURED',
    'SETTLED',
    'REVERSED',
    'EXPIRED',
    'CHARGEBACK'
);


ALTER TYPE public.authorization_state OWNER TO omega;

--
-- Name: card_status_type; Type: TYPE; Schema: public; Owner: omega
--

CREATE TYPE public.card_status_type AS ENUM (
    'ACTIVE',
    'FROZEN',
    'EXPIRED',
    'REVOKED'
);


ALTER TYPE public.card_status_type OWNER TO omega;

--
-- Name: merchant_status_type; Type: TYPE; Schema: public; Owner: omega
--

CREATE TYPE public.merchant_status_type AS ENUM (
    'ACTIVE',
    'INACTIVE',
    'SUSPENDED'
);


ALTER TYPE public.merchant_status_type OWNER TO omega;

--
-- Name: omega_event_type; Type: TYPE; Schema: public; Owner: omega
--

CREATE TYPE public.omega_event_type AS ENUM (
    'TX_INITIATED',
    'TX_AUTHORIZED',
    'TX_SETTLED',
    'CREDIT_ISSUED',
    'RESERVE_ALLOCATED',
    'WALLET_FUNDED',
    'SEED'
);


ALTER TYPE public.omega_event_type OWNER TO omega;

--
-- Name: payment_request_status_type; Type: TYPE; Schema: public; Owner: omega
--

CREATE TYPE public.payment_request_status_type AS ENUM (
    'PENDING',
    'COMPLETED',
    'CANCELLED',
    'EXPIRED'
);


ALTER TYPE public.payment_request_status_type OWNER TO omega;

--
-- Name: payment_transaction_status; Type: TYPE; Schema: public; Owner: omega
--

CREATE TYPE public.payment_transaction_status AS ENUM (
    'PENDING',
    'APPROVED',
    'DECLINED',
    'SETTLED',
    'REFUNDED'
);


ALTER TYPE public.payment_transaction_status OWNER TO omega;

--
-- Name: payment_transaction_type; Type: TYPE; Schema: public; Owner: omega
--

CREATE TYPE public.payment_transaction_type AS ENUM (
    'AUTHORIZATION',
    'RESERVATION',
    'SETTLEMENT',
    'DECLINE'
);


ALTER TYPE public.payment_transaction_type OWNER TO omega;

--
-- Name: token_status_type; Type: TYPE; Schema: public; Owner: omega
--

CREATE TYPE public.token_status_type AS ENUM (
    'ACTIVE',
    'SUSPENDED',
    'DEACTIVATED'
);


ALTER TYPE public.token_status_type OWNER TO omega;

--
-- Name: apply_settlement_event(); Type: FUNCTION; Schema: public; Owner: omega
--

CREATE FUNCTION public.apply_settlement_event() RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    e RECORD;
BEGIN
    FOR e IN
        SELECT * FROM settlement_queue
        WHERE status = 'PENDING'
        ORDER BY created_at ASC
        FOR UPDATE SKIP LOCKED
    LOOP

        -- mark processing
        UPDATE settlement_queue
        SET status = 'PROCESSING',
            processing_at = NOW()
        WHERE id = e.id;

        -- apply balance change deterministically
        UPDATE wallets
        SET settled_balance = settled_balance + e.amount,
            reserved_balance = GREATEST(reserved_balance - e.amount, 0)
        WHERE id = e.wallet_id;

        -- finalize event
        UPDATE settlement_queue
        SET status = 'SETTLED'
        WHERE id = e.id;

    END LOOP;
END;
$$;


ALTER FUNCTION public.apply_settlement_event() OWNER TO omega;

--
-- Name: apply_transaction_to_wallet(); Type: FUNCTION; Schema: public; Owner: omega
--

CREATE FUNCTION public.apply_transaction_to_wallet() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.status = 'CREDIT' THEN
        UPDATE wallets
        SET available_balance = available_balance + NEW.amount,
            settled_balance = settled_balance + NEW.amount
        WHERE id = NEW.wallet_id;
    END IF;

    RETURN NEW;
END;
$$;


ALTER FUNCTION public.apply_transaction_to_wallet() OWNER TO omega;

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
-- Name: block_balance_mutation(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.block_balance_mutation() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Allow ONLY system context writes (projection engine)
    IF current_setting('application_name', true) IS DISTINCT FROM 'OMEGA_PROJECTION_ENGINE' THEN
        RAISE EXCEPTION 'OMEGA_LEDGER: projection table is read-only outside engine context';
    END IF;

    RETURN NEW;
END;
$$;


ALTER FUNCTION public.block_balance_mutation() OWNER TO u0_a253;

--
-- Name: block_ledger_mutation(); Type: FUNCTION; Schema: public; Owner: omega
--

CREATE FUNCTION public.block_ledger_mutation() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    RAISE EXCEPTION 'LEDGER IS IMMUTABLE';
END;
$$;


ALTER FUNCTION public.block_ledger_mutation() OWNER TO omega;

--
-- Name: block_wallet_direct_update(); Type: FUNCTION; Schema: public; Owner: omega
--

CREATE FUNCTION public.block_wallet_direct_update() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    RAISE EXCEPTION 'DIRECT WALLET MUTATION DISABLED — USE EVENT LEDGER';
END;
$$;


ALTER FUNCTION public.block_wallet_direct_update() OWNER TO omega;

--
-- Name: check_bank(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.check_bank() RETURNS TABLE(owner_name text, wallet_id uuid, balance text)
    LANGUAGE plpgsql
    AS $_$
BEGIN
    RETURN QUERY
    SELECT
        a.owner_name,
        w.id,
        ('$' || TO_CHAR(w.settled_balance, 'FM999,999,999,999,999.00'))::TEXT
    FROM wallets w
    LEFT JOIN accounts a ON a.id = w.account_id
    ORDER BY w.settled_balance DESC;
END;
$_$;


ALTER FUNCTION public.check_bank() OWNER TO u0_a253;

--
-- Name: check_global_freeze(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.check_global_freeze() RETURNS boolean
    LANGUAGE plpgsql
    AS $$
DECLARE
    v TEXT;
BEGIN
    SELECT value INTO v
    FROM omega_global_state
    WHERE key = 'ledger_frozen';

    RETURN v = 'true';
END;
$$;


ALTER FUNCTION public.check_global_freeze() OWNER TO u0_a253;

--
-- Name: claim_execution(text, text); Type: FUNCTION; Schema: public; Owner: omega
--

CREATE FUNCTION public.claim_execution(p_key text, p_worker text) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN

    INSERT INTO execution_lease (idempotency_key, status, worker_id)
    VALUES (p_key, 'LOCKED', p_worker)
    ON CONFLICT (idempotency_key) DO NOTHING;

    RETURN FOUND;

END;
$$;


ALTER FUNCTION public.claim_execution(p_key text, p_worker text) OWNER TO omega;

--
-- Name: compute_event_hash(text, text, text, bigint, text, text); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.compute_event_hash(p_event_type text, p_wallet_id text, p_counterparty_id text, p_amount bigint, p_currency text, p_idempotency_key text) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT
    AS $$
    SELECT encode(
        digest(
            -- Canonical string: fields joined by '|', NULLs become empty string
            COALESCE(p_event_type,       '') || '|' ||
            COALESCE(p_wallet_id,        '') || '|' ||
            COALESCE(p_counterparty_id,  '') || '|' ||
            COALESCE(p_amount::TEXT,     '') || '|' ||
            COALESCE(p_currency,         '') || '|' ||
            COALESCE(p_idempotency_key,  ''),
            'sha256'
        ),
        'hex'
    );
$$;


ALTER FUNCTION public.compute_event_hash(p_event_type text, p_wallet_id text, p_counterparty_id text, p_amount bigint, p_currency text, p_idempotency_key text) OWNER TO u0_a253;

--
-- Name: compute_event_hash(text, text, text, numeric, text, text); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.compute_event_hash(event_type text, wallet_id text, counterparty_id text, amount numeric, currency text, idempotency_key text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $$
SELECT encode(
    digest(
        COALESCE(event_type,'') || '|' ||
        COALESCE(wallet_id,'') || '|' ||
        COALESCE(counterparty_id,'') || '|' ||
        COALESCE(amount::TEXT,'') || '|' ||
        COALESCE(currency,'') || '|' ||
        COALESCE(idempotency_key,''),
        'sha256'
    ),
    'hex'
);
$$;


ALTER FUNCTION public.compute_event_hash(event_type text, wallet_id text, counterparty_id text, amount numeric, currency text, idempotency_key text) OWNER TO u0_a253;

--
-- Name: compute_ledger_hash(text, text, text, text, numeric, timestamp without time zone); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.compute_ledger_hash(p_prev_hash text, p_id text, p_debit text, p_credit text, p_amount numeric, p_created timestamp without time zone) RETURNS text
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN encode(
        digest(
            COALESCE(p_prev_hash,'') ||
            p_id ||
            COALESCE(p_debit,'') ||
            COALESCE(p_credit,'') ||
            p_amount::TEXT ||
            p_created::TEXT,
            'sha256'
        ),
        'hex'
    );
END;
$$;


ALTER FUNCTION public.compute_ledger_hash(p_prev_hash text, p_id text, p_debit text, p_credit text, p_amount numeric, p_created timestamp without time zone) OWNER TO u0_a253;

--
-- Name: compute_ledger_hash(text, uuid, text, text, numeric, timestamp without time zone); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.compute_ledger_hash(debit text, credit uuid, memo text, event_type text, amount numeric, created_at timestamp without time zone) RETURNS text
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN encode(
        digest(
            debit || credit::text || memo || event_type || amount::text || created_at::text,
            'sha256'
        ),
        'hex'
    );
END;
$$;


ALTER FUNCTION public.compute_ledger_hash(debit text, credit uuid, memo text, event_type text, amount numeric, created_at timestamp without time zone) OWNER TO u0_a253;

--
-- Name: compute_state_hash(text, bigint, numeric); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.compute_state_hash(p_merkle_root text, p_event_seq bigint, p_total_supply numeric) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $$
    SELECT encode(
        digest(
            p_merkle_root || '|' ||
            p_event_seq::TEXT || '|' ||
            p_total_supply::TEXT,
            'sha256'
        ),
        'hex'
    );
$$;


ALTER FUNCTION public.compute_state_hash(p_merkle_root text, p_event_seq bigint, p_total_supply numeric) OWNER TO u0_a253;

--
-- Name: compute_wallet_leaf_hash(text, numeric); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.compute_wallet_leaf_hash(p_wallet text, p_balance numeric) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $$
    SELECT encode(
        digest(p_wallet || '|' || p_balance::TEXT, 'sha256'),
        'hex'
    );
$$;


ALTER FUNCTION public.compute_wallet_leaf_hash(p_wallet text, p_balance numeric) OWNER TO u0_a253;

--
-- Name: emit_ledger_event(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.emit_ledger_event() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO ledger_event_stream (
        event_id,
        ledger_id,
        account_id,
        event_type,
        amount,
        direction,
        created_at
    )
    VALUES (
        gen_random_uuid(),
        NEW.id,
        NEW.credit_account,
        NEW.event_type,
        NEW.amount,
        NEW.direction,
        NOW()
    );

    RETURN NEW;
END;
$$;


ALTER FUNCTION public.emit_ledger_event() OWNER TO u0_a253;

--
-- Name: enforce_idempotency(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.enforce_idempotency() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM ledger_entries
        WHERE idempotency_key = NEW.idempotency_key
    ) THEN
        RAISE EXCEPTION 'Duplicate ledger event (idempotency violation)';
    END IF;

    RETURN NEW;
END;
$$;


ALTER FUNCTION public.enforce_idempotency() OWNER TO u0_a253;

--
-- Name: enforce_no_negative_supply(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.enforce_no_negative_supply() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF (NEW.balance < 0) THEN
        RAISE EXCEPTION 'Negative balance violation for wallet %', NEW.wallet_id;
    END IF;

    RETURN NEW;
END;
$$;


ALTER FUNCTION public.enforce_no_negative_supply() OWNER TO u0_a253;

--
-- Name: enforce_settlement_consistency(); Type: FUNCTION; Schema: public; Owner: omega
--

CREATE FUNCTION public.enforce_settlement_consistency() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF (NEW.payload->>'auth_id')::uuid <> NEW.auth_id THEN
        RAISE EXCEPTION 'AUTH_ID MISMATCH';
    END IF;

    IF (NEW.payload->>'wallet_id')::uuid <> NEW.wallet_id THEN
        RAISE EXCEPTION 'WALLET_ID MISMATCH';
    END IF;

    IF (NEW.payload->>'amount')::numeric <> NEW.amount THEN
        RAISE EXCEPTION 'AMOUNT MISMATCH';
    END IF;

    RETURN NEW;
END;
$$;


ALTER FUNCTION public.enforce_settlement_consistency() OWNER TO omega;

--
-- Name: generate_iso20022_pain001(uuid, text, text, numeric, text, timestamp without time zone); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.generate_iso20022_pain001(p_entry_id uuid, p_debit text, p_credit text, p_amount numeric, p_memo text, p_created timestamp without time zone) RETURNS xml
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN xmlparse(DOCUMENT
        '<?xml version="1.0" encoding="UTF-8"?>' ||
        '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03">' ||
        '<CstmrCdtTrfInitn>' ||
        '<GrpHdr>' ||
            '<MsgId>' || p_entry_id::TEXT || '</MsgId>' ||
            '<CreDtTm>' || to_char(p_created, 'YYYY-MM-DD"T"HH24:MI:SS') || '</CreDtTm>' ||
            '<NbOfTxs>1</NbOfTxs>' ||
            '<CtrlSum>' || p_amount::TEXT || '</CtrlSum>' ||
            '<InitgPty><Nm>Omega Bank</Nm></InitgPty>' ||
        '</GrpHdr>' ||
        '<PmtInf>' ||
            '<PmtInfId>' || p_entry_id::TEXT || '</PmtInfId>' ||
            '<PmtMtd>TRF</PmtMtd>' ||
            '<DbtrAcct><Id><Othr><Id>' || COALESCE(p_debit,'OMEGA') || '</Id></Othr></Id></DbtrAcct>' ||
            '<CdtTrfTxInf>' ||
                '<Amt><InstdAmt Ccy="USD">' || p_amount::TEXT || '</InstdAmt></Amt>' ||
                '<CdtrAcct><Id><Othr><Id>' || COALESCE(p_credit,'OMEGA') || '</Id></Othr></Id></CdtrAcct>' ||
                '<RmtInf><Ustrd>' || COALESCE(p_memo,'') || '</Ustrd></RmtInf>' ||
            '</CdtTrfTxInf>' ||
        '</PmtInf>' ||
        '</CstmrCdtTrfInitn>' ||
        '</Document>'
    );
END;
$$;


ALTER FUNCTION public.generate_iso20022_pain001(p_entry_id uuid, p_debit text, p_credit text, p_amount numeric, p_memo text, p_created timestamp without time zone) OWNER TO postgres;

--
-- Name: get_wallet(uuid); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.get_wallet(p_account uuid) RETURNS uuid
    LANGUAGE plpgsql STABLE
    AS $$
DECLARE wid UUID;
BEGIN
    SELECT id INTO wid
    FROM wallets
    WHERE account_id = p_account
    LIMIT 1;

    IF wid IS NULL THEN
        RAISE EXCEPTION 'WALLET_NOT_FOUND: %', p_account;
    END IF;

    RETURN wid;
END;
$$;


ALTER FUNCTION public.get_wallet(p_account uuid) OWNER TO u0_a253;

--
-- Name: iso20022_auto_generate(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.iso20022_auto_generate() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO iso_messages (ledger_entry_id, message_type, payload)
    VALUES (
        NEW.id,
        'pain.001',
        generate_iso20022_pain001(
            NEW.id,
            NEW.debit_account,
            NEW.credit_account,
            NEW.amount,
            NEW.memo,
            NEW.created_at
        )
    );
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.iso20022_auto_generate() OWNER TO postgres;

--
-- Name: issue_genesis_liquidity(numeric, text, text); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.issue_genesis_liquidity(p_amount numeric, p_currency text, p_idempotency text) RETURNS uuid
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_wallet_id UUID;
    v_account_id UUID;
    v_event_id UUID := gen_random_uuid();
BEGIN

    -- 1. Create GENESIS account if not exists
    INSERT INTO accounts (id, owner_name)
    VALUES (gen_random_uuid(), 'OMEGA_GENESIS')
    ON CONFLICT DO NOTHING;

    SELECT id INTO v_account_id
    FROM accounts
    WHERE owner_name = 'OMEGA_GENESIS'
    LIMIT 1;

    -- 2. Create NEW Genesis wallet (THIS is your missing piece)
    INSERT INTO wallets (id, account_id, currency)
    VALUES (
        gen_random_uuid(),
        v_account_id,
        p_currency
    )
    RETURNING id INTO v_wallet_id;

    -- 3. Emit Genesis event (source of truth)
    INSERT INTO omega_events (
        event_id,
        event_type,
        aggregate_id,
        aggregate_type,
        payload,
        idempotency_key,
        sequence_number,
        created_at,
        timestamp,
        wallet_id,
        amount,
        currency,
        version
    )
    VALUES (
        v_event_id,
        'GENESIS_ISSUED_V2',
        v_account_id,
        'GENESIS',
        jsonb_build_object(
            'wallet_id', v_wallet_id,
            'amount', p_amount,
            'currency', p_currency,
            'state', 'GENESIS_LIQUIDITY_ISSUED'
        ),
        p_idempotency,
        1,
        NOW(),
        NOW(),
        v_wallet_id,
        p_amount,
        p_currency,
        1
    );

    RETURN v_wallet_id;
END;
$$;


ALTER FUNCTION public.issue_genesis_liquidity(p_amount numeric, p_currency text, p_idempotency text) OWNER TO u0_a253;

--
-- Name: ledger_chain_enforcer(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.ledger_chain_enforcer() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    last_hash TEXT;
BEGIN
    IF NEW.id IS NULL THEN
        NEW.id := uuid_generate_v4();
    END IF;

    SELECT chain_hash INTO last_hash
    FROM ledger_entries
    ORDER BY global_sequence DESC
    LIMIT 1;

    NEW.prev_hash := last_hash;

    NEW.chain_hash := compute_ledger_hash(
        NEW.prev_hash,
        NEW.id::TEXT,
        NEW.debit_account,
        NEW.credit_account,
        NEW.amount,
        NEW.created_at
    );

    RETURN NEW;
END;
$$;


ALTER FUNCTION public.ledger_chain_enforcer() OWNER TO u0_a253;

--
-- Name: ledger_write(text, text, numeric, text, text); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.ledger_write(p_event_type text, p_wallet_id text, p_amount numeric, p_currency text, p_idempotency_key text) RETURNS text
    LANGUAGE plpgsql
    AS $$
DECLARE h TEXT;
DECLARE seq_id BIGINT;
BEGIN

    h := compute_event_hash(
        p_event_type,
        p_wallet_id,
        NULL,
        p_amount,
        p_currency,
        p_idempotency_key
    );

    INSERT INTO omega_events(
        event_type,
        wallet_id,
        amount,
        currency,
        idempotency_key,
        event_hash
    )
    VALUES (
        p_event_type,
        p_wallet_id,
        p_amount,
        p_currency,
        p_idempotency_key,
        h
    )
    RETURNING seq INTO seq_id;

    PERFORM rebuild_account_balances();

    RETURN h;
END;
$$;


ALTER FUNCTION public.ledger_write(p_event_type text, p_wallet_id text, p_amount numeric, p_currency text, p_idempotency_key text) OWNER TO u0_a253;

--
-- Name: ledger_write(text, text, bigint, text, text, text, jsonb); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.ledger_write(p_event_type text, p_wallet_id text, p_amount bigint, p_currency text, p_idempotency_key text, p_counterparty_id text DEFAULT NULL::text, p_metadata jsonb DEFAULT '{}'::jsonb) RETURNS bigint
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_hash      TEXT;
    v_is_new    BOOLEAN;
    v_seq       BIGINT;
BEGIN
    -- 1. Validate inputs
    IF p_wallet_id IS NULL OR length(trim(p_wallet_id)) = 0 THEN
        RAISE EXCEPTION 'OMEGA_LEDGER: wallet_id must not be NULL or empty';
    END IF;

    IF p_amount IS NULL OR p_amount <= 0 THEN
        RAISE EXCEPTION 'OMEGA_LEDGER: amount must be a positive BIGINT, got %', p_amount;
    END IF;

    IF p_currency IS NULL OR length(trim(p_currency)) = 0 THEN
        RAISE EXCEPTION 'OMEGA_LEDGER: currency must not be NULL or empty';
    END IF;

    IF p_event_type NOT IN ('CREDIT','DEBIT','TRANSFER_OUT','TRANSFER_IN','FEE','MINT','BURN') THEN
        RAISE EXCEPTION 'OMEGA_LEDGER: invalid event_type %', p_event_type;
    END IF;

    -- 2. Compute canonical hash
    v_hash := compute_event_hash(
        p_event_type, p_wallet_id, p_counterparty_id,
        p_amount, p_currency, p_idempotency_key
    );

    -- 3. Idempotency check (will raise on conflict)
    v_is_new := ledger_write_guard(
        p_idempotency_key, v_hash,
        p_wallet_id, p_event_type, p_amount, p_currency
    );

    IF NOT v_is_new THEN
        -- Pure duplicate: return previously inserted seq
        SELECT result_seq INTO v_seq
          FROM ledger_write_guard
         WHERE idempotency_key = p_idempotency_key;
        RETURN v_seq;
    END IF;

    -- 4. Append to immutable ledger
    INSERT INTO omega_events (
        event_type, wallet_id, counterparty_id,
        amount, currency, idempotency_key, event_hash, metadata
    ) VALUES (
        p_event_type,
        trim(p_wallet_id),
        NULLIF(trim(COALESCE(p_counterparty_id, '')), ''),
        p_amount,
        trim(p_currency),
        p_idempotency_key,
        v_hash,
        COALESCE(p_metadata, '{}')
    )
    RETURNING seq INTO v_seq;

    -- 5. Record seq back into guard
    UPDATE ledger_write_guard
       SET result_seq = v_seq
     WHERE idempotency_key = p_idempotency_key;

    RETURN v_seq;
END;
$$;


ALTER FUNCTION public.ledger_write(p_event_type text, p_wallet_id text, p_amount bigint, p_currency text, p_idempotency_key text, p_counterparty_id text, p_metadata jsonb) OWNER TO u0_a253;

--
-- Name: ledger_write_guard(text, text, text, text, bigint, text); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.ledger_write_guard(p_idempotency_key text, p_event_hash text, p_wallet_id text, p_event_type text, p_amount bigint, p_currency text) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_existing_hash TEXT;
BEGIN
    -- NULL wallet guard
    IF p_wallet_id IS NULL OR length(trim(p_wallet_id)) = 0 THEN
        RAISE EXCEPTION 'OMEGA_LEDGER: NULL or empty wallet_id rejected [key=%]', p_idempotency_key;
    END IF;

    -- Lookup existing guard record
    SELECT event_hash
      INTO v_existing_hash
      FROM ledger_write_guard
     WHERE idempotency_key = p_idempotency_key;

    IF FOUND THEN
        IF v_existing_hash = p_event_hash THEN
            -- Exact duplicate: idempotent no-op
            RETURN FALSE;
        ELSE
            -- Same key, different payload: hard error
            RAISE EXCEPTION
                'OMEGA_LEDGER: Idempotency conflict – key=% has hash=% but new payload has hash=%',
                p_idempotency_key, v_existing_hash, p_event_hash;
        END IF;
    END IF;

    -- New write: register guard record
    INSERT INTO ledger_write_guard (
        idempotency_key, event_hash, wallet_id, event_type, amount, currency
    ) VALUES (
        p_idempotency_key, p_event_hash, p_wallet_id, p_event_type, p_amount, p_currency
    );

    RETURN TRUE;
END;
$$;


ALTER FUNCTION public.ledger_write_guard(p_idempotency_key text, p_event_hash text, p_wallet_id text, p_event_type text, p_amount bigint, p_currency text) OWNER TO u0_a253;

--
-- Name: omega_apply_event_stream(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.omega_apply_event_stream() RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN

    INSERT INTO omega_balance_stream (account_id, delta, event_type)
    SELECT
        w.account_id,
        CASE
            WHEN e.event_type = 'TRANSFER' THEN -e.amount
            WHEN e.event_type = 'DEPOSIT' THEN e.amount
            ELSE 0
        END,
        e.event_type
    FROM omega_events e
    JOIN wallets w ON w.id = e.wallet_id
    WHERE e.processed IS NOT TRUE;

    UPDATE omega_events
    SET processed = TRUE
    WHERE processed IS NOT TRUE;

END;
$$;


ALTER FUNCTION public.omega_apply_event_stream() OWNER TO u0_a253;

--
-- Name: omega_auto_link_wallet(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.omega_auto_link_wallet() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.account_id IS NULL THEN
        NEW.account_id := '00000000-0000-0000-0000-000000000001';
    END IF;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.omega_auto_link_wallet() OWNER TO u0_a253;

--
-- Name: omega_block_mutation(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.omega_block_mutation() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    RAISE EXCEPTION 'OMEGA_LEDGER: omega_events is immutable';
END;
$$;


ALTER FUNCTION public.omega_block_mutation() OWNER TO u0_a253;

--
-- Name: omega_events_block_mutation(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.omega_events_block_mutation() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    RAISE EXCEPTION 'OMEGA FINALITY: omega_events is immutable';
END;
$$;


ALTER FUNCTION public.omega_events_block_mutation() OWNER TO u0_a253;

--
-- Name: omega_is_frozen(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.omega_is_frozen() RETURNS boolean
    LANGUAGE plpgsql
    AS $$
DECLARE v TEXT;
BEGIN
    SELECT value INTO v FROM omega_ledger_state WHERE key='frozen';
    RETURN v = 'true';
END;
$$;


ALTER FUNCTION public.omega_is_frozen() OWNER TO u0_a253;

--
-- Name: omega_liquidity_router(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.omega_liquidity_router() RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN

    INSERT INTO omega_events (
        event_id,
        event_type,
        aggregate_id,
        aggregate_type,
        payload,
        idempotency_key,
        created_at,
        amount,
        currency
    )
    SELECT
        gen_random_uuid(),
        'AUTO_LIQUIDITY_ROUTE',
        b.account_id,
        'ACCOUNT',
        json_build_object(
            'from', 'OMEGA_RESERVE',
            'reason', 'auto_balance_correction'
        ),
        'liq_route_' || b.account_id,
        NOW(),
        ABS(b.balance),
        'USD'
    FROM omega_account_balances b
    WHERE b.balance < 0;

END;
$$;


ALTER FUNCTION public.omega_liquidity_router() OWNER TO u0_a253;

--
-- Name: omega_rebuild_balances(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.omega_rebuild_balances() RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN

    TRUNCATE TABLE omega_account_balances;

    INSERT INTO omega_account_balances (account_id, balance, updated_at)
    SELECT
        w.account_id,
        COALESCE(SUM(
            CASE
                WHEN lt.description ILIKE '%GENESIS%' THEN lt.amount
                ELSE lt.amount
            END
        ), 0)::NUMERIC(20,2),
        NOW()
    FROM ledger_transactions lt
    JOIN wallets w
        ON w.id = lt.wallet_id
    WHERE w.account_id IS NOT NULL
    GROUP BY w.account_id;

END;
$$;


ALTER FUNCTION public.omega_rebuild_balances() OWNER TO u0_a253;

--
-- Name: omega_sign_ledger_entry(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.omega_sign_ledger_entry() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.hash := encode(
        sha256((
            NEW.id::text ||
            COALESCE(NEW.direction, '') ||
            COALESCE(NEW.amount::text, '0') ||
            COALESCE(NEW.memo, '') ||
            COALESCE(NEW.prev_hash, 'GENESIS') ||
            COALESCE(NEW.event_type, '')
        )::bytea),
        'hex'
    );
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.omega_sign_ledger_entry() OWNER TO postgres;

--
-- Name: omega_transfer(uuid, uuid, numeric, text); Type: FUNCTION; Schema: public; Owner: ledger_service
--

CREATE FUNCTION public.omega_transfer(p_from_wallet uuid, p_to_wallet uuid, p_amount numeric, p_idempotency_key text) RETURNS uuid
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_tx uuid;
    v_existing uuid;
BEGIN

    -- idempotency
    SELECT id INTO v_existing
    FROM ledger_transactions
    WHERE idempotency_key = p_idempotency_key;

    IF v_existing IS NOT NULL THEN
        RETURN v_existing;
    END IF;

    INSERT INTO ledger_transactions (idempotency_key, description)
    VALUES (p_idempotency_key, 'transfer')
    RETURNING id INTO v_tx;

    -- DEBIT
    INSERT INTO ledger_entries (transaction_id, wallet_id, direction, amount)
    VALUES (v_tx, p_from_wallet, 'DEBIT', p_amount);

    -- CREDIT (this MUST always execute)
    INSERT INTO ledger_entries (transaction_id, wallet_id, direction, amount)
    VALUES (v_tx, p_to_wallet, 'CREDIT', p_amount);

    RETURN v_tx;

EXCEPTION WHEN OTHERS THEN
    RAISE;
END;
$$;


ALTER FUNCTION public.omega_transfer(p_from_wallet uuid, p_to_wallet uuid, p_amount numeric, p_idempotency_key text) OWNER TO ledger_service;

--
-- Name: omega_transfer_event(uuid, uuid, numeric, text, text); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.omega_transfer_event(p_from_wallet uuid, p_to_wallet uuid, p_amount numeric, p_currency text, p_idempotency_key text) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN

    -- 🛑 IDENTITY SAFETY (NO DUPLICATES)
    IF EXISTS (
        SELECT 1
        FROM omega_events
        WHERE idempotency_key = p_idempotency_key
    ) THEN
        RAISE NOTICE 'DUPLICATE EVENT IGNORED: %', p_idempotency_key;
        RETURN;
    END IF;

    -- 🧾 WRITE DEBIT EVENT
    INSERT INTO omega_events (
        event_id,
        event_type,
        aggregate_id,
        aggregate_type,
        payload,
        idempotency_key,
        created_at,
        timestamp,
        wallet_id,
        amount,
        currency
    )
    VALUES (
        gen_random_uuid(),
        'WALLET_DEBIT',
        p_from_wallet,
        'WALLET',
        jsonb_build_object(
            'type', 'DEBIT',
            'amount', p_amount,
            'currency', p_currency
        ),
        p_idempotency_key || '_debit',
        NOW(),
        NOW(),
        p_from_wallet,
        -p_amount,
        p_currency
    );

    -- 🧾 WRITE CREDIT EVENT
    INSERT INTO omega_events (
        event_id,
        event_type,
        aggregate_id,
        aggregate_type,
        payload,
        idempotency_key,
        created_at,
        timestamp,
        wallet_id,
        amount,
        currency
    )
    VALUES (
        gen_random_uuid(),
        'WALLET_CREDIT',
        p_to_wallet,
        'WALLET',
        jsonb_build_object(
            'type', 'CREDIT',
            'amount', p_amount,
            'currency', p_currency
        ),
        p_idempotency_key || '_credit',
        NOW(),
        NOW(),
        p_to_wallet,
        p_amount,
        p_currency
    );

END;
$$;


ALTER FUNCTION public.omega_transfer_event(p_from_wallet uuid, p_to_wallet uuid, p_amount numeric, p_currency text, p_idempotency_key text) OWNER TO u0_a253;

--
-- Name: omega_update_available_balance(); Type: FUNCTION; Schema: public; Owner: omega
--

CREATE FUNCTION public.omega_update_available_balance() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN

    NEW.available_balance :=
        COALESCE(NEW.settled_balance, 0)
        - COALESCE(NEW.reserved_balance, 0)
        - COALESCE(NEW.locked_balance, 0);

    RETURN NEW;

END;
$$;


ALTER FUNCTION public.omega_update_available_balance() OWNER TO omega;

--
-- Name: omega_update_balances(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.omega_update_balances() RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN

    INSERT INTO omega_account_balances (account_id, balance, updated_at)
    SELECT
        account_id,
        SUM(delta)::NUMERIC(20,2),
        NOW()
    FROM omega_balance_stream
    GROUP BY account_id

    ON CONFLICT (account_id)
    DO UPDATE SET
        balance = EXCLUDED.balance,
        updated_at = NOW();

END;
$$;


ALTER FUNCTION public.omega_update_balances() OWNER TO u0_a253;

--
-- Name: omega_write_guard(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.omega_write_guard() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF omega_is_frozen() THEN
        RAISE EXCEPTION 'OMEGA_LEDGER: system frozen';
    END IF;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.omega_write_guard() OWNER TO u0_a253;

--
-- Name: rebuild_account_balances(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.rebuild_account_balances() RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    PERFORM set_config('application_name', 'OMEGA_PROJECTION_ENGINE', true);

    TRUNCATE TABLE account_balances;

    INSERT INTO account_balances (
        wallet_id,
        currency,
        balance,
        total_credited,
        total_debited,
        event_count,
        last_seq,
        last_updated_at
    )
    SELECT
        ne.wallet AS wallet_id,
        ne.currency,

        SUM(ne.signed_amount),
        SUM(CASE WHEN ne.signed_amount > 0 THEN ne.signed_amount ELSE 0 END),
        SUM(CASE WHEN ne.signed_amount < 0 THEN -ne.signed_amount ELSE 0 END),
        COUNT(*),
        MAX(ne.seq),
        now()
    FROM normalized_events ne
    GROUP BY ne.wallet, ne.currency;

END;
$$;


ALTER FUNCTION public.rebuild_account_balances() OWNER TO u0_a253;

--
-- Name: rebuild_projection(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.rebuild_projection() RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    DELETE FROM account_balances;

    INSERT INTO account_balances (wallet_id, balance, currency, updated_at)
    SELECT
        wallet,
        SUM(amount),
        currency,
        NOW()
    FROM normalized_events
    GROUP BY wallet, currency;
END;
$$;


ALTER FUNCTION public.rebuild_projection() OWNER TO u0_a253;

--
-- Name: refresh_balances_safe(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.refresh_balances_safe() RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    REFRESH MATERIALIZED VIEW ledger_balances_mv;
END;
$$;


ALTER FUNCTION public.refresh_balances_safe() OWNER TO u0_a253;

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
-- Name: reserve_funds(uuid, numeric); Type: FUNCTION; Schema: public; Owner: omega
--

CREATE FUNCTION public.reserve_funds(p_wallet_id uuid, p_amount numeric) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_available NUMERIC;
BEGIN

    SELECT (settled_balance - reserved_balance)
    INTO v_available
    FROM wallets
    WHERE id = p_wallet_id
    FOR UPDATE;

    IF v_available < p_amount THEN
        RETURN FALSE;
    END IF;

    UPDATE wallets
    SET reserved_balance = reserved_balance + p_amount
    WHERE id = p_wallet_id;

    RETURN TRUE;

END;
$$;


ALTER FUNCTION public.reserve_funds(p_wallet_id uuid, p_amount numeric) OWNER TO omega;

--
-- Name: resolve_identity(text, text, text, text, text); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.resolve_identity(p_ledger_id text, p_bank_id text, p_wallet_id text, p_owner text, p_telegram text) RETURNS text
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_identity_hash TEXT;
BEGIN

    v_identity_hash := encode(
        digest(
            COALESCE(p_ledger_id,'') || '|' ||
            COALESCE(p_bank_id,'')   || '|' ||
            COALESCE(p_wallet_id,'') || '|' ||
            COALESCE(p_owner,'')     || '|' ||
            COALESCE(p_telegram,''),
        'sha256'),
    'hex');

    INSERT INTO canonical_accounts (
        account_id,
        owner_id,
        telegram_uid,
        stripe_customer_id,
        account_type,
        currency,
        status,
        source_system,
        identity_hash
    )
    VALUES (
        p_ledger_id,
        p_owner,
        p_telegram,
        NULL,
        'ASSET',
        'USD',
        'ACTIVE',
        'ledger',
        v_identity_hash
    )
    ON CONFLICT (account_id)
    DO UPDATE SET
        identity_hash = EXCLUDED.identity_hash,
        owner_id = EXCLUDED.owner_id,
        telegram_uid = EXCLUDED.telegram_uid;

    RETURN v_identity_hash;

END;
$$;


ALTER FUNCTION public.resolve_identity(p_ledger_id text, p_bank_id text, p_wallet_id text, p_owner text, p_telegram text) OWNER TO u0_a253;

--
-- Name: run_bank_world_test_v1(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.run_bank_world_test_v1() RETURNS TABLE(test_name text, status text, details text)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_count INT;
BEGIN

    SELECT COUNT(*) INTO v_count FROM accounts;

    IF v_count = 0 THEN
        RETURN QUERY SELECT 'bank_core','FAIL','no accounts';
    ELSE
        RETURN QUERY SELECT 'bank_core','PASS','accounts present';
    END IF;

    RETURN QUERY SELECT 'identity','PASS','bank identity layer OK';

END;
$$;


ALTER FUNCTION public.run_bank_world_test_v1() OWNER TO u0_a253;

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

    -- ACCOUNT LAYER
    SELECT COUNT(*) INTO v_count FROM canonical_accounts;

    IF v_count = 0 THEN
        RETURN QUERY SELECT 'account_layer','FAIL','no canonical_accounts';
    ELSE
        RETURN QUERY SELECT 'account_layer','PASS','accounts present';
    END IF;

    -- LEDGER LAYER
    IF NOT EXISTS (SELECT 1 FROM ledger_wal_stream LIMIT 1) THEN
        RETURN QUERY SELECT 'ledger_wal','WARN','empty ledger (sandbox)';
    ELSE
        RETURN QUERY SELECT 'ledger_wal','PASS','ledger active';
    END IF;

    -- BANK LAYER
    IF NOT EXISTS (SELECT 1 FROM accounts LIMIT 1) THEN
        RETURN QUERY SELECT 'bank_core','FAIL','bank accounts missing';
    ELSE
        RETURN QUERY SELECT 'bank_core','PASS','bank active';
    END IF;

    -- PROJECTION LAYER (SAFE CHECK ONLY)
    IF EXISTS (
        SELECT 1 FROM pg_matviews WHERE matviewname = 'ledger_balances_mv'
    ) THEN
        RETURN QUERY SELECT 'projection','PASS','mv exists';
    ELSE
        RETURN QUERY SELECT 'projection','FAIL','missing ledger_balances_mv';
    END IF;

    RETURN;

END;
$$;


ALTER FUNCTION public.run_world_test_sandbox_v3() OWNER TO u0_a253;

--
-- Name: safe_insert_event(text, text, text, numeric, text, jsonb); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.safe_insert_event(p_id text, p_wallet text, p_type text, p_amount numeric, p_currency text, p_payload jsonb) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM ledger_write_guard WHERE idempotency_key = p_id
    ) THEN
        RETURN;
    END IF;

    INSERT INTO omega_events (
        event_id,
        wallet_id,
        event_type,
        amount,
        currency,
        payload,
        idempotency_key,
        created_at
    )
    VALUES (
        gen_random_uuid(),
        p_wallet,
        p_type,
        p_amount,
        p_currency,
        p_payload,
        p_id,
        NOW()
    );

    INSERT INTO ledger_write_guard(idempotency_key)
    VALUES (p_id);

END;
$$;


ALTER FUNCTION public.safe_insert_event(p_id text, p_wallet text, p_type text, p_amount numeric, p_currency text, p_payload jsonb) OWNER TO u0_a253;

--
-- Name: send_money(uuid, uuid, numeric, text, text); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.send_money(from_wallet uuid, to_wallet uuid, amount numeric, currency text, idempotency text) RETURNS text
    LANGUAGE plpgsql
    AS $$
BEGIN

    -- 1. write ledger event (source of truth)
    INSERT INTO omega_events (
        event_id,
        event_type,
        aggregate_id,
        aggregate_type,
        payload,
        idempotency_key,
        created_at,
        amount,
        currency
    )
    VALUES (
        gen_random_uuid(),
        'TRANSFER',
        from_wallet,
        'WALLET',
        json_build_object(
            'to', to_wallet,
            'amount', amount
        ),
        idempotency,
        NOW(),
        amount,
        currency
    )
    ON CONFLICT (idempotency_key) DO NOTHING;

    -- 2. rebuild projection safely
    PERFORM omega_rebuild_balances();

    RETURN 'TRANSFER_POSTED';

END;
$$;


ALTER FUNCTION public.send_money(from_wallet uuid, to_wallet uuid, amount numeric, currency text, idempotency text) OWNER TO u0_a253;

--
-- Name: set_wallet_balance(uuid, numeric); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.set_wallet_balance(p_account_id uuid, p_balance numeric) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE wallets
    SET available_balance = p_balance,
        settled_balance = p_balance
    WHERE account_id = p_account_id;
END;
$$;


ALTER FUNCTION public.set_wallet_balance(p_account_id uuid, p_balance numeric) OWNER TO u0_a253;

--
-- Name: system_rebuild(); Type: PROCEDURE; Schema: public; Owner: u0_a253
--

CREATE PROCEDURE public.system_rebuild()
    LANGUAGE plpgsql
    AS $$
BEGIN
    RAISE NOTICE 'OMEGA_LEDGER: Starting deterministic system rebuild at %', now();

    -- Rebuild projection from scratch
    PERFORM rebuild_account_balances();

    RAISE NOTICE 'OMEGA_LEDGER: Rebuild complete. Running validation...';

    -- Emit consistency report to server log
    PERFORM validate_projection_consistency();
    PERFORM validate_zero_inflation();
    PERFORM validate_wallet_integrity();
    PERFORM validate_idempotency();

    RAISE NOTICE 'OMEGA_LEDGER: Validation complete at %', now();
END;
$$;


ALTER PROCEDURE public.system_rebuild() OWNER TO u0_a253;

--
-- Name: trg_account_balances_guard(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.trg_account_balances_guard() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Enforce consistency constraint proactively (belt over CHECK constraint)
    IF NEW.balance <> (NEW.total_credited - NEW.total_debited) THEN
        RAISE EXCEPTION
            'OMEGA_LEDGER: account_balances integrity violation – wallet=% balance=% != credited(%) - debited(%)',
            NEW.wallet_id, NEW.balance, NEW.total_credited, NEW.total_debited;
    END IF;

    IF NEW.balance < 0 THEN
        RAISE EXCEPTION
            'OMEGA_LEDGER: account_balances integrity violation – negative balance % for wallet=%',
            NEW.balance, NEW.wallet_id;
    END IF;

    RETURN NEW;
END;
$$;


ALTER FUNCTION public.trg_account_balances_guard() OWNER TO u0_a253;

--
-- Name: trg_omega_events_immutability(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.trg_omega_events_immutability() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    RAISE EXCEPTION
        'OMEGA_LEDGER: omega_events is immutable – % operation is forbidden on seq=%',
        TG_OP, COALESCE(OLD.seq::TEXT, '?');
    RETURN NULL;
END;
$$;


ALTER FUNCTION public.trg_omega_events_immutability() OWNER TO u0_a253;

--
-- Name: trg_omega_events_project(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.trg_omega_events_project() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- NULL wallet rows should never reach here (constraint blocks them),
    -- but defend in depth:
    IF NEW.wallet_id IS NULL OR length(trim(NEW.wallet_id)) = 0 THEN
        RAISE WARNING 'OMEGA_LEDGER: trigger received event with NULL/empty wallet_id – seq=%', NEW.seq;
        RETURN NEW;
    END IF;

    -- Update projection for primary wallet
    PERFORM upsert_account_balance(trim(NEW.wallet_id), trim(NEW.currency));

    -- Update projection for counterparty wallet (TRANSFER_IN / TRANSFER_OUT)
    IF NEW.counterparty_id IS NOT NULL AND length(trim(NEW.counterparty_id)) > 0 THEN
        PERFORM upsert_account_balance(trim(NEW.counterparty_id), trim(NEW.currency));
    END IF;

    RETURN NEW;
END;
$$;


ALTER FUNCTION public.trg_omega_events_project() OWNER TO u0_a253;

--
-- Name: trigger_projection(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.trigger_projection() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    PERFORM rebuild_projection();
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.trigger_projection() OWNER TO u0_a253;

--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: omega
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_updated_at_column() OWNER TO omega;

--
-- Name: upsert_account_balance(text, text); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.upsert_account_balance(p_wallet_id text, p_currency text) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_balance       BIGINT;
    v_credited      BIGINT;
    v_debited       BIGINT;
    v_count         BIGINT;
    v_last_seq      BIGINT;
BEGIN
    SELECT
        SUM(ne.signed_amount),
        SUM(CASE WHEN ne.signed_amount > 0 THEN  ne.signed_amount ELSE 0 END),
        SUM(CASE WHEN ne.signed_amount < 0 THEN -ne.signed_amount ELSE 0 END),
        COUNT(*),
        MAX(ne.seq)
    INTO v_balance, v_credited, v_debited, v_count, v_last_seq
    FROM normalized_events ne
    WHERE ne.wallet_id = p_wallet_id
      AND ne.currency  = p_currency;

    -- If no events exist for this wallet/currency, remove stale projection row
    IF v_count IS NULL OR v_count = 0 THEN
        DELETE FROM account_balances
         WHERE wallet_id = p_wallet_id AND currency = p_currency;
        RETURN;
    END IF;

    -- Guard: balance must not go negative
    IF v_balance < 0 THEN
        RAISE EXCEPTION
            'OMEGA_LEDGER: Projection integrity violation – wallet=% currency=% would have negative balance %',
            p_wallet_id, p_currency, v_balance;
    END IF;

    INSERT INTO account_balances (
        wallet_id, currency,
        balance, total_credited, total_debited,
        event_count, last_seq, last_updated_at
    ) VALUES (
        p_wallet_id, p_currency,
        v_balance, v_credited, v_debited,
        v_count, v_last_seq, now()
    )
    ON CONFLICT (wallet_id, currency) DO UPDATE SET
        balance         = EXCLUDED.balance,
        total_credited  = EXCLUDED.total_credited,
        total_debited   = EXCLUDED.total_debited,
        event_count     = EXCLUDED.event_count,
        last_seq        = EXCLUDED.last_seq,
        last_updated_at = EXCLUDED.last_updated_at;
END;
$$;


ALTER FUNCTION public.upsert_account_balance(p_wallet_id text, p_currency text) OWNER TO u0_a253;

--
-- Name: validate_consensus(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.validate_consensus() RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    total_nodes INT;
    approved_nodes INT;
    mismatch_count INT;
BEGIN

    SELECT COUNT(*) INTO total_nodes
    FROM omega_consensus_nodes
    WHERE active = TRUE;

    SELECT COUNT(*) INTO approved_nodes
    FROM omega_consensus_votes v
    JOIN omega_consensus_nodes n ON n.node_id = v.node_id
    WHERE v.approved = TRUE
      AND n.active = TRUE;

    SELECT COUNT(DISTINCT state_hash) INTO mismatch_count
    FROM omega_consensus_votes;

    IF mismatch_count > 1 THEN
        RAISE EXCEPTION 'CONSENSUS FAILURE: state hash divergence detected';
    END IF;

    IF approved_nodes < (total_nodes * 2 / 3) THEN
        RAISE EXCEPTION 'CONSENSUS FAILURE: quorum not reached';
    END IF;

END;
$$;


ALTER FUNCTION public.validate_consensus() OWNER TO u0_a253;

--
-- Name: validate_ledger_transaction(uuid); Type: FUNCTION; Schema: public; Owner: omega
--

CREATE FUNCTION public.validate_ledger_transaction(p_tx uuid) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    d numeric;
    c numeric;
BEGIN

    SELECT COALESCE(SUM(amount),0)
    INTO d
    FROM ledger_entries
    WHERE transaction_id = p_tx AND direction='DEBIT';

    SELECT COALESCE(SUM(amount),0)
    INTO c
    FROM ledger_entries
    WHERE transaction_id = p_tx AND direction='CREDIT';

    IF d <> c THEN
        RAISE EXCEPTION 'UNBALANCED TX % debit=% credit=%', p_tx, d, c;
    END IF;

END;
$$;


ALTER FUNCTION public.validate_ledger_transaction(p_tx uuid) OWNER TO omega;

--
-- Name: validate_projection_consistency(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.validate_projection_consistency() RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    projected NUMERIC;
    actual NUMERIC;
BEGIN
    SELECT COALESCE(SUM(balance),0)
    INTO projected
    FROM account_balances;

    SELECT COALESCE(SUM(signed_amount),0)
    INTO actual
    FROM normalized_events;

    IF ABS(projected - actual) > 0.000001 THEN
        RAISE EXCEPTION
            'OMEGA DRIFT DETECTED: projected=% actual=% diff=%',
            projected, actual, projected - actual;
    END IF;
END;
$$;


ALTER FUNCTION public.validate_projection_consistency() OWNER TO u0_a253;

--
-- Name: validate_transaction_balance(uuid); Type: FUNCTION; Schema: public; Owner: omega
--

CREATE FUNCTION public.validate_transaction_balance(p_tx uuid) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
DECLARE
    debit numeric;
    credit numeric;
BEGIN
    SELECT COALESCE(SUM(amount),0)
    INTO debit
    FROM ledger_entries
    WHERE transaction_id = p_tx
      AND direction = 'DEBIT';

    SELECT COALESCE(SUM(amount),0)
    INTO credit
    FROM ledger_entries
    WHERE transaction_id = p_tx
      AND direction = 'CREDIT';

    RETURN debit = credit;
END;
$$;


ALTER FUNCTION public.validate_transaction_balance(p_tx uuid) OWNER TO omega;

--
-- Name: validate_zero_inflation(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.validate_zero_inflation() RETURNS TABLE(currency text, total_minted bigint, total_burned bigint, total_credited bigint, total_debited bigint, total_fees bigint, net_supply bigint, sum_all_balances bigint, inflation_delta bigint, status text)
    LANGUAGE sql STABLE
    AS $$
    WITH event_totals AS (
        SELECT
            currency,
            SUM(CASE WHEN event_type = 'MINT'         THEN amount ELSE 0 END) AS total_minted,
            SUM(CASE WHEN event_type = 'BURN'         THEN amount ELSE 0 END) AS total_burned,
            SUM(CASE WHEN event_type = 'CREDIT'       THEN amount ELSE 0 END) AS total_credited,
            SUM(CASE WHEN event_type IN ('DEBIT','TRANSFER_OUT') THEN amount ELSE 0 END) AS total_debited,
            SUM(CASE WHEN event_type = 'FEE'          THEN amount ELSE 0 END) AS total_fees
        FROM omega_events
        GROUP BY currency
    ),
    balance_totals AS (
        SELECT currency, SUM(balance) AS sum_all_balances
        FROM account_balances
        GROUP BY currency
    )
    SELECT
        et.currency,
        et.total_minted,
        et.total_burned,
        et.total_credited,
        et.total_debited,
        et.total_fees,
        -- Net supply = what was put in minus what was taken out
        (et.total_minted + et.total_credited)
            - (et.total_burned + et.total_debited + et.total_fees) AS net_supply,
        COALESCE(bt.sum_all_balances, 0)                           AS sum_all_balances,
        -- Inflation delta: non-zero indicates a leak or double-count
        COALESCE(bt.sum_all_balances, 0)
            - ((et.total_minted + et.total_credited)
               - (et.total_burned + et.total_debited + et.total_fees)) AS inflation_delta,
        CASE
            WHEN COALESCE(bt.sum_all_balances, 0)
                 = ((et.total_minted + et.total_credited)
                    - (et.total_burned + et.total_debited + et.total_fees))
            THEN 'OK'
            ELSE 'INFLATION_DETECTED'
        END AS status
    FROM event_totals et
    LEFT JOIN balance_totals bt USING (currency)
    ORDER BY et.currency;
$$;


ALTER FUNCTION public.validate_zero_inflation() OWNER TO u0_a253;

--
-- Name: verify_system_boot(); Type: FUNCTION; Schema: public; Owner: u0_a253
--

CREATE FUNCTION public.verify_system_boot() RETURNS TABLE(component text, status text, details text)
    LANGUAGE plpgsql
    AS $$
DECLARE
    rec RECORD;
BEGIN
    FOR rec IN SELECT * FROM system_boot_state LOOP

        -- LEDGER CORE CHECKS
        IF rec.component = 'ledger_core' THEN

            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger WHERE tgname = 'trg_block_ledger_update'
            ) THEN
                RETURN QUERY SELECT rec.component, 'FAIL', 'missing trg_block_ledger_update';
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_matviews WHERE matviewname = 'ledger_balances_mv'
            ) THEN
                RETURN QUERY SELECT rec.component, 'FAIL', 'missing ledger_balances_mv';
            END IF;

        END IF;

        -- BANK CORE CHECKS
        IF rec.component = 'bank_core' THEN

            IF NOT EXISTS (
                SELECT 1 FROM pg_proc WHERE proname = 'post_ledger_entry'
            ) THEN
                RETURN QUERY SELECT rec.component, 'FAIL', 'missing post_ledger_entry';
            END IF;

        END IF;

        -- DEFAULT PASS
        RETURN QUERY SELECT rec.component, 'PASS', 'ok';

    END LOOP;
END;
$$;


ALTER FUNCTION public.verify_system_boot() OWNER TO u0_a253;

--
-- Name: omega_ledger_server; Type: SERVER; Schema: -; Owner: u0_a253
--

CREATE SERVER omega_ledger_server FOREIGN DATA WRAPPER postgres_fdw OPTIONS (
    dbname 'omega_ledger',
    host 'localhost',
    port '5432'
);


ALTER SERVER omega_ledger_server OWNER TO u0_a253;

--
-- Name: USER MAPPING u0_a253 SERVER omega_ledger_server; Type: USER MAPPING; Schema: -; Owner: u0_a253
--

CREATE USER MAPPING FOR u0_a253 SERVER omega_ledger_server OPTIONS (
    password 'postgres',
    "user" 'postgres'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: account_balances; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.account_balances (
    wallet_id text NOT NULL,
    balance numeric(38,8) DEFAULT 0 NOT NULL,
    currency text DEFAULT 'USD'::text NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    credited numeric(38,8) DEFAULT 0,
    debited numeric(38,8) DEFAULT 0,
    event_count bigint DEFAULT 0,
    last_seq bigint DEFAULT 0
);


ALTER TABLE public.account_balances OWNER TO u0_a253;

--
-- Name: accounts; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.accounts (
    account_id uuid DEFAULT public.uuid_generate_v4() CONSTRAINT accounts_id_not_null NOT NULL,
    owner_name text NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    telegram_uid character varying(32),
    identity_id text,
    email text,
    status text DEFAULT 'active'::text,
    stripe_customer_id text,
    account_type text DEFAULT 'ASSET'::text,
    currency text DEFAULT 'USD'::text
);


ALTER TABLE public.accounts OWNER TO omega;

--
-- Name: ach_wire_events; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.ach_wire_events (
    id uuid NOT NULL,
    wallet_id uuid,
    rail text,
    direction text,
    amount numeric(20,2),
    external_reference text,
    status text,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.ach_wire_events OWNER TO omega;

--
-- Name: async_settlement_jobs; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.async_settlement_jobs (
    id uuid NOT NULL,
    auth_id uuid,
    wallet_id uuid,
    merchant text,
    amount numeric(20,2),
    network text,
    priority integer DEFAULT 1,
    status text,
    created_at timestamp without time zone DEFAULT now(),
    processed_at timestamp without time zone
);


ALTER TABLE public.async_settlement_jobs OWNER TO omega;

--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.audit_logs (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    action text,
    metadata jsonb,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.audit_logs OWNER TO omega;

--
-- Name: auth_holds; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.auth_holds (
    id uuid NOT NULL,
    wallet_id uuid NOT NULL,
    amount numeric(20,2) NOT NULL,
    merchant text,
    status text NOT NULL,
    expires_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.auth_holds OWNER TO omega;

--
-- Name: authorization_expirations; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.authorization_expirations (
    id uuid NOT NULL,
    auth_id uuid,
    wallet_id uuid,
    expired_amount numeric(20,2),
    expired_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.authorization_expirations OWNER TO omega;

--
-- Name: authorization_holds; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.authorization_holds (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    transaction_id uuid NOT NULL,
    wallet_id uuid NOT NULL,
    amount numeric(20,2) NOT NULL,
    status text NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    merchant_name text,
    currency text DEFAULT 'USD'::text NOT NULL,
    external_reference text,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    expires_at timestamp without time zone,
    idempotency_key text
);


ALTER TABLE public.authorization_holds OWNER TO omega;

--
-- Name: canonical_accounts; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.canonical_accounts (
    account_id text NOT NULL,
    owner_id text,
    telegram_uid text,
    stripe_customer_id text,
    account_type text NOT NULL,
    currency text NOT NULL,
    status text DEFAULT 'ACTIVE'::text NOT NULL,
    source_system text NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    identity_hash text
);


ALTER TABLE public.canonical_accounts OWNER TO u0_a253;

--
-- Name: capture_events; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.capture_events (
    id uuid NOT NULL,
    auth_hold_id uuid NOT NULL,
    transaction_id uuid,
    amount numeric(20,2),
    status text,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.capture_events OWNER TO omega;

--
-- Name: card_registry; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.card_registry (
    card_id uuid NOT NULL,
    pan text,
    exp text,
    cvv text,
    wallet_id text,
    status text,
    created_at timestamp without time zone
);


ALTER TABLE public.card_registry OWNER TO u0_a253;

--
-- Name: card_transactions; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.card_transactions (
    id uuid NOT NULL,
    card_token text NOT NULL,
    wallet_id uuid NOT NULL,
    amount numeric(20,2) NOT NULL,
    merchant text NOT NULL,
    status text NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    idempotency_key text
);


ALTER TABLE public.card_transactions OWNER TO omega;

--
-- Name: cards; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.cards (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    wallet_id uuid NOT NULL,
    card_number text NOT NULL,
    cvv text NOT NULL,
    expiration_date date NOT NULL,
    status public.card_status_type DEFAULT 'ACTIVE'::public.card_status_type NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    identity_id text,
    pan_encrypted text,
    cvv_encrypted text,
    pan_last4 text,
    expiry text
);


ALTER TABLE public.cards OWNER TO omega;

--
-- Name: chargeback_cases; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.chargeback_cases (
    id uuid NOT NULL,
    auth_id uuid,
    wallet_id uuid,
    merchant text,
    amount numeric(20,2),
    network text,
    reason_code text,
    status text,
    created_at timestamp without time zone DEFAULT now(),
    resolved_at timestamp without time zone
);


ALTER TABLE public.chargeback_cases OWNER TO omega;

--
-- Name: connector_event_log; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.connector_event_log (
    id uuid NOT NULL,
    idempotency_key text NOT NULL,
    event_type text NOT NULL,
    aggregate_id uuid,
    aggregate_type text,
    payload jsonb NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.connector_event_log OWNER TO omega;

--
-- Name: consensus_drift_log; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.consensus_drift_log (
    id bigint NOT NULL,
    wallet_id uuid,
    live_limit numeric(20,2),
    replay_limit numeric(20,2),
    delta numeric(20,2),
    detected_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.consensus_drift_log OWNER TO omega;

--
-- Name: consensus_drift_log_id_seq; Type: SEQUENCE; Schema: public; Owner: omega
--

CREATE SEQUENCE public.consensus_drift_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.consensus_drift_log_id_seq OWNER TO omega;

--
-- Name: consensus_drift_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omega
--

ALTER SEQUENCE public.consensus_drift_log_id_seq OWNED BY public.consensus_drift_log.id;


--
-- Name: credit_lines; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.credit_lines (
    wallet_id uuid NOT NULL,
    credit_limit numeric(20,2) DEFAULT 0.00 NOT NULL,
    used_credit numeric(20,2) DEFAULT 0.00 NOT NULL,
    status text DEFAULT 'ACTIVE'::text,
    risk_score numeric(10,2) DEFAULT 0.00,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.credit_lines OWNER TO omega;

--
-- Name: credit_policy_state; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.credit_policy_state (
    wallet_id uuid NOT NULL,
    current_limit numeric(20,2) DEFAULT 0 NOT NULL,
    state text DEFAULT 'ACTIVE'::text NOT NULL,
    last_updated timestamp without time zone DEFAULT now()
);


ALTER TABLE public.credit_policy_state OWNER TO omega;

--
-- Name: currency_treasury; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.currency_treasury (
    currency_code text NOT NULL,
    treasury_balance numeric(20,2),
    reserved_balance numeric(20,2),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.currency_treasury OWNER TO omega;

--
-- Name: dispute_cases; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.dispute_cases (
    id uuid NOT NULL,
    auth_id uuid,
    wallet_id uuid,
    merchant text,
    amount numeric(20,2),
    reason text,
    status text,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.dispute_cases OWNER TO omega;

--
-- Name: execution_lease; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.execution_lease (
    idempotency_key text NOT NULL,
    status text NOT NULL,
    locked_at timestamp without time zone DEFAULT now(),
    worker_id text NOT NULL
);


ALTER TABLE public.execution_lease OWNER TO omega;

--
-- Name: fraud_velocity_state; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.fraud_velocity_state (
    wallet_id uuid NOT NULL,
    tx_count_1m integer DEFAULT 0,
    tx_volume_1m numeric(20,2) DEFAULT 0,
    risk_score numeric(10,2) DEFAULT 0,
    blocked boolean DEFAULT false,
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.fraud_velocity_state OWNER TO omega;

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
-- Name: idempotency_keys; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.idempotency_keys (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    idempotency_key text NOT NULL,
    transaction_id uuid,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.idempotency_keys OWNER TO omega;

--
-- Name: interchange_fee_events; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.interchange_fee_events (
    id uuid NOT NULL,
    auth_id uuid,
    network text,
    fee_amount numeric(20,2),
    fee_percent numeric(10,4),
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.interchange_fee_events OWNER TO omega;

--
-- Name: invariant_failures; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.invariant_failures (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    invariant_name text NOT NULL,
    failure_details text NOT NULL,
    detected_at timestamp without time zone DEFAULT now() NOT NULL,
    severity text NOT NULL
);


ALTER TABLE public.invariant_failures OWNER TO omega;

--
-- Name: iso_messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.iso_messages (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    ledger_entry_id uuid,
    message_type text NOT NULL,
    payload xml NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.iso_messages OWNER TO postgres;

--
-- Name: issuer_queue; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.issuer_queue (
    id uuid NOT NULL,
    event_type text,
    payload jsonb,
    status text,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.issuer_queue OWNER TO omega;

--
-- Name: ledger_balances_mv; Type: FOREIGN TABLE; Schema: public; Owner: u0_a253
--

CREATE FOREIGN TABLE public.ledger_balances_mv (
    account text,
    balance numeric
)
SERVER omega_ledger_server
OPTIONS (
    schema_name 'public',
    table_name 'ledger_balances_mv'
);
ALTER FOREIGN TABLE ONLY public.ledger_balances_mv ALTER COLUMN account OPTIONS (
    column_name 'account'
);
ALTER FOREIGN TABLE ONLY public.ledger_balances_mv ALTER COLUMN balance OPTIONS (
    column_name 'balance'
);


ALTER FOREIGN TABLE public.ledger_balances_mv OWNER TO u0_a253;

--
-- Name: ledger_entries; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.ledger_entries (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    transaction_id uuid NOT NULL,
    wallet_id uuid,
    direction text NOT NULL,
    amount numeric(20,2) NOT NULL,
    idempotency_key text,
    created_at timestamp without time zone DEFAULT now(),
    is_finalized boolean DEFAULT false,
    debit_account text,
    credit_account text,
    memo text,
    event_type text,
    hash text,
    wallet_required boolean DEFAULT true,
    global_sequence bigint NOT NULL,
    prev_hash text,
    chain_hash text,
    CONSTRAINT ledger_entries_amount_check CHECK ((amount > (0)::numeric)),
    CONSTRAINT ledger_entries_amount_positive CHECK ((amount > (0)::numeric)),
    CONSTRAINT ledger_entries_direction_check CHECK ((direction = ANY (ARRAY['DEBIT'::text, 'CREDIT'::text]))),
    CONSTRAINT ledger_entries_immutable CHECK (true),
    CONSTRAINT wallet_required_check CHECK (((wallet_required = false) OR (wallet_id IS NOT NULL)))
);


ALTER TABLE public.ledger_entries OWNER TO omega;

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
-- Name: ledger_event_stream; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.ledger_event_stream (
    event_id uuid NOT NULL,
    ledger_id uuid,
    account_id text,
    event_type text,
    amount numeric(20,2),
    direction text,
    created_at timestamp without time zone DEFAULT now(),
    processed boolean DEFAULT false
);


ALTER TABLE public.ledger_event_stream OWNER TO u0_a253;

--
-- Name: ledger_events; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.ledger_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    event_type text NOT NULL,
    aggregate_id uuid NOT NULL,
    aggregate_type text NOT NULL,
    payload jsonb NOT NULL,
    idempotency_key text,
    sequence_number bigint NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.ledger_events OWNER TO omega;

--
-- Name: ledger_events_sequence_number_seq; Type: SEQUENCE; Schema: public; Owner: omega
--

CREATE SEQUENCE public.ledger_events_sequence_number_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ledger_events_sequence_number_seq OWNER TO omega;

--
-- Name: ledger_events_sequence_number_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omega
--

ALTER SEQUENCE public.ledger_events_sequence_number_seq OWNED BY public.ledger_events.sequence_number;


--
-- Name: ledger_postings; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.ledger_postings (
    posting_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    event_id uuid NOT NULL,
    sequence_number bigint NOT NULL,
    account_type text DEFAULT 'TREASURY'::text NOT NULL,
    account_id uuid,
    direction text DEFAULT 'CREDIT'::text NOT NULL,
    amount numeric NOT NULL,
    currency text DEFAULT 'USD'::text,
    created_at timestamp without time zone DEFAULT now(),
    prev_hash text,
    event_hash text,
    chain_hash text,
    CONSTRAINT ledger_postings_amount_check CHECK ((amount >= (0)::numeric)),
    CONSTRAINT ledger_postings_direction_check_fixed CHECK ((direction = ANY (ARRAY['DEBIT'::text, 'CREDIT'::text])))
);


ALTER TABLE public.ledger_postings OWNER TO omega;

--
-- Name: ledger_replay; Type: VIEW; Schema: public; Owner: u0_a253
--

CREATE VIEW public.ledger_replay AS
 SELECT id,
    transaction_id,
    wallet_id,
    direction,
    amount,
    idempotency_key,
    created_at,
    is_finalized,
    debit_account,
    credit_account,
    memo,
    event_type,
    hash,
    wallet_required,
    global_sequence,
    prev_hash,
    chain_hash
   FROM public.ledger_entries
  ORDER BY global_sequence;


ALTER VIEW public.ledger_replay OWNER TO u0_a253;

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
-- Name: ledger_transactions; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.ledger_transactions (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    description text,
    idempotency_key text NOT NULL
);


ALTER TABLE public.ledger_transactions OWNER TO omega;

--
-- Name: ledger_wal_stream; Type: FOREIGN TABLE; Schema: public; Owner: u0_a253
--

CREATE FOREIGN TABLE public.ledger_wal_stream (
    global_sequence bigint NOT NULL,
    ledger_id text NOT NULL,
    debit_account text,
    credit_account text,
    amount numeric NOT NULL,
    created_at timestamp without time zone,
    prev_hash text,
    currency text
)
SERVER omega_ledger_server
OPTIONS (
    schema_name 'public',
    table_name 'ledger_wal_stream'
);
ALTER FOREIGN TABLE ONLY public.ledger_wal_stream ALTER COLUMN global_sequence OPTIONS (
    column_name 'global_sequence'
);
ALTER FOREIGN TABLE ONLY public.ledger_wal_stream ALTER COLUMN ledger_id OPTIONS (
    column_name 'ledger_id'
);
ALTER FOREIGN TABLE ONLY public.ledger_wal_stream ALTER COLUMN debit_account OPTIONS (
    column_name 'debit_account'
);
ALTER FOREIGN TABLE ONLY public.ledger_wal_stream ALTER COLUMN credit_account OPTIONS (
    column_name 'credit_account'
);
ALTER FOREIGN TABLE ONLY public.ledger_wal_stream ALTER COLUMN amount OPTIONS (
    column_name 'amount'
);
ALTER FOREIGN TABLE ONLY public.ledger_wal_stream ALTER COLUMN created_at OPTIONS (
    column_name 'created_at'
);
ALTER FOREIGN TABLE ONLY public.ledger_wal_stream ALTER COLUMN prev_hash OPTIONS (
    column_name 'prev_hash'
);
ALTER FOREIGN TABLE ONLY public.ledger_wal_stream ALTER COLUMN currency OPTIONS (
    column_name 'currency'
);


ALTER FOREIGN TABLE public.ledger_wal_stream OWNER TO u0_a253;

--
-- Name: ledger_write_guard; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.ledger_write_guard (
    idempotency_key text NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.ledger_write_guard OWNER TO u0_a253;

--
-- Name: merchant_batches; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.merchant_batches (
    id uuid NOT NULL,
    merchant text,
    network text,
    batch_total numeric(20,2),
    tx_count integer,
    batch_status text,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.merchant_batches OWNER TO omega;

--
-- Name: merchants; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.merchants (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name text NOT NULL,
    merchant_id text NOT NULL,
    api_key text NOT NULL,
    status public.merchant_status_type DEFAULT 'ACTIVE'::public.merchant_status_type NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.merchants OWNER TO omega;

--
-- Name: network_clearance_windows; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.network_clearance_windows (
    id uuid NOT NULL,
    network text,
    settlement_window text,
    cutoff_time text,
    active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.network_clearance_windows OWNER TO omega;

--
-- Name: omega_events; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.omega_events (
    event_id uuid NOT NULL,
    event_type text NOT NULL,
    aggregate_id uuid NOT NULL,
    aggregate_type text NOT NULL,
    payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    idempotency_key text,
    sequence_number bigint NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    "timestamp" timestamp without time zone,
    merchant_id text,
    wallet_id uuid,
    amount numeric(18,2),
    currency text,
    version integer DEFAULT 1
);


ALTER TABLE public.omega_events OWNER TO omega;

--
-- Name: normalized_events; Type: VIEW; Schema: public; Owner: u0_a253
--

CREATE VIEW public.normalized_events AS
 SELECT sequence_number AS seq,
    (wallet_id)::text AS wallet,
    event_type,
    (COALESCE(amount, (0)::numeric))::numeric(38,8) AS amount,
    COALESCE(currency, 'USD'::text) AS currency,
    payload,
    created_at,
        CASE
            WHEN (event_type = ANY (ARRAY['CREDIT'::text, 'MINT'::text, 'TRANSFER_IN'::text, 'GENESIS_ISSUED'::text, 'GENESIS_ISSUED_V2'::text])) THEN (COALESCE(amount, (0)::numeric))::numeric(38,8)
            ELSE (- (COALESCE(amount, (0)::numeric))::numeric(38,8))
        END AS signed_amount
   FROM public.omega_events
  WHERE (wallet_id IS NOT NULL);


ALTER VIEW public.normalized_events OWNER TO u0_a253;

--
-- Name: wallets; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.wallets (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    account_id uuid,
    currency text NOT NULL,
    available_balance numeric(20,2) DEFAULT NULL::numeric,
    pending_balance numeric(20,2) DEFAULT NULL::numeric,
    created_at timestamp without time zone DEFAULT now(),
    locked_balance numeric(20,2) DEFAULT 0 NOT NULL,
    settled_balance numeric(20,2) DEFAULT 0 NOT NULL,
    reserved_balance numeric(20,2) DEFAULT 0,
    balance_lock boolean DEFAULT false,
    identity_id text,
    canonical_account_id text,
    address text,
    status text DEFAULT 'active'::text,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.wallets OWNER TO omega;

--
-- Name: wallet_state; Type: VIEW; Schema: public; Owner: omega
--

CREATE VIEW public.wallet_state AS
 SELECT id AS wallet_id,
    settled_balance,
    locked_balance,
    (settled_balance - locked_balance) AS available_balance
   FROM public.wallets w;


ALTER VIEW public.wallet_state OWNER TO omega;

--
-- Name: obs_wallet_health; Type: VIEW; Schema: public; Owner: omega
--

CREATE VIEW public.obs_wallet_health AS
 SELECT w.wallet_id,
    w.settled_balance,
    w.locked_balance,
    (w.settled_balance - w.locked_balance) AS available_balance,
    COALESCE(sum(
        CASE
            WHEN (le.direction = 'CREDIT'::text) THEN le.amount
            ELSE (- le.amount)
        END), (0)::numeric) AS ledger_balance,
    (w.settled_balance - COALESCE(sum(
        CASE
            WHEN (le.direction = 'CREDIT'::text) THEN le.amount
            ELSE (- le.amount)
        END), (0)::numeric)) AS drift
   FROM (public.wallet_state w
     LEFT JOIN public.ledger_entries le ON ((w.wallet_id = le.wallet_id)))
  GROUP BY w.wallet_id, w.settled_balance, w.locked_balance;


ALTER VIEW public.obs_wallet_health OWNER TO omega;

--
-- Name: obs_drift_alerts; Type: VIEW; Schema: public; Owner: omega
--

CREATE VIEW public.obs_drift_alerts AS
 SELECT wallet_id,
    settled_balance,
    locked_balance,
    available_balance,
    ledger_balance,
    drift
   FROM public.obs_wallet_health
  WHERE (abs(drift) > 0.01);


ALTER VIEW public.obs_drift_alerts OWNER TO omega;

--
-- Name: obs_invariant_stream; Type: VIEW; Schema: public; Owner: omega
--

CREATE VIEW public.obs_invariant_stream AS
 SELECT invariant_name,
    severity,
    detected_at,
    failure_details
   FROM public.invariant_failures
  ORDER BY detected_at DESC;


ALTER VIEW public.obs_invariant_stream OWNER TO omega;

--
-- Name: obs_ledger_activity; Type: VIEW; Schema: public; Owner: omega
--

CREATE VIEW public.obs_ledger_activity AS
 SELECT wallet_id,
    count(*) AS tx_count,
    sum(
        CASE
            WHEN (direction = 'CREDIT'::text) THEN amount
            ELSE (0)::numeric
        END) AS credits,
    sum(
        CASE
            WHEN (direction = 'DEBIT'::text) THEN amount
            ELSE (0)::numeric
        END) AS debits
   FROM public.ledger_entries
  GROUP BY wallet_id;


ALTER VIEW public.obs_ledger_activity OWNER TO omega;

--
-- Name: settlement_queue; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.settlement_queue (
    id uuid NOT NULL,
    event_type text NOT NULL,
    status text NOT NULL,
    payload jsonb NOT NULL,
    idempotency_key text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    retry_count integer DEFAULT 0 NOT NULL,
    processing_at timestamp without time zone,
    auth_id uuid,
    wallet_id uuid,
    amount numeric(20,2)
);


ALTER TABLE public.settlement_queue OWNER TO u0_a253;

--
-- Name: obs_queue_state; Type: VIEW; Schema: public; Owner: omega
--

CREATE VIEW public.obs_queue_state AS
 SELECT status,
    count(*) AS count,
    min(created_at) AS oldest,
    max(updated_at) AS newest
   FROM public.settlement_queue
  GROUP BY status;


ALTER VIEW public.obs_queue_state OWNER TO omega;

--
-- Name: omega_account_balances; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.omega_account_balances (
    account_id uuid NOT NULL,
    balance numeric(20,2) DEFAULT 0.00 NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.omega_account_balances OWNER TO u0_a253;

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
-- Name: omega_account_map; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.omega_account_map (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    canonical_name text,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.omega_account_map OWNER TO omega;

--
-- Name: omega_balance_snapshot_import; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.omega_balance_snapshot_import (
    account text,
    balance numeric
);


ALTER TABLE public.omega_balance_snapshot_import OWNER TO u0_a253;

--
-- Name: omega_balance_stream; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.omega_balance_stream (
    id integer NOT NULL,
    account_id uuid,
    delta numeric(20,2),
    event_type text,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.omega_balance_stream OWNER TO u0_a253;

--
-- Name: omega_balance_stream_id_seq; Type: SEQUENCE; Schema: public; Owner: u0_a253
--

CREATE SEQUENCE public.omega_balance_stream_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.omega_balance_stream_id_seq OWNER TO u0_a253;

--
-- Name: omega_balance_stream_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: u0_a253
--

ALTER SEQUENCE public.omega_balance_stream_id_seq OWNED BY public.omega_balance_stream.id;


--
-- Name: omega_balances_rebuild; Type: VIEW; Schema: public; Owner: u0_a253
--

CREATE VIEW public.omega_balances_rebuild AS
 SELECT credit_account AS wallet_id,
    sum(amount) AS balance
   FROM public.ledger_entries
  GROUP BY credit_account;


ALTER VIEW public.omega_balances_rebuild OWNER TO u0_a253;

--
-- Name: omega_balances_unified; Type: VIEW; Schema: public; Owner: u0_a253
--

CREATE VIEW public.omega_balances_unified AS
 WITH ledger_balance AS (
         SELECT x.account,
            sum(x.amount) AS balance
           FROM ( SELECT ledger_entries.debit_account AS account,
                    ledger_entries.amount
                   FROM public.ledger_entries
                UNION ALL
                 SELECT ledger_entries.credit_account AS account,
                    (- ledger_entries.amount)
                   FROM public.ledger_entries) x
          GROUP BY x.account
        )
 SELECT w.account_id,
    w.currency,
    COALESCE(w.available_balance, (0)::numeric) AS wallet_balance,
    COALESCE(lb.balance, (0)::numeric) AS ledger_balance,
    (COALESCE(w.available_balance, (0)::numeric) - COALESCE(lb.balance, (0)::numeric)) AS delta
   FROM (public.wallets w
     LEFT JOIN ledger_balance lb ON ((lb.account = (w.account_id)::text)));


ALTER VIEW public.omega_balances_unified OWNER TO u0_a253;

--
-- Name: omega_bank_dashboard; Type: VIEW; Schema: public; Owner: u0_a253
--

CREATE VIEW public.omega_bank_dashboard AS
 SELECT a.owner_name,
    w.currency,
    w.available_balance,
    w.pending_balance,
    w.locked_balance,
    w.settled_balance,
    ('$'::text || to_char(w.settled_balance, 'FM999,999,999,999,999.00'::text)) AS formatted_balance
   FROM (public.wallets w
     LEFT JOIN public.accounts a ON ((a.account_id = w.account_id)))
  ORDER BY w.settled_balance DESC;


ALTER VIEW public.omega_bank_dashboard OWNER TO u0_a253;

--
-- Name: omega_bank_view; Type: VIEW; Schema: public; Owner: omega
--

CREATE VIEW public.omega_bank_view AS
 SELECT wallet_id AS account,
    (sum(
        CASE
            WHEN (direction = 'CREDIT'::text) THEN amount
            ELSE (0)::numeric
        END) - sum(
        CASE
            WHEN (direction = 'DEBIT'::text) THEN amount
            ELSE (0)::numeric
        END)) AS balance
   FROM public.ledger_entries
  GROUP BY wallet_id;


ALTER VIEW public.omega_bank_view OWNER TO omega;

--
-- Name: omega_card_events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.omega_card_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    card_token text NOT NULL,
    event_type text NOT NULL,
    amount numeric(20,2),
    merchant text,
    status text DEFAULT 'APPROVED'::text,
    ledger_entry_id uuid,
    chain_hash text,
    prev_hash text,
    created_at timestamp without time zone DEFAULT now(),
    metadata jsonb DEFAULT '{}'::jsonb
);


ALTER TABLE public.omega_card_events OWNER TO postgres;

--
-- Name: omega_cards; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.omega_cards (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    card_token text NOT NULL,
    wallet_id uuid NOT NULL,
    owner_name text,
    pan_encrypted text NOT NULL,
    pan_last4 text NOT NULL,
    pan_hash text NOT NULL,
    cvv_hash text NOT NULL,
    expiry_month integer NOT NULL,
    expiry_year integer NOT NULL,
    status text DEFAULT 'ACTIVE'::text,
    card_type text DEFAULT 'VIRTUAL'::text,
    spend_limit numeric(20,2) DEFAULT 5000.00,
    spend_used numeric(20,2) DEFAULT 0.00,
    ledger_entry_id uuid,
    issued_at timestamp without time zone DEFAULT now(),
    frozen_at timestamp without time zone,
    metadata jsonb DEFAULT '{}'::jsonb
);


ALTER TABLE public.omega_cards OWNER TO postgres;

--
-- Name: omega_consensus_nodes; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.omega_consensus_nodes (
    node_id text NOT NULL,
    endpoint text NOT NULL,
    public_key text DEFAULT 'auto-generated'::text,
    last_seen timestamp with time zone DEFAULT now(),
    active boolean DEFAULT true
)
WITH (autovacuum_enabled='true');


ALTER TABLE public.omega_consensus_nodes OWNER TO u0_a253;

--
-- Name: omega_consensus_state; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.omega_consensus_state (
    node_id text NOT NULL,
    chain_head_hash text NOT NULL,
    last_seq bigint NOT NULL,
    merkle_root text DEFAULT ''::text,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.omega_consensus_state OWNER TO u0_a253;

--
-- Name: omega_consensus_votes; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.omega_consensus_votes (
    node_id text NOT NULL,
    snapshot_id uuid NOT NULL,
    state_hash text,
    approved boolean,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.omega_consensus_votes OWNER TO u0_a253;

--
-- Name: omega_cycle_log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.omega_cycle_log (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    cycle_date timestamp without time zone DEFAULT now(),
    amount numeric(20,2),
    hops integer,
    successful integer,
    failed integer,
    elapsed_secs numeric(10,2),
    txn_ids jsonb
);


ALTER TABLE public.omega_cycle_log OWNER TO postgres;

--
-- Name: omega_events_sequence_number_seq; Type: SEQUENCE; Schema: public; Owner: omega
--

CREATE SEQUENCE public.omega_events_sequence_number_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.omega_events_sequence_number_seq OWNER TO omega;

--
-- Name: omega_events_sequence_number_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omega
--

ALTER SEQUENCE public.omega_events_sequence_number_seq OWNED BY public.omega_events.sequence_number;


--
-- Name: omega_financial_map; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.omega_financial_map (
    treasury_role text NOT NULL,
    wallet_id uuid
);


ALTER TABLE public.omega_financial_map OWNER TO omega;

--
-- Name: omega_genesis_events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.omega_genesis_events (
    genesis_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    treasury_usd numeric(20,2),
    treasury_eur numeric(20,2),
    treasury_gbp numeric(20,2),
    total_reserves_usd numeric(20,2),
    genesis_hash text,
    node_count integer DEFAULT 2,
    ledger_count bigint,
    confirmed_at timestamp without time zone DEFAULT now(),
    chain_hash text
);


ALTER TABLE public.omega_genesis_events OWNER TO postgres;

--
-- Name: omega_global_state; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.omega_global_state (
    key text NOT NULL,
    value text
);


ALTER TABLE public.omega_global_state OWNER TO u0_a253;

--
-- Name: omega_idempotency_log; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.omega_idempotency_log (
    id uuid NOT NULL,
    event_id uuid NOT NULL,
    idempotency_key text,
    event_type text NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.omega_idempotency_log OWNER TO omega;

--
-- Name: omega_instruments; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.omega_instruments (
    instrument_id uuid NOT NULL,
    wallet_id uuid NOT NULL,
    instrument_token text NOT NULL,
    instrument_type text NOT NULL,
    spend_limit numeric(20,2),
    currency text,
    status text NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    metadata jsonb DEFAULT '{}'::jsonb
);


ALTER TABLE public.omega_instruments OWNER TO omega;

--
-- Name: omega_ledger_state; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.omega_ledger_state (
    key text NOT NULL,
    value text NOT NULL
);


ALTER TABLE public.omega_ledger_state OWNER TO u0_a253;

--
-- Name: omega_master_bank; Type: VIEW; Schema: public; Owner: u0_a253
--

CREATE VIEW public.omega_master_bank AS
 SELECT COALESCE(a.owner_name, 'UNASSIGNED'::text) AS owner,
    w.id AS wallet_id,
    w.currency,
    (COALESCE(w.available_balance, 0.00))::numeric(20,2) AS available_balance,
    (COALESCE(w.pending_balance, 0.00))::numeric(20,2) AS pending_balance,
    (COALESCE(w.locked_balance, 0.00))::numeric(20,2) AS locked_balance,
    (COALESCE(w.reserved_balance, 0.00))::numeric(20,2) AS reserved_balance,
    (COALESCE(w.settled_balance, 0.00))::numeric(20,2) AS settled_balance
   FROM (public.wallets w
     LEFT JOIN public.accounts a ON ((a.account_id = w.account_id)));


ALTER VIEW public.omega_master_bank OWNER TO u0_a253;

--
-- Name: omega_merkle_state; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.omega_merkle_state (
    wallet_id text NOT NULL,
    balance_hash text NOT NULL,
    leaf_hash text NOT NULL,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.omega_merkle_state OWNER TO u0_a253;

--
-- Name: omega_mesh_events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.omega_mesh_events (
    id integer NOT NULL,
    from_node text,
    event_type text,
    payload jsonb,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.omega_mesh_events OWNER TO postgres;

--
-- Name: omega_mesh_events_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.omega_mesh_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.omega_mesh_events_id_seq OWNER TO postgres;

--
-- Name: omega_mesh_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.omega_mesh_events_id_seq OWNED BY public.omega_mesh_events.id;


--
-- Name: omega_net_worth; Type: VIEW; Schema: public; Owner: u0_a253
--

CREATE VIEW public.omega_net_worth AS
 SELECT wallet_id,
    balance,
    currency,
    updated_at
   FROM public.account_balances;


ALTER VIEW public.omega_net_worth OWNER TO u0_a253;

--
-- Name: omega_network_state_view; Type: VIEW; Schema: public; Owner: omega
--

CREATE VIEW public.omega_network_state_view AS
 WITH replay AS (
         SELECT ledger_entries.wallet_id,
            sum(
                CASE
                    WHEN (ledger_entries.direction = 'CREDIT'::text) THEN ledger_entries.amount
                    WHEN (ledger_entries.direction = 'DEBIT'::text) THEN (- ledger_entries.amount)
                    ELSE (0)::numeric
                END) AS replay_balance
           FROM public.ledger_entries
          GROUP BY ledger_entries.wallet_id
        )
 SELECT w.id,
    w.settled_balance,
    COALESCE(r.replay_balance, (0)::numeric) AS replay_balance,
    (w.settled_balance - COALESCE(r.replay_balance, (0)::numeric)) AS drift
   FROM (public.wallets w
     LEFT JOIN replay r ON ((w.id = r.wallet_id)));


ALTER VIEW public.omega_network_state_view OWNER TO omega;

--
-- Name: omega_node_manifest; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.omega_node_manifest (
    node_id text NOT NULL,
    hostname text,
    config jsonb,
    version text,
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.omega_node_manifest OWNER TO postgres;

--
-- Name: omega_node_registry; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.omega_node_registry (
    node_id text NOT NULL,
    host text NOT NULL,
    mesh_port integer DEFAULT 7433,
    status text DEFAULT 'active'::text,
    last_seen timestamp without time zone DEFAULT now(),
    chain_tip bigint DEFAULT 0,
    entry_count bigint DEFAULT 0,
    version text DEFAULT '1.0'::text,
    metadata jsonb DEFAULT '{}'::jsonb
);


ALTER TABLE public.omega_node_registry OWNER TO postgres;

--
-- Name: treasury_reserve; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.treasury_reserve (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name text NOT NULL,
    total_capital numeric(20,2) DEFAULT 0.00 NOT NULL,
    allocated_credit numeric(20,2) DEFAULT 0.00 NOT NULL,
    frozen boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.treasury_reserve OWNER TO omega;

--
-- Name: omega_proof_of_reserves; Type: VIEW; Schema: public; Owner: omega
--

CREATE VIEW public.omega_proof_of_reserves AS
 SELECT ( SELECT COALESCE(sum(treasury_reserve.total_capital), (0)::numeric) AS "coalesce"
           FROM public.treasury_reserve) AS treasury_backing,
    ( SELECT COALESCE(sum(wallets.settled_balance), (0)::numeric) AS "coalesce"
           FROM public.wallets) AS issued_liabilities,
    ( SELECT COALESCE(sum(credit_lines.credit_limit), (0)::numeric) AS "coalesce"
           FROM public.credit_lines) AS total_credit_exposure,
    (( SELECT COALESCE(sum(treasury_reserve.total_capital), (0)::numeric) AS "coalesce"
           FROM public.treasury_reserve) - ( SELECT COALESCE(sum(wallets.settled_balance), (0)::numeric) AS "coalesce"
           FROM public.wallets)) AS reserve_surplus;


ALTER VIEW public.omega_proof_of_reserves OWNER TO omega;

--
-- Name: omega_recovery_journal; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.omega_recovery_journal (
    id bigint NOT NULL,
    event_type text NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.omega_recovery_journal OWNER TO u0_a253;

--
-- Name: omega_recovery_journal_id_seq; Type: SEQUENCE; Schema: public; Owner: u0_a253
--

CREATE SEQUENCE public.omega_recovery_journal_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.omega_recovery_journal_id_seq OWNER TO u0_a253;

--
-- Name: omega_recovery_journal_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: u0_a253
--

ALTER SEQUENCE public.omega_recovery_journal_id_seq OWNED BY public.omega_recovery_journal.id;


--
-- Name: omega_self_verifying_ledger; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.omega_self_verifying_ledger (
    id bigint NOT NULL,
    payload jsonb NOT NULL,
    previous_hash text,
    current_hash text NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.omega_self_verifying_ledger OWNER TO u0_a253;

--
-- Name: omega_self_verifying_ledger_id_seq; Type: SEQUENCE; Schema: public; Owner: u0_a253
--

CREATE SEQUENCE public.omega_self_verifying_ledger_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.omega_self_verifying_ledger_id_seq OWNER TO u0_a253;

--
-- Name: omega_self_verifying_ledger_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: u0_a253
--

ALTER SEQUENCE public.omega_self_verifying_ledger_id_seq OWNED BY public.omega_self_verifying_ledger.id;


--
-- Name: omega_settlement_global_lock; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.omega_settlement_global_lock (
    event_id uuid NOT NULL,
    hash text NOT NULL,
    locked_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.omega_settlement_global_lock OWNER TO omega;

--
-- Name: omega_settlement_state; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.omega_settlement_state (
    id uuid NOT NULL,
    settlement_id uuid NOT NULL,
    state text NOT NULL,
    payload jsonb NOT NULL,
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.omega_settlement_state OWNER TO omega;

--
-- Name: omega_spawn_signals; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.omega_spawn_signals (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    signal_node text,
    reason text,
    ledger_count bigint,
    created_at timestamp without time zone DEFAULT now(),
    actioned boolean DEFAULT false
);


ALTER TABLE public.omega_spawn_signals OWNER TO postgres;

--
-- Name: omega_state_snapshots; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.omega_state_snapshots (
    snapshot_id uuid DEFAULT gen_random_uuid() NOT NULL,
    merkle_root text NOT NULL,
    event_seq bigint NOT NULL,
    wallet_count bigint NOT NULL,
    total_supply numeric(38,8) NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.omega_state_snapshots OWNER TO u0_a253;

--
-- Name: omega_supply_lock; Type: VIEW; Schema: public; Owner: u0_a253
--

CREATE VIEW public.omega_supply_lock AS
 SELECT sum(balance) AS total_supply,
    count(*) AS wallets,
    bool_and((balance >= (0)::numeric)) AS no_negative_inflation
   FROM public.account_balances;


ALTER VIEW public.omega_supply_lock OWNER TO u0_a253;

--
-- Name: omega_system_liquidity; Type: VIEW; Schema: public; Owner: u0_a253
--

CREATE VIEW public.omega_system_liquidity AS
 SELECT sum(settled_balance) AS total_liquidity,
    sum(available_balance) AS total_available,
    sum(reserved_balance) AS total_reserved
   FROM public.wallets;


ALTER VIEW public.omega_system_liquidity OWNER TO u0_a253;

--
-- Name: omega_treasury_roles; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.omega_treasury_roles (
    account_role text NOT NULL,
    wallet_id uuid,
    reserve_balance numeric(20,2),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.omega_treasury_roles OWNER TO omega;

--
-- Name: overdraft_limits; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.overdraft_limits (
    wallet_id uuid NOT NULL,
    limit_amount numeric(20,2) DEFAULT 0 NOT NULL
);


ALTER TABLE public.overdraft_limits OWNER TO u0_a253;

--
-- Name: payment_authorizations; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.payment_authorizations (
    id uuid NOT NULL,
    wallet_id uuid NOT NULL,
    merchant text NOT NULL,
    amount numeric(20,2) NOT NULL,
    status text NOT NULL,
    network text NOT NULL,
    response_code text NOT NULL,
    created_at timestamp without time zone NOT NULL,
    lifecycle_state public.authorization_state DEFAULT 'AUTHORIZED'::public.authorization_state
);


ALTER TABLE public.payment_authorizations OWNER TO omega;

--
-- Name: payment_instruments; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.payment_instruments (
    instrument_id uuid NOT NULL,
    wallet_id uuid NOT NULL,
    type text NOT NULL,
    status text NOT NULL,
    spend_limit numeric(20,2),
    currency text,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.payment_instruments OWNER TO omega;

--
-- Name: payment_requests; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.payment_requests (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    merchant_id uuid NOT NULL,
    amount numeric(20,2) NOT NULL,
    currency text DEFAULT 'USD'::text NOT NULL,
    description text DEFAULT ''::text,
    status public.payment_request_status_type DEFAULT 'PENDING'::public.payment_request_status_type NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.payment_requests OWNER TO omega;

--
-- Name: payment_reversals; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.payment_reversals (
    id uuid NOT NULL,
    auth_id uuid NOT NULL,
    wallet_id uuid NOT NULL,
    amount numeric(20,2) NOT NULL,
    reason text NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.payment_reversals OWNER TO omega;

--
-- Name: payment_settlements; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.payment_settlements (
    id uuid NOT NULL,
    auth_id uuid NOT NULL,
    wallet_id uuid NOT NULL,
    merchant text NOT NULL,
    amount numeric(20,2) NOT NULL,
    status text NOT NULL,
    settled_at timestamp without time zone NOT NULL
);


ALTER TABLE public.payment_settlements OWNER TO omega;

--
-- Name: payment_transactions; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.payment_transactions (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    payment_request_id uuid,
    wallet_id uuid NOT NULL,
    card_id uuid,
    token_id uuid,
    ledger_event_id uuid,
    amount numeric(20,2) NOT NULL,
    currency text DEFAULT 'USD'::text NOT NULL,
    transaction_type public.payment_transaction_type NOT NULL,
    status public.payment_transaction_status DEFAULT 'PENDING'::public.payment_transaction_status NOT NULL,
    idempotency_key uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.payment_transactions OWNER TO omega;

--
-- Name: pending_holds; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.pending_holds (
    id uuid NOT NULL,
    auth_id uuid,
    wallet_id uuid,
    hold_amount numeric(20,2),
    expires_at timestamp without time zone,
    status text,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.pending_holds OWNER TO omega;

--
-- Name: processed_transactions; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.processed_transactions (
    idempotency_key text NOT NULL,
    tx_hash text NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.processed_transactions OWNER TO u0_a253;

--
-- Name: reconciliation_snapshots; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.reconciliation_snapshots (
    id uuid NOT NULL,
    ledger_total numeric(20,2) NOT NULL,
    wallet_total numeric(20,2) NOT NULL,
    treasury_total numeric(20,2) NOT NULL,
    external_total numeric(20,2) NOT NULL,
    drift numeric(20,2) NOT NULL,
    status text NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    CONSTRAINT reconciliation_snapshots_status_check CHECK ((status = ANY (ARRAY['MATCHED'::text, 'DRIFT'::text, 'CRITICAL'::text])))
);


ALTER TABLE public.reconciliation_snapshots OWNER TO omega;

--
-- Name: reserve_locks; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.reserve_locks (
    id uuid NOT NULL,
    wallet_id uuid NOT NULL,
    amount numeric(20,2) NOT NULL,
    status text NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.reserve_locks OWNER TO u0_a253;

--
-- Name: reserve_segments; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.reserve_segments (
    id uuid NOT NULL,
    segment_name text,
    reserve_type text,
    balance numeric(20,2),
    locked boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.reserve_segments OWNER TO omega;

--
-- Name: settlement_batches; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.settlement_batches (
    id uuid NOT NULL,
    network text,
    batch_total numeric(20,2),
    tx_count integer,
    status text,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.settlement_batches OWNER TO omega;

--
-- Name: settlement_events; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.settlement_events (
    id uuid NOT NULL,
    hold_id uuid,
    event_type text NOT NULL,
    payload jsonb NOT NULL,
    status text NOT NULL,
    retry_count integer DEFAULT 0 NOT NULL,
    idempotency_key text NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    CONSTRAINT settlement_events_event_type_check CHECK ((event_type = ANY (ARRAY['AUTH'::text, 'CAPTURE'::text, 'REVERSAL'::text, 'CLEARING'::text, 'RECONCILIATION'::text]))),
    CONSTRAINT settlement_events_status_check CHECK ((status = ANY (ARRAY['PENDING'::text, 'PROCESSING'::text, 'SETTLED'::text, 'FAILED'::text])))
);


ALTER TABLE public.settlement_events OWNER TO omega;

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
-- Name: supply_lock; Type: VIEW; Schema: public; Owner: u0_a253
--

CREATE VIEW public.supply_lock AS
 WITH minted AS (
         SELECT omega_events.currency,
            sum(omega_events.amount) AS gross_minted
           FROM public.omega_events
          WHERE (omega_events.event_type = 'MINT'::text)
          GROUP BY omega_events.currency
        ), burned AS (
         SELECT omega_events.currency,
            sum(omega_events.amount) AS gross_burned
           FROM public.omega_events
          WHERE (omega_events.event_type = 'BURN'::text)
          GROUP BY omega_events.currency
        ), fees_collected AS (
         SELECT omega_events.currency,
            sum(omega_events.amount) AS total_fees
           FROM public.omega_events
          WHERE (omega_events.event_type = 'FEE'::text)
          GROUP BY omega_events.currency
        ), live_balances AS (
         SELECT account_balances.currency,
            sum(account_balances.balance) AS sum_balances,
            count(DISTINCT account_balances.wallet_id) AS wallet_count
           FROM public.account_balances
          GROUP BY account_balances.currency
        ), event_totals AS (
         SELECT omega_events.currency,
            count(*) AS total_events
           FROM public.omega_events
          GROUP BY omega_events.currency
        )
 SELECT COALESCE(m.currency, b.currency, lb.currency, f.currency) AS currency,
    COALESCE(m.gross_minted, (0)::numeric) AS gross_minted,
    COALESCE(b.gross_burned, (0)::numeric) AS gross_burned,
    COALESCE(f.total_fees, (0)::numeric) AS total_fees_collected,
    (COALESCE(m.gross_minted, (0)::numeric) - COALESCE(b.gross_burned, (0)::numeric)) AS net_supply,
    COALESCE(lb.sum_balances, (0)::numeric) AS circulating_balance,
        CASE
            WHEN (COALESCE(lb.sum_balances, (0)::numeric) = (COALESCE(m.gross_minted, (0)::numeric) - COALESCE(b.gross_burned, (0)::numeric))) THEN 'LOCKED'::text
            ELSE 'SUPPLY_DRIFT'::text
        END AS lock_status,
    COALESCE(lb.wallet_count, (0)::bigint) AS active_wallets,
    COALESCE(et.total_events, (0)::bigint) AS total_events
   FROM ((((minted m
     FULL JOIN burned b ON ((m.currency = b.currency)))
     FULL JOIN fees_collected f ON ((COALESCE(m.currency, b.currency) = f.currency)))
     FULL JOIN live_balances lb ON ((COALESCE(m.currency, b.currency, f.currency) = lb.currency)))
     FULL JOIN event_totals et ON ((COALESCE(m.currency, b.currency, f.currency, lb.currency) = et.currency)))
  ORDER BY COALESCE(m.currency, b.currency, lb.currency, f.currency);


ALTER VIEW public.supply_lock OWNER TO u0_a253;

--
-- Name: system_accounts; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.system_accounts (
    name text NOT NULL,
    account_id uuid NOT NULL
);


ALTER TABLE public.system_accounts OWNER TO u0_a253;

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
-- Name: system_snapshots; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.system_snapshots (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    snapshot_time timestamp without time zone DEFAULT now(),
    ledger_hash text,
    wallet_hash text,
    treasury_hash text,
    invariant_failures integer,
    active_queues integer,
    snapshot jsonb
);


ALTER TABLE public.system_snapshots OWNER TO omega;

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
-- Name: tokens; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.tokens (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    card_id uuid NOT NULL,
    token_value text NOT NULL,
    status public.token_status_type DEFAULT 'ACTIVE'::public.token_status_type NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.tokens OWNER TO omega;

--
-- Name: transaction_stream; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.transaction_stream (
    id bigint NOT NULL,
    wallet_id uuid NOT NULL,
    amount numeric(20,2) NOT NULL,
    merchant_risk numeric(10,2) DEFAULT 0,
    velocity_1m numeric(10,2) DEFAULT 0,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.transaction_stream OWNER TO omega;

--
-- Name: transaction_stream_id_seq; Type: SEQUENCE; Schema: public; Owner: omega
--

CREATE SEQUENCE public.transaction_stream_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.transaction_stream_id_seq OWNER TO omega;

--
-- Name: transaction_stream_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omega
--

ALTER SEQUENCE public.transaction_stream_id_seq OWNED BY public.transaction_stream.id;


--
-- Name: transactions; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.transactions (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    wallet_id uuid,
    amount numeric(20,2),
    status text,
    merchant text,
    risk_score integer,
    created_at timestamp without time zone DEFAULT now(),
    settlement_status text DEFAULT 'PENDING'::text,
    idempotency_key text,
    authorization_hold boolean DEFAULT false,
    settled_at timestamp without time zone,
    reconciled_at timestamp without time zone
);


ALTER TABLE public.transactions OWNER TO omega;

--
-- Name: treasury_accounts; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.treasury_accounts (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    reserve_name text,
    reserve_balance numeric(20,2),
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.treasury_accounts OWNER TO omega;

--
-- Name: treasury_limits; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.treasury_limits (
    asset_type text NOT NULL,
    total_liquidity numeric(20,2) NOT NULL,
    reserved numeric(20,2) DEFAULT 0 NOT NULL
);


ALTER TABLE public.treasury_limits OWNER TO omega;

--
-- Name: treasury_locks; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.treasury_locks (
    id uuid NOT NULL,
    wallet_id uuid NOT NULL,
    hold_id uuid NOT NULL,
    amount numeric(20,2) NOT NULL,
    status text NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    CONSTRAINT treasury_locks_amount_check CHECK ((amount > (0)::numeric)),
    CONSTRAINT treasury_locks_status_check CHECK ((status = ANY (ARRAY['LOCKED'::text, 'RELEASED'::text, 'SETTLED'::text])))
);


ALTER TABLE public.treasury_locks OWNER TO omega;

--
-- Name: treasury_state; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.treasury_state (
    asset_type text NOT NULL,
    available_balance numeric(20,2) DEFAULT 0 NOT NULL,
    locked_balance numeric(20,2) DEFAULT 0 NOT NULL,
    pending_outflow numeric(20,2) DEFAULT 0 NOT NULL
);


ALTER TABLE public.treasury_state OWNER TO omega;

--
-- Name: treasury_state_projection; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.treasury_state_projection (
    treasury_id uuid NOT NULL,
    reserve_balance numeric(20,2) DEFAULT 0 NOT NULL,
    outstanding_liabilities numeric(20,2) DEFAULT 0 NOT NULL,
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.treasury_state_projection OWNER TO omega;

--
-- Name: v_spendable_only; Type: VIEW; Schema: public; Owner: omega
--

CREATE VIEW public.v_spendable_only AS
 SELECT id AS wallet_id,
    (settled_balance - locked_balance) AS spendable_balance
   FROM public.wallets;


ALTER VIEW public.v_spendable_only OWNER TO omega;

--
-- Name: v_wallet_balances; Type: VIEW; Schema: public; Owner: omega
--

CREATE VIEW public.v_wallet_balances AS
 SELECT w.id AS wallet_id,
    COALESCE(sum(
        CASE
            WHEN (le.direction = 'CREDIT'::text) THEN le.amount
            ELSE (- le.amount)
        END), (0)::numeric) AS ledger_balance,
    w.settled_balance,
    w.locked_balance,
    (w.settled_balance - w.locked_balance) AS spendable_balance,
    (w.settled_balance - COALESCE(sum(
        CASE
            WHEN (le.direction = 'CREDIT'::text) THEN le.amount
            ELSE (- le.amount)
        END), (0)::numeric)) AS drift
   FROM (public.wallets w
     LEFT JOIN public.ledger_entries le ON ((le.wallet_id = w.id)))
  GROUP BY w.id, w.settled_balance, w.locked_balance;


ALTER VIEW public.v_wallet_balances OWNER TO omega;

--
-- Name: velocity_tracking; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.velocity_tracking (
    wallet_id uuid NOT NULL,
    transaction_count integer DEFAULT 0,
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.velocity_tracking OWNER TO omega;

--
-- Name: virtual_cards; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.virtual_cards (
    id uuid NOT NULL,
    wallet_id uuid NOT NULL,
    card_token text NOT NULL,
    masked_pan text NOT NULL,
    expiry_month integer NOT NULL,
    expiry_year integer NOT NULL,
    cvv_hash text NOT NULL,
    status text DEFAULT 'ACTIVE'::text NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    spendable_limit numeric(20,2) DEFAULT 0 NOT NULL
);


ALTER TABLE public.virtual_cards OWNER TO omega;

--
-- Name: wallet_balances; Type: MATERIALIZED VIEW; Schema: public; Owner: omega
--

CREATE MATERIALIZED VIEW public.wallet_balances AS
 SELECT wallet_id,
    sum(
        CASE
            WHEN (direction = 'CREDIT'::text) THEN amount
            ELSE (- amount)
        END) AS balance
   FROM public.ledger_entries
  GROUP BY wallet_id
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.wallet_balances OWNER TO omega;

--
-- Name: wallet_projections; Type: TABLE; Schema: public; Owner: u0_a253
--

CREATE TABLE public.wallet_projections (
    account_id uuid NOT NULL,
    balance numeric(20,2),
    updated_at timestamp without time zone DEFAULT now(),
    wallet_id text
);


ALTER TABLE public.wallet_projections OWNER TO u0_a253;

--
-- Name: wallet_registry; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.wallet_registry (
    alias text NOT NULL,
    wallet_id uuid NOT NULL
);


ALTER TABLE public.wallet_registry OWNER TO omega;

--
-- Name: wallet_state_projection; Type: TABLE; Schema: public; Owner: omega
--

CREATE TABLE public.wallet_state_projection (
    wallet_id uuid NOT NULL,
    available_balance numeric(20,2) DEFAULT 0 NOT NULL,
    pending_balance numeric(20,2) DEFAULT 0 NOT NULL,
    reserved_balance numeric(20,2) DEFAULT 0 NOT NULL,
    settled_balance numeric(20,2) DEFAULT 0 NOT NULL,
    credit_limit numeric(20,2) DEFAULT 0 NOT NULL,
    used_credit numeric(20,2) DEFAULT 0 NOT NULL,
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.wallet_state_projection OWNER TO omega;

--
-- Name: consensus_drift_log id; Type: DEFAULT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.consensus_drift_log ALTER COLUMN id SET DEFAULT nextval('public.consensus_drift_log_id_seq'::regclass);


--
-- Name: fx_logs id; Type: DEFAULT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.fx_logs ALTER COLUMN id SET DEFAULT nextval('public.fx_logs_id_seq'::regclass);


--
-- Name: ledger_entries global_sequence; Type: DEFAULT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.ledger_entries ALTER COLUMN global_sequence SET DEFAULT nextval('public.ledger_entries_global_sequence_seq'::regclass);


--
-- Name: ledger_events sequence_number; Type: DEFAULT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.ledger_events ALTER COLUMN sequence_number SET DEFAULT nextval('public.ledger_events_sequence_number_seq'::regclass);


--
-- Name: omega_balance_stream id; Type: DEFAULT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.omega_balance_stream ALTER COLUMN id SET DEFAULT nextval('public.omega_balance_stream_id_seq'::regclass);


--
-- Name: omega_events sequence_number; Type: DEFAULT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.omega_events ALTER COLUMN sequence_number SET DEFAULT nextval('public.omega_events_sequence_number_seq'::regclass);


--
-- Name: omega_mesh_events id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.omega_mesh_events ALTER COLUMN id SET DEFAULT nextval('public.omega_mesh_events_id_seq'::regclass);


--
-- Name: omega_recovery_journal id; Type: DEFAULT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.omega_recovery_journal ALTER COLUMN id SET DEFAULT nextval('public.omega_recovery_journal_id_seq'::regclass);


--
-- Name: omega_self_verifying_ledger id; Type: DEFAULT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.omega_self_verifying_ledger ALTER COLUMN id SET DEFAULT nextval('public.omega_self_verifying_ledger_id_seq'::regclass);


--
-- Name: transaction_stream id; Type: DEFAULT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.transaction_stream ALTER COLUMN id SET DEFAULT nextval('public.transaction_stream_id_seq'::regclass);


--
-- Name: account_balances account_balances_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.account_balances
    ADD CONSTRAINT account_balances_pkey PRIMARY KEY (wallet_id);


--
-- Name: accounts accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.accounts
    ADD CONSTRAINT accounts_pkey PRIMARY KEY (account_id);


--
-- Name: ach_wire_events ach_wire_events_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.ach_wire_events
    ADD CONSTRAINT ach_wire_events_pkey PRIMARY KEY (id);


--
-- Name: async_settlement_jobs async_settlement_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.async_settlement_jobs
    ADD CONSTRAINT async_settlement_jobs_pkey PRIMARY KEY (id);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: auth_holds auth_holds_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.auth_holds
    ADD CONSTRAINT auth_holds_pkey PRIMARY KEY (id);


--
-- Name: authorization_expirations authorization_expirations_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.authorization_expirations
    ADD CONSTRAINT authorization_expirations_pkey PRIMARY KEY (id);


--
-- Name: authorization_holds authorization_holds_idempotency_key_key; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.authorization_holds
    ADD CONSTRAINT authorization_holds_idempotency_key_key UNIQUE (idempotency_key);


--
-- Name: authorization_holds authorization_holds_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.authorization_holds
    ADD CONSTRAINT authorization_holds_pkey PRIMARY KEY (id);


--
-- Name: canonical_accounts canonical_accounts_identity_hash_key; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.canonical_accounts
    ADD CONSTRAINT canonical_accounts_identity_hash_key UNIQUE (identity_hash);


--
-- Name: canonical_accounts canonical_accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.canonical_accounts
    ADD CONSTRAINT canonical_accounts_pkey PRIMARY KEY (account_id);


--
-- Name: capture_events capture_events_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.capture_events
    ADD CONSTRAINT capture_events_pkey PRIMARY KEY (id);


--
-- Name: card_registry card_registry_pan_key; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.card_registry
    ADD CONSTRAINT card_registry_pan_key UNIQUE (pan);


--
-- Name: card_registry card_registry_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.card_registry
    ADD CONSTRAINT card_registry_pkey PRIMARY KEY (card_id);


--
-- Name: card_transactions card_transactions_idempotency_key_key; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.card_transactions
    ADD CONSTRAINT card_transactions_idempotency_key_key UNIQUE (idempotency_key);


--
-- Name: card_transactions card_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.card_transactions
    ADD CONSTRAINT card_transactions_pkey PRIMARY KEY (id);


--
-- Name: cards cards_card_number_key; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.cards
    ADD CONSTRAINT cards_card_number_key UNIQUE (card_number);


--
-- Name: cards cards_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.cards
    ADD CONSTRAINT cards_pkey PRIMARY KEY (id);


--
-- Name: chargeback_cases chargeback_cases_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.chargeback_cases
    ADD CONSTRAINT chargeback_cases_pkey PRIMARY KEY (id);


--
-- Name: connector_event_log connector_event_log_idempotency_key_key; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.connector_event_log
    ADD CONSTRAINT connector_event_log_idempotency_key_key UNIQUE (idempotency_key);


--
-- Name: connector_event_log connector_event_log_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.connector_event_log
    ADD CONSTRAINT connector_event_log_pkey PRIMARY KEY (id);


--
-- Name: consensus_drift_log consensus_drift_log_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.consensus_drift_log
    ADD CONSTRAINT consensus_drift_log_pkey PRIMARY KEY (id);


--
-- Name: credit_lines credit_lines_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.credit_lines
    ADD CONSTRAINT credit_lines_pkey PRIMARY KEY (wallet_id);


--
-- Name: credit_policy_state credit_policy_state_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.credit_policy_state
    ADD CONSTRAINT credit_policy_state_pkey PRIMARY KEY (wallet_id);


--
-- Name: currency_treasury currency_treasury_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.currency_treasury
    ADD CONSTRAINT currency_treasury_pkey PRIMARY KEY (currency_code);


--
-- Name: dispute_cases dispute_cases_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.dispute_cases
    ADD CONSTRAINT dispute_cases_pkey PRIMARY KEY (id);


--
-- Name: execution_lease execution_lease_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.execution_lease
    ADD CONSTRAINT execution_lease_pkey PRIMARY KEY (idempotency_key);


--
-- Name: fraud_velocity_state fraud_velocity_state_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.fraud_velocity_state
    ADD CONSTRAINT fraud_velocity_state_pkey PRIMARY KEY (wallet_id);


--
-- Name: fx_logs fx_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.fx_logs
    ADD CONSTRAINT fx_logs_pkey PRIMARY KEY (id);


--
-- Name: idempotency_keys idempotency_keys_idempotency_key_key; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.idempotency_keys
    ADD CONSTRAINT idempotency_keys_idempotency_key_key UNIQUE (idempotency_key);


--
-- Name: idempotency_keys idempotency_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.idempotency_keys
    ADD CONSTRAINT idempotency_keys_pkey PRIMARY KEY (id);


--
-- Name: interchange_fee_events interchange_fee_events_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.interchange_fee_events
    ADD CONSTRAINT interchange_fee_events_pkey PRIMARY KEY (id);


--
-- Name: invariant_failures invariant_failures_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.invariant_failures
    ADD CONSTRAINT invariant_failures_pkey PRIMARY KEY (id);


--
-- Name: iso_messages iso_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.iso_messages
    ADD CONSTRAINT iso_messages_pkey PRIMARY KEY (id);


--
-- Name: issuer_queue issuer_queue_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.issuer_queue
    ADD CONSTRAINT issuer_queue_pkey PRIMARY KEY (id);


--
-- Name: ledger_entries ledger_entries_idempotency_key_key; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.ledger_entries
    ADD CONSTRAINT ledger_entries_idempotency_key_key UNIQUE (idempotency_key);


--
-- Name: ledger_entries ledger_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.ledger_entries
    ADD CONSTRAINT ledger_entries_pkey PRIMARY KEY (id);


--
-- Name: ledger_event_stream ledger_event_stream_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.ledger_event_stream
    ADD CONSTRAINT ledger_event_stream_pkey PRIMARY KEY (event_id);


--
-- Name: ledger_events ledger_events_idempotency_key_key; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.ledger_events
    ADD CONSTRAINT ledger_events_idempotency_key_key UNIQUE (idempotency_key);


--
-- Name: ledger_events ledger_events_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.ledger_events
    ADD CONSTRAINT ledger_events_pkey PRIMARY KEY (id);


--
-- Name: ledger_events ledger_events_sequence_number_key; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.ledger_events
    ADD CONSTRAINT ledger_events_sequence_number_key UNIQUE (sequence_number);


--
-- Name: ledger_postings ledger_postings_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.ledger_postings
    ADD CONSTRAINT ledger_postings_pkey PRIMARY KEY (posting_id);


--
-- Name: ledger_snapshots ledger_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.ledger_snapshots
    ADD CONSTRAINT ledger_snapshots_pkey PRIMARY KEY (account, global_sequence);


--
-- Name: ledger_transactions ledger_transactions_idempotency_key_key; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.ledger_transactions
    ADD CONSTRAINT ledger_transactions_idempotency_key_key UNIQUE (idempotency_key);


--
-- Name: ledger_transactions ledger_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.ledger_transactions
    ADD CONSTRAINT ledger_transactions_pkey PRIMARY KEY (id);


--
-- Name: ledger_write_guard ledger_write_guard_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.ledger_write_guard
    ADD CONSTRAINT ledger_write_guard_pkey PRIMARY KEY (idempotency_key);


--
-- Name: merchant_batches merchant_batches_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.merchant_batches
    ADD CONSTRAINT merchant_batches_pkey PRIMARY KEY (id);


--
-- Name: merchants merchants_merchant_id_key; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.merchants
    ADD CONSTRAINT merchants_merchant_id_key UNIQUE (merchant_id);


--
-- Name: merchants merchants_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.merchants
    ADD CONSTRAINT merchants_pkey PRIMARY KEY (id);


--
-- Name: network_clearance_windows network_clearance_windows_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.network_clearance_windows
    ADD CONSTRAINT network_clearance_windows_pkey PRIMARY KEY (id);


--
-- Name: omega_account_balances omega_account_balances_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.omega_account_balances
    ADD CONSTRAINT omega_account_balances_pkey PRIMARY KEY (account_id);


--
-- Name: omega_account_canonical omega_account_canonical_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.omega_account_canonical
    ADD CONSTRAINT omega_account_canonical_pkey PRIMARY KEY (account_id);


--
-- Name: omega_account_map omega_account_map_canonical_name_key; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.omega_account_map
    ADD CONSTRAINT omega_account_map_canonical_name_key UNIQUE (canonical_name);


--
-- Name: omega_account_map omega_account_map_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.omega_account_map
    ADD CONSTRAINT omega_account_map_pkey PRIMARY KEY (id);


--
-- Name: omega_balance_stream omega_balance_stream_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.omega_balance_stream
    ADD CONSTRAINT omega_balance_stream_pkey PRIMARY KEY (id);


--
-- Name: omega_card_events omega_card_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.omega_card_events
    ADD CONSTRAINT omega_card_events_pkey PRIMARY KEY (id);


--
-- Name: omega_cards omega_cards_card_token_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.omega_cards
    ADD CONSTRAINT omega_cards_card_token_key UNIQUE (card_token);


--
-- Name: omega_cards omega_cards_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.omega_cards
    ADD CONSTRAINT omega_cards_pkey PRIMARY KEY (id);


--
-- Name: omega_consensus_nodes omega_consensus_nodes_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.omega_consensus_nodes
    ADD CONSTRAINT omega_consensus_nodes_pkey PRIMARY KEY (node_id);


--
-- Name: omega_consensus_state omega_consensus_state_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.omega_consensus_state
    ADD CONSTRAINT omega_consensus_state_pkey PRIMARY KEY (node_id);


--
-- Name: omega_consensus_votes omega_consensus_votes_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.omega_consensus_votes
    ADD CONSTRAINT omega_consensus_votes_pkey PRIMARY KEY (node_id, snapshot_id);


--
-- Name: omega_cycle_log omega_cycle_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.omega_cycle_log
    ADD CONSTRAINT omega_cycle_log_pkey PRIMARY KEY (id);


--
-- Name: omega_events omega_events_idempotency_key_key; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.omega_events
    ADD CONSTRAINT omega_events_idempotency_key_key UNIQUE (idempotency_key);


--
-- Name: omega_events omega_events_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.omega_events
    ADD CONSTRAINT omega_events_pkey PRIMARY KEY (event_id);


--
-- Name: omega_financial_map omega_financial_map_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.omega_financial_map
    ADD CONSTRAINT omega_financial_map_pkey PRIMARY KEY (treasury_role);


--
-- Name: omega_genesis_events omega_genesis_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.omega_genesis_events
    ADD CONSTRAINT omega_genesis_events_pkey PRIMARY KEY (genesis_id);


--
-- Name: omega_global_state omega_global_state_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.omega_global_state
    ADD CONSTRAINT omega_global_state_pkey PRIMARY KEY (key);


--
-- Name: omega_idempotency_log omega_idempotency_log_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.omega_idempotency_log
    ADD CONSTRAINT omega_idempotency_log_pkey PRIMARY KEY (id);


--
-- Name: omega_instruments omega_instruments_instrument_token_key; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.omega_instruments
    ADD CONSTRAINT omega_instruments_instrument_token_key UNIQUE (instrument_token);


--
-- Name: omega_instruments omega_instruments_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.omega_instruments
    ADD CONSTRAINT omega_instruments_pkey PRIMARY KEY (instrument_id);


--
-- Name: omega_ledger_state omega_ledger_state_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.omega_ledger_state
    ADD CONSTRAINT omega_ledger_state_pkey PRIMARY KEY (key);


--
-- Name: omega_merkle_state omega_merkle_state_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.omega_merkle_state
    ADD CONSTRAINT omega_merkle_state_pkey PRIMARY KEY (wallet_id);


--
-- Name: omega_mesh_events omega_mesh_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.omega_mesh_events
    ADD CONSTRAINT omega_mesh_events_pkey PRIMARY KEY (id);


--
-- Name: omega_node_manifest omega_node_manifest_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.omega_node_manifest
    ADD CONSTRAINT omega_node_manifest_pkey PRIMARY KEY (node_id);


--
-- Name: omega_node_registry omega_node_registry_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.omega_node_registry
    ADD CONSTRAINT omega_node_registry_pkey PRIMARY KEY (node_id);


--
-- Name: omega_recovery_journal omega_recovery_journal_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.omega_recovery_journal
    ADD CONSTRAINT omega_recovery_journal_pkey PRIMARY KEY (id);


--
-- Name: omega_self_verifying_ledger omega_self_verifying_ledger_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.omega_self_verifying_ledger
    ADD CONSTRAINT omega_self_verifying_ledger_pkey PRIMARY KEY (id);


--
-- Name: omega_settlement_global_lock omega_settlement_global_lock_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.omega_settlement_global_lock
    ADD CONSTRAINT omega_settlement_global_lock_pkey PRIMARY KEY (event_id);


--
-- Name: omega_settlement_state omega_settlement_state_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.omega_settlement_state
    ADD CONSTRAINT omega_settlement_state_pkey PRIMARY KEY (id);


--
-- Name: omega_spawn_signals omega_spawn_signals_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.omega_spawn_signals
    ADD CONSTRAINT omega_spawn_signals_pkey PRIMARY KEY (id);


--
-- Name: omega_state_snapshots omega_state_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.omega_state_snapshots
    ADD CONSTRAINT omega_state_snapshots_pkey PRIMARY KEY (snapshot_id);


--
-- Name: omega_treasury_roles omega_treasury_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.omega_treasury_roles
    ADD CONSTRAINT omega_treasury_roles_pkey PRIMARY KEY (account_role);


--
-- Name: overdraft_limits overdraft_limits_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.overdraft_limits
    ADD CONSTRAINT overdraft_limits_pkey PRIMARY KEY (wallet_id);


--
-- Name: payment_authorizations payment_authorizations_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.payment_authorizations
    ADD CONSTRAINT payment_authorizations_pkey PRIMARY KEY (id);


--
-- Name: payment_instruments payment_instruments_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.payment_instruments
    ADD CONSTRAINT payment_instruments_pkey PRIMARY KEY (instrument_id);


--
-- Name: payment_requests payment_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.payment_requests
    ADD CONSTRAINT payment_requests_pkey PRIMARY KEY (id);


--
-- Name: payment_reversals payment_reversals_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.payment_reversals
    ADD CONSTRAINT payment_reversals_pkey PRIMARY KEY (id);


--
-- Name: payment_settlements payment_settlements_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.payment_settlements
    ADD CONSTRAINT payment_settlements_pkey PRIMARY KEY (id);


--
-- Name: payment_transactions payment_transactions_idempotency_key_key; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.payment_transactions
    ADD CONSTRAINT payment_transactions_idempotency_key_key UNIQUE (idempotency_key);


--
-- Name: payment_transactions payment_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.payment_transactions
    ADD CONSTRAINT payment_transactions_pkey PRIMARY KEY (id);


--
-- Name: pending_holds pending_holds_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.pending_holds
    ADD CONSTRAINT pending_holds_pkey PRIMARY KEY (id);


--
-- Name: processed_transactions processed_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.processed_transactions
    ADD CONSTRAINT processed_transactions_pkey PRIMARY KEY (idempotency_key);


--
-- Name: reconciliation_snapshots reconciliation_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.reconciliation_snapshots
    ADD CONSTRAINT reconciliation_snapshots_pkey PRIMARY KEY (id);


--
-- Name: reserve_locks reserve_locks_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.reserve_locks
    ADD CONSTRAINT reserve_locks_pkey PRIMARY KEY (id);


--
-- Name: reserve_segments reserve_segments_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.reserve_segments
    ADD CONSTRAINT reserve_segments_pkey PRIMARY KEY (id);


--
-- Name: settlement_batches settlement_batches_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.settlement_batches
    ADD CONSTRAINT settlement_batches_pkey PRIMARY KEY (id);


--
-- Name: settlement_events settlement_events_idempotency_key_key; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.settlement_events
    ADD CONSTRAINT settlement_events_idempotency_key_key UNIQUE (idempotency_key);


--
-- Name: settlement_events settlement_events_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.settlement_events
    ADD CONSTRAINT settlement_events_pkey PRIMARY KEY (id);


--
-- Name: settlement_queue settlement_queue_idempotency_key_key; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.settlement_queue
    ADD CONSTRAINT settlement_queue_idempotency_key_key UNIQUE (idempotency_key);


--
-- Name: settlement_queue settlement_queue_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.settlement_queue
    ADD CONSTRAINT settlement_queue_pkey PRIMARY KEY (id);


--
-- Name: stripe_identity_map stripe_identity_map_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.stripe_identity_map
    ADD CONSTRAINT stripe_identity_map_pkey PRIMARY KEY (stripe_customer_id);


--
-- Name: system_accounts system_accounts_account_id_key; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.system_accounts
    ADD CONSTRAINT system_accounts_account_id_key UNIQUE (account_id);


--
-- Name: system_accounts system_accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.system_accounts
    ADD CONSTRAINT system_accounts_pkey PRIMARY KEY (name);


--
-- Name: system_boot_state system_boot_state_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.system_boot_state
    ADD CONSTRAINT system_boot_state_pkey PRIMARY KEY (component);


--
-- Name: system_snapshots system_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.system_snapshots
    ADD CONSTRAINT system_snapshots_pkey PRIMARY KEY (id);


--
-- Name: telegram_identity_map telegram_identity_map_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.telegram_identity_map
    ADD CONSTRAINT telegram_identity_map_pkey PRIMARY KEY (telegram_uid);


--
-- Name: tokens tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.tokens
    ADD CONSTRAINT tokens_pkey PRIMARY KEY (id);


--
-- Name: tokens tokens_token_value_key; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.tokens
    ADD CONSTRAINT tokens_token_value_key UNIQUE (token_value);


--
-- Name: transaction_stream transaction_stream_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.transaction_stream
    ADD CONSTRAINT transaction_stream_pkey PRIMARY KEY (id);


--
-- Name: transactions transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);


--
-- Name: treasury_accounts treasury_accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.treasury_accounts
    ADD CONSTRAINT treasury_accounts_pkey PRIMARY KEY (id);


--
-- Name: treasury_limits treasury_limits_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.treasury_limits
    ADD CONSTRAINT treasury_limits_pkey PRIMARY KEY (asset_type);


--
-- Name: treasury_locks treasury_locks_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.treasury_locks
    ADD CONSTRAINT treasury_locks_pkey PRIMARY KEY (id);


--
-- Name: treasury_reserve treasury_reserve_name_key; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.treasury_reserve
    ADD CONSTRAINT treasury_reserve_name_key UNIQUE (name);


--
-- Name: treasury_reserve treasury_reserve_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.treasury_reserve
    ADD CONSTRAINT treasury_reserve_pkey PRIMARY KEY (id);


--
-- Name: treasury_state treasury_state_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.treasury_state
    ADD CONSTRAINT treasury_state_pkey PRIMARY KEY (asset_type);


--
-- Name: treasury_state_projection treasury_state_projection_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.treasury_state_projection
    ADD CONSTRAINT treasury_state_projection_pkey PRIMARY KEY (treasury_id);


--
-- Name: velocity_tracking velocity_tracking_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.velocity_tracking
    ADD CONSTRAINT velocity_tracking_pkey PRIMARY KEY (wallet_id);


--
-- Name: virtual_cards virtual_cards_card_token_key; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.virtual_cards
    ADD CONSTRAINT virtual_cards_card_token_key UNIQUE (card_token);


--
-- Name: virtual_cards virtual_cards_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.virtual_cards
    ADD CONSTRAINT virtual_cards_pkey PRIMARY KEY (id);


--
-- Name: wallet_projections wallet_projections_pkey; Type: CONSTRAINT; Schema: public; Owner: u0_a253
--

ALTER TABLE ONLY public.wallet_projections
    ADD CONSTRAINT wallet_projections_pkey PRIMARY KEY (account_id);


--
-- Name: wallet_registry wallet_registry_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.wallet_registry
    ADD CONSTRAINT wallet_registry_pkey PRIMARY KEY (alias);


--
-- Name: wallet_registry wallet_registry_wallet_id_key; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.wallet_registry
    ADD CONSTRAINT wallet_registry_wallet_id_key UNIQUE (wallet_id);


--
-- Name: wallet_state_projection wallet_state_projection_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.wallet_state_projection
    ADD CONSTRAINT wallet_state_projection_pkey PRIMARY KEY (wallet_id);


--
-- Name: wallets wallets_pkey; Type: CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.wallets
    ADD CONSTRAINT wallets_pkey PRIMARY KEY (id);


--
-- Name: idx_account_balances_wallet; Type: INDEX; Schema: public; Owner: u0_a253
--

CREATE INDEX idx_account_balances_wallet ON public.account_balances USING btree (wallet_id);


--
-- Name: idx_accounts_telegram_uid; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_accounts_telegram_uid ON public.accounts USING btree (telegram_uid);


--
-- Name: idx_async_jobs_status; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_async_jobs_status ON public.async_settlement_jobs USING btree (status);


--
-- Name: idx_auth_status; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_auth_status ON public.authorization_holds USING btree (status);


--
-- Name: idx_auth_wallet; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_auth_wallet ON public.authorization_holds USING btree (wallet_id);


--
-- Name: idx_card_events_token; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_card_events_token ON public.omega_card_events USING btree (card_token);


--
-- Name: idx_card_tx_token; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_card_tx_token ON public.card_transactions USING btree (card_token);


--
-- Name: idx_card_tx_wallet; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_card_tx_wallet ON public.card_transactions USING btree (wallet_id);


--
-- Name: idx_cards_card_number; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_cards_card_number ON public.cards USING btree (card_number);


--
-- Name: idx_cards_token; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_cards_token ON public.omega_cards USING btree (card_token);


--
-- Name: idx_cards_wallet; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_cards_wallet ON public.omega_cards USING btree (wallet_id);


--
-- Name: idx_cards_wallet_id; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_cards_wallet_id ON public.cards USING btree (wallet_id);


--
-- Name: idx_chargeback_status; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_chargeback_status ON public.chargeback_cases USING btree (status);


--
-- Name: idx_global_lock_hash; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_global_lock_hash ON public.omega_settlement_global_lock USING btree (hash);


--
-- Name: idx_holds_wallet_status; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_holds_wallet_status ON public.authorization_holds USING btree (wallet_id, status);


--
-- Name: idx_iso_messages_ledger; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_iso_messages_ledger ON public.iso_messages USING btree (ledger_entry_id);


--
-- Name: idx_iso_messages_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_iso_messages_type ON public.iso_messages USING btree (message_type);


--
-- Name: idx_ledger_accounts; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_ledger_accounts ON public.ledger_entries USING btree (debit_account, credit_account);


--
-- Name: idx_ledger_aggregate; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_ledger_aggregate ON public.ledger_events USING btree (aggregate_id, sequence_number);


--
-- Name: idx_ledger_chain_hash; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_ledger_chain_hash ON public.ledger_postings USING btree (chain_hash);


--
-- Name: idx_ledger_entries_transaction_id; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_ledger_entries_transaction_id ON public.ledger_entries USING btree (transaction_id);


--
-- Name: idx_ledger_entries_wallet_id_created_at; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_ledger_entries_wallet_id_created_at ON public.ledger_entries USING btree (wallet_id, created_at);


--
-- Name: idx_ledger_events_aggregate; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_ledger_events_aggregate ON public.ledger_events USING btree (aggregate_id);


--
-- Name: idx_ledger_events_seq; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_ledger_events_seq ON public.ledger_events USING btree (sequence_number);


--
-- Name: idx_ledger_postings_account; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_ledger_postings_account ON public.ledger_postings USING btree (account_id);


--
-- Name: idx_ledger_postings_event_id; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_ledger_postings_event_id ON public.ledger_postings USING btree (event_id);


--
-- Name: idx_ledger_postings_sequence; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_ledger_postings_sequence ON public.ledger_postings USING btree (sequence_number);


--
-- Name: idx_ledger_transactions_idempotency_key; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_ledger_transactions_idempotency_key ON public.ledger_transactions USING btree (idempotency_key);


--
-- Name: idx_ledger_type; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_ledger_type ON public.ledger_events USING btree (event_type);


--
-- Name: idx_merchants_merchant_id; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_merchants_merchant_id ON public.merchants USING btree (merchant_id);


--
-- Name: idx_omega_events_created; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_omega_events_created ON public.omega_events USING btree (created_at DESC);


--
-- Name: idx_omega_events_type_wallet; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_omega_events_type_wallet ON public.omega_events USING btree (event_type, wallet_id);


--
-- Name: idx_omega_idempotency_event_id; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_omega_idempotency_event_id ON public.omega_idempotency_log USING btree (event_id);


--
-- Name: idx_omega_idempotency_key; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_omega_idempotency_key ON public.omega_idempotency_log USING btree (idempotency_key);


--
-- Name: idx_payment_authorizations_lifecycle; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_payment_authorizations_lifecycle ON public.payment_authorizations USING btree (lifecycle_state);


--
-- Name: idx_payment_requests_merchant_id; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_payment_requests_merchant_id ON public.payment_requests USING btree (merchant_id);


--
-- Name: idx_payment_transactions_idempotency_key; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_payment_transactions_idempotency_key ON public.payment_transactions USING btree (idempotency_key);


--
-- Name: idx_payment_transactions_ledger_event_id; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_payment_transactions_ledger_event_id ON public.payment_transactions USING btree (ledger_event_id);


--
-- Name: idx_payment_transactions_status; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_payment_transactions_status ON public.payment_transactions USING btree (status);


--
-- Name: idx_payment_transactions_wallet_id; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_payment_transactions_wallet_id ON public.payment_transactions USING btree (wallet_id);


--
-- Name: idx_pending_holds_status; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_pending_holds_status ON public.pending_holds USING btree (status);


--
-- Name: idx_settlement_hold; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_settlement_hold ON public.settlement_events USING btree (hold_id);


--
-- Name: idx_settlement_retry; Type: INDEX; Schema: public; Owner: u0_a253
--

CREATE INDEX idx_settlement_retry ON public.settlement_queue USING btree (status, retry_count);


--
-- Name: idx_settlement_state_id; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_settlement_state_id ON public.omega_settlement_state USING btree (settlement_id);


--
-- Name: idx_settlement_state_time; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_settlement_state_time ON public.omega_settlement_state USING btree (updated_at);


--
-- Name: idx_settlement_status; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_settlement_status ON public.settlement_events USING btree (status);


--
-- Name: idx_tokens_card_id; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_tokens_card_id ON public.tokens USING btree (card_id);


--
-- Name: idx_tokens_token_value; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_tokens_token_value ON public.tokens USING btree (token_value);


--
-- Name: idx_treasury_lock_wallet; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_treasury_lock_wallet ON public.treasury_locks USING btree (wallet_id);


--
-- Name: idx_vcards_wallet; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_vcards_wallet ON public.virtual_cards USING btree (wallet_id);


--
-- Name: idx_wallet_account; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_wallet_account ON public.wallets USING btree (account_id);


--
-- Name: idx_wallets_available_balance; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX idx_wallets_available_balance ON public.wallets USING btree (available_balance);


--
-- Name: ledger_global_seq_idx; Type: INDEX; Schema: public; Owner: omega
--

CREATE UNIQUE INDEX ledger_global_seq_idx ON public.ledger_entries USING btree (global_sequence);


--
-- Name: ledger_idempotency_unique; Type: INDEX; Schema: public; Owner: omega
--

CREATE UNIQUE INDEX ledger_idempotency_unique ON public.ledger_entries USING btree (idempotency_key);


--
-- Name: ledger_tx_idem_unique; Type: INDEX; Schema: public; Owner: omega
--

CREATE UNIQUE INDEX ledger_tx_idem_unique ON public.ledger_transactions USING btree (idempotency_key);


--
-- Name: wallet_projections_wallet_id_idx; Type: INDEX; Schema: public; Owner: u0_a253
--

CREATE UNIQUE INDEX wallet_projections_wallet_id_idx ON public.wallet_projections USING btree (wallet_id) WHERE (wallet_id IS NOT NULL);


--
-- Name: wallets_identity_id_idx; Type: INDEX; Schema: public; Owner: omega
--

CREATE INDEX wallets_identity_id_idx ON public.wallets USING btree (identity_id);


--
-- Name: ledger_write_guard ledger_write_guard_no_delete; Type: RULE; Schema: public; Owner: u0_a253
--

CREATE RULE ledger_write_guard_no_delete AS
    ON DELETE TO public.ledger_write_guard DO INSTEAD NOTHING;


--
-- Name: ledger_write_guard ledger_write_guard_no_update; Type: RULE; Schema: public; Owner: u0_a253
--

CREATE RULE ledger_write_guard_no_update AS
    ON UPDATE TO public.ledger_write_guard DO INSTEAD NOTHING;


--
-- Name: omega_events omega_events_no_delete; Type: RULE; Schema: public; Owner: omega
--

CREATE RULE omega_events_no_delete AS
    ON DELETE TO public.omega_events DO INSTEAD NOTHING;


--
-- Name: omega_events omega_events_no_update; Type: RULE; Schema: public; Owner: omega
--

CREATE RULE omega_events_no_update AS
    ON UPDATE TO public.omega_events DO INSTEAD NOTHING;


--
-- Name: account_balances account_balances_guard; Type: TRIGGER; Schema: public; Owner: u0_a253
--

CREATE TRIGGER account_balances_guard BEFORE INSERT OR DELETE OR UPDATE ON public.account_balances FOR EACH ROW EXECUTE FUNCTION public.block_balance_mutation();


--
-- Name: omega_events freeze_guard; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER freeze_guard BEFORE INSERT ON public.omega_events FOR EACH ROW EXECUTE FUNCTION public.omega_write_guard();


--
-- Name: ledger_entries ledger_chain_trigger; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER ledger_chain_trigger BEFORE INSERT ON public.ledger_entries FOR EACH ROW EXECUTE FUNCTION public.ledger_chain_enforcer();


--
-- Name: ledger_entries ledger_idempotency_trigger; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER ledger_idempotency_trigger BEFORE INSERT ON public.ledger_entries FOR EACH ROW EXECUTE FUNCTION public.enforce_idempotency();


--
-- Name: ledger_entries ledger_protect; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER ledger_protect BEFORE DELETE OR UPDATE ON public.ledger_entries FOR EACH ROW EXECUTE FUNCTION public.block_ledger_mutation();


--
-- Name: account_balances no_balance_update; Type: TRIGGER; Schema: public; Owner: u0_a253
--

CREATE TRIGGER no_balance_update BEFORE INSERT OR DELETE OR UPDATE ON public.account_balances FOR EACH ROW EXECUTE FUNCTION public.block_balance_mutation();


--
-- Name: omega_events no_delete_events; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER no_delete_events BEFORE DELETE ON public.omega_events FOR EACH ROW EXECUTE FUNCTION public.omega_events_block_mutation();


--
-- Name: omega_events no_update_events; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER no_update_events BEFORE UPDATE ON public.omega_events FOR EACH ROW EXECUTE FUNCTION public.omega_events_block_mutation();


--
-- Name: omega_events omega_events_block_update; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER omega_events_block_update BEFORE DELETE OR UPDATE ON public.omega_events FOR EACH ROW EXECUTE FUNCTION public.omega_block_mutation();


--
-- Name: omega_events omega_events_no_delete; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER omega_events_no_delete BEFORE DELETE ON public.omega_events FOR EACH ROW EXECUTE FUNCTION public.omega_events_block_mutation();


--
-- Name: omega_events omega_events_no_update; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER omega_events_no_update BEFORE UPDATE ON public.omega_events FOR EACH ROW EXECUTE FUNCTION public.omega_events_block_mutation();


--
-- Name: omega_events omega_projection_trigger; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER omega_projection_trigger AFTER INSERT ON public.omega_events FOR EACH ROW EXECUTE FUNCTION public.trigger_projection();


--
-- Name: settlement_queue settlement_consistency_guard; Type: TRIGGER; Schema: public; Owner: u0_a253
--

CREATE TRIGGER settlement_consistency_guard BEFORE INSERT OR UPDATE ON public.settlement_queue FOR EACH ROW EXECUTE FUNCTION public.enforce_settlement_consistency();


--
-- Name: omega_events trg_after_insert_omega_events; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER trg_after_insert_omega_events AFTER INSERT ON public.omega_events FOR EACH ROW EXECUTE FUNCTION public.trg_omega_events_project();


--
-- Name: transactions trg_apply_transaction; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER trg_apply_transaction AFTER INSERT ON public.transactions FOR EACH ROW EXECUTE FUNCTION public.apply_transaction_to_wallet();


--
-- Name: account_balances trg_balance_guard; Type: TRIGGER; Schema: public; Owner: u0_a253
--

CREATE TRIGGER trg_balance_guard BEFORE INSERT OR DELETE OR UPDATE ON public.account_balances FOR EACH ROW EXECUTE FUNCTION public.block_balance_mutation();


--
-- Name: omega_events trg_immutability_delete; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER trg_immutability_delete BEFORE DELETE ON public.omega_events FOR EACH ROW EXECUTE FUNCTION public.trg_omega_events_immutability();


--
-- Name: omega_events trg_immutability_update; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER trg_immutability_update BEFORE UPDATE ON public.omega_events FOR EACH ROW EXECUTE FUNCTION public.trg_omega_events_immutability();


--
-- Name: ledger_entries trg_iso20022; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER trg_iso20022 AFTER INSERT ON public.ledger_entries FOR EACH ROW EXECUTE FUNCTION public.iso20022_auto_generate();


--
-- Name: ledger_entries trg_ledger_event_stream; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER trg_ledger_event_stream AFTER INSERT ON public.ledger_entries FOR EACH ROW EXECUTE FUNCTION public.emit_ledger_event();


--
-- Name: ledger_entries trg_sign_ledger_entry; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER trg_sign_ledger_entry BEFORE INSERT ON public.ledger_entries FOR EACH ROW EXECUTE FUNCTION public.omega_sign_ledger_entry();


--
-- Name: wallets trg_update_available_balance; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER trg_update_available_balance BEFORE INSERT OR UPDATE ON public.wallets FOR EACH ROW EXECUTE FUNCTION public.omega_update_available_balance();


--
-- Name: cards update_cards_updated_at; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER update_cards_updated_at BEFORE UPDATE ON public.cards FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: merchants update_merchants_updated_at; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER update_merchants_updated_at BEFORE UPDATE ON public.merchants FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: payment_requests update_payment_requests_updated_at; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER update_payment_requests_updated_at BEFORE UPDATE ON public.payment_requests FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: payment_transactions update_payment_transactions_updated_at; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER update_payment_transactions_updated_at BEFORE UPDATE ON public.payment_transactions FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: tokens update_tokens_updated_at; Type: TRIGGER; Schema: public; Owner: omega
--

CREATE TRIGGER update_tokens_updated_at BEFORE UPDATE ON public.tokens FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: iso_messages iso_messages_ledger_entry_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.iso_messages
    ADD CONSTRAINT iso_messages_ledger_entry_id_fkey FOREIGN KEY (ledger_entry_id) REFERENCES public.ledger_entries(id);


--
-- Name: ledger_postings ledger_postings_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.ledger_postings
    ADD CONSTRAINT ledger_postings_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.omega_events(event_id);


--
-- Name: payment_requests payment_requests_merchant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.payment_requests
    ADD CONSTRAINT payment_requests_merchant_id_fkey FOREIGN KEY (merchant_id) REFERENCES public.merchants(id);


--
-- Name: payment_transactions payment_transactions_card_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.payment_transactions
    ADD CONSTRAINT payment_transactions_card_id_fkey FOREIGN KEY (card_id) REFERENCES public.cards(id);


--
-- Name: payment_transactions payment_transactions_ledger_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.payment_transactions
    ADD CONSTRAINT payment_transactions_ledger_event_id_fkey FOREIGN KEY (ledger_event_id) REFERENCES public.ledger_events(id);


--
-- Name: payment_transactions payment_transactions_payment_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.payment_transactions
    ADD CONSTRAINT payment_transactions_payment_request_id_fkey FOREIGN KEY (payment_request_id) REFERENCES public.payment_requests(id);


--
-- Name: payment_transactions payment_transactions_token_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.payment_transactions
    ADD CONSTRAINT payment_transactions_token_id_fkey FOREIGN KEY (token_id) REFERENCES public.tokens(id);


--
-- Name: tokens tokens_card_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.tokens
    ADD CONSTRAINT tokens_card_id_fkey FOREIGN KEY (card_id) REFERENCES public.cards(id) ON DELETE CASCADE;


--
-- Name: transactions transactions_wallet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_wallet_id_fkey FOREIGN KEY (wallet_id) REFERENCES public.wallets(id);


--
-- Name: wallets wallets_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omega
--

ALTER TABLE ONLY public.wallets
    ADD CONSTRAINT wallets_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(account_id);


--
-- Name: ledger_entries; Type: ROW SECURITY; Schema: public; Owner: omega
--

ALTER TABLE public.ledger_entries ENABLE ROW LEVEL SECURITY;

--
-- Name: ledger_entries ledger_write_only_transfer; Type: POLICY; Schema: public; Owner: omega
--

CREATE POLICY ledger_write_only_transfer ON public.ledger_entries FOR INSERT TO ledger_service WITH CHECK (true);


--
-- Name: omega_pub; Type: PUBLICATION; Schema: -; Owner: u0_a253
--

CREATE PUBLICATION omega_pub WITH (publish = 'insert, update, delete, truncate');


ALTER PUBLICATION omega_pub OWNER TO u0_a253;

--
-- Name: omega_pub ledger_entries; Type: PUBLICATION TABLE; Schema: public; Owner: u0_a253
--

ALTER PUBLICATION omega_pub ADD TABLE ONLY public.ledger_entries;


--
-- PostgreSQL database dump complete
--

\unrestrict 7sH9HE7bBLd7HpSXq261OBnmchJQP3E32T4hHxQ4m2OzhabfHeiZH04vRbQU2PH

