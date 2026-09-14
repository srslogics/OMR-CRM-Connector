import { env } from 'cloudflare:workers';
import { cookies } from 'next/headers';
export function authDb(){if(!env.DB)throw new Error('Storage unavailable');return env.DB}
export const OWNER_PHONE='9665821832';
export const OWNER_EMAIL='srslogics@gmail.com';
const encoder=new TextEncoder();
export function normalizePhone(value:unknown){if(typeof value!=='string')throw Error('Enter a valid mobile number.');let s=value.replace(/[\s()+-]/g,'');if(s.length===12&&s.startsWith('91'))s=s.slice(2);if(!/^[6-9]\d{9}$/.test(s))throw Error('Enter a valid 10-digit mobile number.');return s}
function hex(bytes:ArrayBuffer|Uint8Array){return Array.from(new Uint8Array(bytes)).map(b=>b.toString(16).padStart(2,'0')).join('')}
export async function digest(value:string){return hex(await crypto.subtle.digest('SHA-256',encoder.encode(value)))}
export async function hashPassword(password:string,salt=hex(crypto.getRandomValues(new Uint8Array(16)))){const key=await crypto.subtle.importKey('raw',encoder.encode(password),'PBKDF2',false,['deriveBits']);const result=await crypto.subtle.deriveBits({name:'PBKDF2',salt:encoder.encode(salt),iterations:100000,hash:'SHA-256'},key,256);return `pbkdf2$100000$${salt}$${hex(result)}`}
export function validPassword(v:unknown):asserts v is string{if(typeof v!=='string'||v.length<10||v.length>128)throw Error('Use a password with 10 to 128 characters.')}
export async function checkPassword(password:string,stored:string){const parts=stored.split('$');if(parts.length!==4)return false;const result=await hashPassword(password,parts[2]);let diff=result.length^stored.length;for(let i=0;i<result.length;i++)diff|=result.charCodeAt(i)^stored.charCodeAt(i);return diff===0}
export async function getSession(){const jar=await cookies();const token=jar.get('__Host-srs_session')?.value||jar.get('srs_session')?.value;if(!token)return null;return await authDb().prepare('SELECT a.id AS userId,a.phone,a.name,a.role FROM auth_sessions s JOIN auth_accounts a ON a.id=s.account_id WHERE s.token_hash=? AND s.expires_at>? AND a.active=1').bind(await digest(token),Date.now()).first<{userId:string,phone:string,name:string,role:string}>()}
export async function sessionResponse(accountId:string,req:Request){const token=hex(crypto.getRandomValues(new Uint8Array(32)));await authDb().prepare('INSERT INTO auth_sessions(token_hash,account_id,expires_at) VALUES(?,?,?)').bind(await digest(token),accountId,Date.now()+7*86400000).run();const secure=new URL(req.url).protocol==='https:';return Response.json({ok:true},{headers:{'Cache-Control':'no-store','Set-Cookie':`${secure?'__Host-srs_session':'srs_session'}=${token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=604800${secure?'; Secure':''}`}})}
export function requireOrigin(req:Request){const origin=req.headers.get('origin');if(origin!==new URL(req.url).origin)throw Error('Request origin not allowed.')}
