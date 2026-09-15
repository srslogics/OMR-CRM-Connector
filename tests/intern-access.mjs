// Run only against a disposable test workspace with no existing owner.
import assert from 'node:assert/strict';
const base=process.env.TEST_BASE_URL;
const setupKey=process.env.TEST_SETUP_KEY;
if(!base||!setupKey)throw Error('Set TEST_BASE_URL and TEST_SETUP_KEY for a disposable workspace.');
async function request(path,body,cookie){const res=await fetch(base+path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json',Origin:base,...(cookie?{Cookie:cookie}:{})},...(body?{body:JSON.stringify(body)}:{})});return {status:res.status,cookie:res.headers.get('set-cookie')?.split(';')[0],data:res.headers.get('content-type')?.includes('json')?await res.json():await res.text()}}
const password='Disposable-test-2026';
const owner=await request('/api/auth',{action:'setup',phone:'9665821832',password,setupKey});assert.equal(owner.status,200);
assert.equal((await request('/api/auth',{action:'account',phone:'9999999999',name:'Test Intern',password},owner.cookie)).status,200);
const intern=await request('/api/auth',{action:'login',phone:'9999999999',password});assert.equal(intern.status,200);
const record={action:'save',id:crypto.randomUUID(),name:'Test Student',school:'Test School',fatherPhone:'8888888888',motherPhone:'',className:'10',marks:'87.5'};
assert.equal((await request('/api/workspace',record,intern.cookie)).status,200);
for(const path of ['/api/workspace','/api/workspace?q=Test&class=10']){const r=await request(path,null,intern.cookie);assert.equal(r.status,200);assert.deepEqual(r.data.records,[]);assert.deepEqual(r.data.members,[]);assert.ok(!JSON.stringify(r.data).includes('8888888888'));}
assert.equal((await request('/api/workspace?export=csv',null,intern.cookie)).status,403);
assert.equal((await request('/api/workspace',{...record,name:'Unauthorized edit'},intern.cookie)).status,403);
assert.equal((await request('/api/workspace',{action:'review',id:record.id,status:'Reviewed'},intern.cookie)).status,403);
const visible=await request('/api/workspace',null,owner.cookie);assert.equal(visible.data.records.length,1);assert.equal(visible.data.records[0].name,'Test Student');assert.equal(Number(visible.data.records[0].marks),87.5);
assert.equal((await request('/api/workspace',{...record,id:crypto.randomUUID(),marks:'invalid'},intern.cookie)).status,400);
assert.equal((await request('/api/workspace',{...record,name:'Owner correction',marks:0},owner.cookie)).status,200);
const csv=await request('/api/workspace?export=csv',null,owner.cookie);assert.equal(csv.status,200);assert.ok(csv.data.includes('Owner correction'));assert.ok(csv.data.includes('Marks'));assert.ok(csv.data.includes('"0"'));
assert.equal((await request('/api/workspace',{...record,marks:''},owner.cookie)).status,200);assert.equal((await request('/api/workspace',null,owner.cookie)).data.records[0].marks,null);
assert.equal((await request('/api/workspace')).status,401);
console.log('PASS: intern submission, no saved lead retrieval, export/edit/review denied, owner read/edit/export, anonymous denied.');
