// Run after intern-access.mjs against the same disposable test workspace.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {getPool} from '../db/postgres/pool.mjs';
const base=process.env.TEST_BASE_URL;
const schema=process.env.SRS_DB_SCHEMA;
if(!base||!schema?.startsWith('srs_')||!schema.endsWith('_test')||!/^[a-z_]+$/.test(schema))throw Error('A disposable *_test schema and TEST_BASE_URL are required.');
async function request(path,body,cookie){const r=await fetch(base+path,{method:body?'POST':'GET',headers:{Origin:base,'Content-Type':'application/json',...(cookie?{Cookie:cookie}:{})},...(body?{body:JSON.stringify(body)}:{})});return {status:r.status,cookie:r.headers.get('set-cookie')?.split(';')[0],data:await r.json()}}
const login=()=>request('/api/auth',{action:'login',phone:'9999999999',password:'Disposable-test-2026'});
const first=await login(),second=await login();assert.equal(first.status,200);assert.equal(second.status,200);
assert.equal((await request('/api/workspace',null,first.cookie)).status,401);
assert.equal((await request('/api/auth',null,second.cookie)).status,200);
const hash=createHash('sha256').update(second.cookie.split('=')[1]).digest('hex');
const pool=getPool();
try{
 await pool.query(`UPDATE ${schema}.auth_sessions SET last_active_at=$1 WHERE token_hash=$2`,[Date.now()-14*60000,hash]);
 assert.equal((await request('/api/auth',{action:'activity'},second.cookie)).status,200);
 const renewed=await pool.query(`SELECT last_active_at FROM ${schema}.auth_sessions WHERE token_hash=$1`,[hash]);assert.ok(Number(renewed.rows[0].last_active_at)>Date.now()-10000);
 await pool.query(`UPDATE ${schema}.auth_sessions SET last_active_at=$1 WHERE token_hash=$2`,[Date.now()-16*60000,hash]);
 for(const [path,body] of [['/api/auth',null],['/api/auth',{action:'activity'}],['/api/workspace',null]])assert.equal((await request(path,body,second.cookie)).status,401);
 const owner=await request('/api/auth',{action:'login',phone:'9665821832',password:'Disposable-test-2026'});
 const result=await request('/api/workspace',null,owner.cookie);assert.equal(result.status,200);
 for(const event of ['Submitted student record','Blocked records download','Blocked submitted-record edit','Blocked record review','Downloaded records CSV','Signed in — previous session replaced'])assert.ok(result.data.activity.some(r=>r.event===event),event);
 assert.ok(!JSON.stringify(result.data.activity).includes('Disposable-test-2026'));
 const fresh=await login();const restricted=await request('/api/workspace',null,fresh.cookie);assert.equal(restricted.data.activity,undefined);
 console.log('PASS: previous session revoked, active session renewed, idle session rejected and cannot revive, owner audit history, intern audit denied.');
}finally{await pool.end()}
