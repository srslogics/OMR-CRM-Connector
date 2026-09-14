import pg from 'pg';
import {readFileSync} from 'node:fs';
import {join} from 'node:path';
let pool;
export function getPool(){
 if(!process.env.DATABASE_URL)throw new Error('DATABASE_URL is required');
 if(!pool){const url=new URL(process.env.DATABASE_URL);url.searchParams.delete('sslmode');url.searchParams.delete('ssl');pool=new pg.Pool({connectionString:url.toString(),ssl:{rejectUnauthorized:true,ca:readFileSync(join(process.cwd(),'db/postgres/supabase-ca.crt'),'utf8')},max:5,connectionTimeoutMillis:15000,idleTimeoutMillis:30000});}
 return pool;
}
