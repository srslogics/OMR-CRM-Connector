import nextEnv from '@next/env';
const {loadEnvConfig}=nextEnv;
import { spawn } from 'node:child_process';
loadEnvConfig(process.cwd());
const {migrate}=await import('./migrate-postgres.mjs');
await migrate();
const child=spawn(process.execPath,['node_modules/next/dist/bin/next','start','--hostname','0.0.0.0','--port',process.env.PORT||'3000'],{stdio:'inherit',env:process.env});
for(const signal of ['SIGTERM','SIGINT'])process.on(signal,()=>child.kill(signal));
child.on('exit',code=>process.exit(code??1));
