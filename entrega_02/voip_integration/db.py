import os
import psycopg2
from psycopg2.extras import RealDictCursor
from config import settings

def get_conn():
    return psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD
    )

def insert_buffer(call_uuid, raw_payload):
    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO voip_call_buffer (call_uuid, raw_payload)
                VALUES (%s, %s)
                ON CONFLICT (call_uuid) DO NOTHING
                RETURNING id;
            """, (call_uuid, raw_payload))
            return cur.fetchone()
