const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const src=fs.readFileSync(__dirname+'/static/app.js','utf8'),ctx={};vm.createContext(ctx);
vm.runInContext(src.slice(src.indexOf('function markSummary('),src.indexOf('function updateScore(')),ctx);
assert.match(ctx.markSummary({total:0,unresolved:25},'review'),/Pending review/);
assert.doesNotMatch(ctx.markSummary({total:0,unresolved:25},'review'),/>0 \/100/);
assert.match(ctx.markSummary({total:0,unresolved:0},'approved'),/0 \/100/);
assert.match(ctx.markSummary({total:12,unresolved:15},'review'),/incomplete/);
assert.match(ctx.markSummary({total:12,unresolved:0},'review'),/Provisional/);
console.log('Uncertain zero, genuine approved zero and incomplete subtotal display passed.');
