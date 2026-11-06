import fs from 'node:fs/promises';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {command,museStatus,ROOT} from './production.mjs';

async function discover(){
 if(process.env.SIBERIA_MUSE_URL)return (await museStatus(process.env.SIBERIA_MUSE_URL)).base;
 const script=`$ErrorActionPreference='SilentlyContinue'; $ps=Get-Process | Where-Object {$_.ProcessName -eq 'Muse AI Studio'}; $ports=@(); foreach($p in $ps){ if($p.Path){ $f=Join-Path (Split-Path $p.Path) 'resources\\app\\.data\\muse-desktop\\studio-port'; if(Test-Path -LiteralPath $f){ $n=Get-Content -LiteralPath $f; if($n -match '^\\d+$'){$ports+= [int]$n} } } }; $ids=@($ps | ForEach-Object {$_.Id}); if($ids.Count){$ports+= @(Get-NetTCPConnection -State Listen | Where-Object {$_.OwningProcess -in $ids -and $_.LocalAddress -eq '127.0.0.1'} | ForEach-Object {$_.LocalPort})}; ConvertTo-Json -Compress -InputObject @($ports | Sort-Object -Unique)`;
 const result=await command('powershell.exe',['-NoProfile','-NonInteractive','-Command',script],{capture:true});
 const ports=JSON.parse(result.stdout.trim()||'[]');
 for(const port of ports){
  try{return (await museStatus('http://127.0.0.1:'+port)).base;}catch{}
 }
 throw Error('Mo Muse AI Studio 1.6.0, dang nhap Muse 01 va bam Kiem tra phien, roi chay lai.');
}
try{
 const operation=process.argv[2]||'all';
 const args=[path.join(ROOT,'production.mjs'),operation];
 if(['all','generate','check'].includes(operation)){
  const base=await discover();console.log('Muse cua ban: '+base);args.push('--base-url',base);
 }
 args.push(...process.argv.slice(3));
 const child=spawn(process.execPath,args,{cwd:ROOT,stdio:'inherit',windowsHide:false,env:process.env});
 child.on('exit',code=>{process.exitCode=code??1;});child.on('error',e=>{console.error(e.message);process.exitCode=1;});
}catch(e){console.error(e.message);process.exitCode=1;}
