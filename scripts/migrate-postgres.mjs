import { readFile } from 'node:fs/promises';
import { getPool } from '../db/postgres/pool.mjs';
export async function migrate(){const pool=getPool();const client=await pool.connect();try{await client.query('BEGIN');await client.query("SELECT pg_advisory_xact_lock(88491273)");await client.query(await readFile(new URL('../db/postgres/001_initial.sql',import.meta.url),'utf8'));await client.query('COMMIT');console.log('Database schema is ready.')}catch(e){await client.query('ROLLBACK');console.error('Database initialization failed:',e.code||'connection error');throw new Error('Database initialization failed. Check database configuration.')}finally{client.release();await pool.end()}}
if(process.argv[1]?.endsWith('migrate-postgres.mjs'))await migrate();
