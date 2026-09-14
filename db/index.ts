import { getPool } from './postgres/pool.mjs';
// Preserve prepared-query call sites while binding all values through PostgreSQL.
class Statement {
 constructor(public sql:string,public values:unknown[]=[]){ }
 bind(...values:unknown[]){return new Statement(this.sql,values)}
 async run(){return getPool().query(this.sql,this.values)}
 async first<T=Record<string,unknown>>():Promise<T|null>{const r=await this.run();return (r.rows[0] as T)||null}
 async all(){const r=await this.run();return {results:r.rows}}
}
const schema=process.env.SRS_DB_SCHEMA||'srs_records';
if(!/^[a-z_][a-z0-9_]*$/.test(schema))throw new Error('Invalid database schema');
const tables=['ownership','members','records','auth_accounts','auth_sessions','auth_attempts','activity_log'];
export function getDb(){return {
 prepare(sql:string){let n=0;let text=sql.replace(/\?/g,()=>`$${++n}`);for(const table of tables)text=text.replace(new RegExp(`\\b(FROM|JOIN|INTO|UPDATE)\\s+${table}\\b`,'gi'),`$1 ${schema}.${table}`);return new Statement(text)},
 async batch(statements:Statement[]){const client=await getPool().connect();try{await client.query('BEGIN');const results=[];for(const s of statements)results.push(await client.query(s.sql,s.values));await client.query('COMMIT');return results}catch(e){await client.query('ROLLBACK');throw e}finally{client.release()}}
}}
