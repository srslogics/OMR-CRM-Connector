const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const src=fs.readFileSync(__dirname+'/static/app.js','utf8');
let finish,calls=0,renders=0;
const ctx={document:{hidden:false},page:'batch',batch:{id:'first',status:'processing'},api:()=>{calls++;return new Promise(resolve=>{finish=resolve})},renderBatch:()=>renders++};
vm.createContext(ctx);vm.runInContext(src.slice(src.indexOf('let batchPollBusy='),src.indexOf('setInterval(refreshBatchProgress')),ctx);
(async()=>{
 const pending=ctx.refreshBatchProgress();await ctx.refreshBatchProgress();assert.equal(calls,1);
 ctx.page='review';finish({id:'first',status:'ready'});await pending;assert.equal(renders,0);
 ctx.page='batch';ctx.document.hidden=true;await ctx.refreshBatchProgress();assert.equal(calls,1);
 ctx.document.hidden=false;const next=ctx.refreshBatchProgress();finish({id:'first',status:'ready'});await next;assert.equal(renders,1);
 await ctx.refreshBatchProgress();assert.equal(calls,2);
 console.log('Polling overlap, navigation, hidden tab and completed batch checks passed.');
})().catch(e=>{console.error(e);process.exitCode=1});
