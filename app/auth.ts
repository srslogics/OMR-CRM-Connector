import { getDb } from '../db';
import { cookies } from 'next/headers';
export const authDb=getDb;
export const OWNER_PHONE='9665821832';
export const OWNER_EMAIL='srslogics@gmail.com';
export const IDLE_MS=15*60*1000;
const encoder=new TextEncoder();
export async function audit(actor:{userId:string,name:string}|null,event:string){await authDb().prepare('INSERT INTO activity_log(actor_id,actor_name,event) VALUES(?,?,?)').bind(actor?.userId||null,actor?.name||'Unknown account',event).run()}

export function normalizePhone(value:unknown){if(typeof value!=='string')throw Error('Enter a valid mobile number.');let s=value.replace(/[\s()+-]/g,'');if(s.length===12&&s.startsWith('91'))s=s.slice(2);if(!/^[6-9]\d{9}$/.test(s))throw Error('Enter a valid 10-digit mobile number.');return s}
function hex(bytes:ArrayBuffer|Uint8Array){return Array.from(new Uint8Array(bytes)).map(b=>b.toString(16).padStart(2,'0')).join('')}
export async function digest(value:string){return hex(await crypto.subtle.digest('SHA-256',encoder.encode(value)))}
export async function hashPassword(password:string,salt=hex(crypto.getRandomValues(new Uint8Array(16)))){const key=await crypto.subtle.importKey('raw',encoder.encode(password),'PBKDF2',false,['deriveBits']);const result=await crypto.subtle.deriveBits({name:'PBKDF2',salt:encoder.encode(salt),iterations:100000,hash:'SHA-256'},key,256);return `pbkdf2$100000$${salt}$${hex(result)}`}
export function validPassword(v:unknown):asserts v is string{if(typeof v!=='string'||v.length<10||v.length>128)throw Error('Use a password with 10 to 128 characters.')}
export async function checkPassword(password:string,stored:string){const parts=stored.split('$');if(parts.length!==4)return false;const result=await hashPassword(password,parts[2]);let diff=result.length^stored.length;for(let i=0;i<result.length;i++)diff|=result.charCodeAt(i)^stored.charCodeAt(i);return diff===0}
export async function getSession(){const jar=await cookies();const token=jar.get('__Host-srs_session')?.value||jar.get('srs_session')?.value;if(!token)return null;return await authDb().prepare('SELECT a.id AS "userId",a.phone,a.name,a.role FROM auth_sessions s JOIN auth_accounts a ON a.id=s.account_id WHERE s.token_hash=? AND s.expires_at>? AND s.last_active_at>? AND a.active=1').bind(await digest(token),Date.now(),Date.now()-IDLE_MS).first<{userId:string,phone:string,name:string,role:string}>()}
export async function sessionResponse(accountId:string,req:Request){const token=hex(crypto.getRandomValues(new Uint8Array(32)));await authDb().prepare('INSERT INTO auth_sessions(token_hash,account_id,expires_at,last_active_at) VALUES(?,?,?,?) ON CONFLICT(account_id) DO UPDATE SET token_hash=excluded.token_hash,expires_at=excluded.expires_at,last_active_at=excluded.last_active_at').bind(await digest(token),accountId,Date.now()+7*86400000,Date.now()).run();const actor=await authDb().prepare('SELECT id AS "userId",name FROM auth_accounts WHERE id=?').bind(accountId).first<{userId:string,name:string}>();await audit(actor,'Signed in — previous session replaced');const secure=process.env.NODE_ENV==='production';return Response.json({ok:true},{headers:{'Cache-Control':'no-store','Set-Cookie':`${secure?'__Host-srs_session':'srs_session'}=${token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=604800${secure?'; Secure':''}`}})}
export function requireOrigin(req:Request){const origin=req.headers.get('origin');if(!origin||origin!==(process.env.APP_URL||process.env.RENDER_EXTERNAL_URL||new URL(req.url).origin).replace(/\/$/,''))throw Error('Request origin not allowed.')}

export async function touchSession(){const jar=await cookies();const token=jar.get('__Host-srs_session')?.value||jar.get('srs_session')?.value;if(!token)return false;const now=Date.now();const row=await authDb().prepare('UPDATE auth_sessions SET last_active_at=? WHERE token_hash=? AND expires_at>? AND last_active_at>? RETURNING account_id').bind(now,await digest(token),now,now-IDLE_MS).first();return !!row}
