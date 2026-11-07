/** Finish the English soundtrack while Muse visuals await a connected session. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {command,tools,probe,digest,verifyWav,createScore,mixAudio} from './kit/production.mjs';

const base=path.dirname(fileURLToPath(import.meta.url));
const out=path.resolve('audio-master');await fs.mkdir(out,{recursive:true});
const work=path.resolve('audio-master-work');await fs.mkdir(work,{recursive:true});
const repo=process.env.GITHUB_REPOSITORY;
if(!repo)throw Error('GITHUB_REPOSITORY must identify the owner repository.');
await command('gh',['release','download','siberia-2536-production-v1','--repo',repo,
 '--pattern','en.wav','--pattern','en-report.json','--dir',work,'--clobber']);
const master=JSON.parse(await fs.readFile(path.join(base,'master_timeline.json'),'utf8'));
const sourceReport=JSON.parse(await fs.readFile(path.join(work,'en-report.json'),'utf8'));
const voice=path.join(work,'en.wav'),voiceHash=await digest(voice);
if(voiceHash!==sourceReport.audio_sha256||master.target_seconds!==1536)throw Error('Finalized English source failed verification.');
const {ffmpeg,ffprobe}=await tools();
await verifyWav(voice,1536,ffprobe);
const score=path.join(work,'original-score.wav');
console.log('Composing full-length original ambient bed and chapter transition sweeps...');
await createScore(score,1536,master.chapters);
const mixed=path.join(out,'Siberia_EN_FINAL_MIX_25m36.wav');
console.log('Mixing and ducking the background beneath the narration...');
await mixAudio({voice,score,output:mixed,seconds:1536,ffmpeg,root:work});
const music=path.join(out,'Siberia_MUSIC_FX_25m36.flac');
await command(ffmpeg,['-hide_banner','-loglevel','error','-y','-i',score,'-c:a','flac','-compression_level','8',music]);
const mp3=path.join(out,'Siberia_EN_FINAL_MIX_25m36.mp3');
await command(ffmpeg,['-hide_banner','-loglevel','error','-y','-i',mixed,'-c:a','libmp3lame','-b:a','192k',mp3]);
async function measure(file){
 const r=await command(ffmpeg,['-hide_banner','-nostats','-i',file,'-af','loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json','-f','null','-'],{capture:true});
 const block=r.stderr.match(/\{\s*"input_i"[\s\S]*?\}/g)?.at(-1);
 if(!block)throw Error('Audio measurement failed.');
 const m=JSON.parse(block);return {integrated_lufs:Number(m.input_i),true_peak_dbtp:Number(m.input_tp),loudness_range_lu:Number(m.input_lra)};
}
const tracks=[];
for(const file of [mixed,music]){
 const info=await probe(file,ffprobe),s=info.streams.find(s=>s.codec_type==='audio');
 const [n,d]=s.time_base.split('/').map(Number),frames=Number(s.duration_ts)*n*48000/d;
 if(s.channels!==2||Number(s.sample_rate)!==48000||frames!==73728000)throw Error('Lossless master sample count mismatch: '+path.basename(file));
 tracks.push({file:path.basename(file),channels:2,sample_rate:48000,sample_frames:frames,seconds:1536,sha256:await digest(file)});
}
const wavMeasurement=await measure(mixed),mp3Measurement=await measure(mp3);
if(Math.abs(wavMeasurement.integrated_lufs+16)>.5||wavMeasurement.true_peak_dbtp> -1)throw Error('Lossless master failed the loudness check.');
if(Math.abs(mp3Measurement.integrated_lufs+16)>.7||mp3Measurement.true_peak_dbtp> -.8)throw Error('Encoded listening copy failed the loudness check.');
const report={verified_utc:new Date().toISOString(),duration_seconds:1536,scope:'Finished audio soundtrack only; no Muse media or completed video included.',
 source_english_wav_sha256:voiceHash,source_voice:sourceReport.selected_voice_metadata,
 music:'Original deterministic ambient composition and transition sweeps, synthesized by the included production helper; no source-video music copied.',
 narration_ducking:true,lossless_tracks:tracks,wav_loudness:wavMeasurement,mp3_loudness:mp3Measurement,
 mp3:{file:path.basename(mp3),sha256:await digest(mp3),note:'Listening copy; use the lossless WAV for exact editing.'},
 muse_visuals_included:false,completed_video_included:false};
await fs.writeFile(path.join(out,'AUDIO_MASTER_QA.json'),JSON.stringify(report,null,2),'utf8');
await fs.writeFile(path.join(out,'AUDIO_README_VI.md'),`# Âm thanh bản chính tiếng Anh · 25:36

- **Siberia_EN_FINAL_MIX_25m36.wav**: giọng Anh đã phối nhạc nền và tiếng chuyển chương, stereo PCM16, 48 kHz, đúng 25:36. Dùng tệp này với phần hình cùng timeline.
- **Siberia_EN_FINAL_MIX_25m36.mp3**: bản nghe thử.
- **Siberia_MUSIC_FX_25m36.flac**: nhạc và hiệu ứng riêng, nén không mất dữ liệu, đúng 25:36. Có thể phối với các giọng quốc gia đã xuất; đây là nền trước khi ducking theo lời.
- **AUDIO_MASTER_QA.json**: số mẫu, checksum và số đo âm lượng thực tế.

Các giọng riêng từng ngôn ngữ vẫn được giữ nguyên. Bản âm thanh này không chứa hình ảnh và không phải MP4 đã hoàn tất. Cần media thật từ phiên Muse đã đăng nhập để ghép phần hình.
`,'utf8');
let checks='';
for(const name of (await fs.readdir(out)).sort())if(name!=='AUDIO_SHA256SUMS.txt')checks+=await digest(path.join(out,name))+'  '+name+'\n';
await fs.writeFile(path.join(out,'AUDIO_SHA256SUMS.txt'),checks,'utf8');
await command('gh',['release','upload','siberia-2536-production-v1','--repo',repo,...(await fs.readdir(out)).map(n=>path.join(out,n)),'--clobber']);
console.log(JSON.stringify(report,null,2));
