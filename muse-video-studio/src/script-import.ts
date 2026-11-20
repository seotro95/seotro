import { outputStem } from '../output-names.mjs';
export type ScriptEntry = { prompt: string; outputName?: string };
const timestamp = /^\s*\d{1,2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{1,2}:\d{2}:\d{2}[,.]\d{3}.*$/;
const nameLabel = /^(?:\[\s*)?(?:t[eê]n\s*(?:(?:ảnh|anh|video|t[eệ]p|file)(?:\s*[/&]\s*(?:ảnh|anh|video))?)?|file\s*name|filename|output\s*name|name|title|(?:tiêu\s*đề|tieu\s*de))\s*[:=]\s*(.+?)(?:\s*\])?$/i;
function headingEntries(text:string):ScriptEntry[]|undefined {
  // Character dossiers have numbered parent titles and nested render prompts.
  // Nested voice descriptions and identity notes are metadata, not render jobs.
  const bracketed=[...text.matchAll(/^[ \t]*\[[ \t]*(\d+)[ \t]*\][ \t]*([^\n]+)$/gm)];
  const numbered=[...text.matchAll(/^\s*(\d+)[.)]\s+([^\n]+)$/gm)];
  const headings=bracketed.length?bracketed:numbered.filter(match=>match[2].length<180&&!/^\[?TIMELINE\b|^(?:PROMPT|MO TA GIONG|TEN THONG)/i.test(match[2].normalize('NFD').replace(/\p{M}/gu,'')));
  if(!headings.length)return undefined;
  const result:ScriptEntry[]=[];
  for(const [index,heading] of headings.entries()){
    const title=heading[2].trim();
    const body=text.slice(heading.index!+heading[0].length,headings[index+1]?.index??text.length).replace(/^[\s=\-]+|[\s=\-]+$/g,'').trim();
    if(!body)return undefined; // One-line prompt lists keep the legacy parser.
    const subheads=[...body.matchAll(/^\s*\d+[.)]\s+([^\n]+)$/gm)];
    const renders=subheads.filter(match=>/^(?:PROMPT|VIDEO PROMPT|IMAGE PROMPT)\b/i.test(match[1]));
    if(renders.length){
      for(const render of renders){
        const next=subheads.find(match=>match.index!>render.index!);
        const prompt=body.slice(render.index!+render[0].length,next?.index??body.length).replace(/^[\s=]+|[\s=]+$/g,'').trim();
        if(!prompt)continue;
        const suffix=render[1].replace(/^(?:VIDEO |IMAGE )?PROMPT\s*/i,'').split(/\s+[—–]\s+|\s*\(/)[0].replace(/[:：]+$/,'').trim();
        const entry=extractScriptEntry(prompt);
        result.push({...entry,outputName:outputStem(`${title}${renders.length>1?` — ${suffix||'Prompt'}`:''}`)});
      }
    }else{
      const entry=extractScriptEntry(body);
      result.push({...entry,outputName:entry.outputName||outputStem(title)});
    }
  }
  return result.length?result:undefined;
}
export function extractScriptEntry(block: string): ScriptEntry {
  const lines = block.trim().split('\n');
  let outputName = '';
  const body: string[] = [];
  for (const [index, raw] of lines.entries()) {
    let line = raw.trim();
    if (!index) line = line.replace(/^\s*(?:#?\d+[.)\-:]|[-•])\s+/, '');
    const inline = line.match(/^(.+?)\s*\|\s*(?:prompt|nội\s*dung)\s*:\s*(.+)$/i);
    const named = line.match(nameLabel);
    const file = line.match(/^([^<>:"/\\|?*\n]+\.(?:png|jpe?g|webp|mp4|webm|mov))\s*(?::|\||—|–)\s*(.+)$/i);
    if (!outputName && inline && nameLabel.test(inline[1])) {
      outputName = outputStem(inline[1].match(nameLabel)![1]); body.push(inline[2]);
    } else if (!outputName && named) outputName = outputStem(named[1]);
    else if (!outputName && file) { outputName = outputStem(file[1]); body.push(file[2]); }
    else if (!index && /^#{1,6}\s+/.test(line) && lines.length > 1) outputName = outputStem(line.replace(/^#{1,6}\s+/, ''));
    else body.push(line.replace(/^(?:prompt|nội\s*dung)\s*:\s*/i, ''));
  }
  return { prompt: body.join('\n').trim(), ...(outputName ? { outputName } : {}) };
}
export function parseScriptEntries(text: string): ScriptEntry[] {
  const normalized = text.replace(/^\uFEFF/, '').replace(/\r\n?/g, '\n').trim();
  if (!normalized) return [];
  if (normalized.split('\n').some(line => timestamp.test(line))) {
    const blocks: string[] = []; let current: string[] = []; let inCue = false;
    const flush = () => { if (current.length) blocks.push(current.join('\n')); current = []; };
    for (const line of normalized.split('\n')) {
      if (timestamp.test(line)) { flush(); inCue = true; continue; }
      if (!line.trim()) { flush(); inCue = false; continue; }
      if (!inCue || /^\d+$/.test(line.trim())) continue;
      current.push(line.replace(/<[^>]*>/g, '').trim());
    }
    flush();
    return blocks.flatMap(block=>headingEntries(block)||[extractScriptEntry(block)]).map(entry => ({...entry, prompt: entry.prompt.replace(/\n+/g, ' ')})).filter(entry => entry.prompt);
  }
  const named=headingEntries(normalized);if(named)return named;
  const paragraphs = normalized.split(/\n\s*\n/);
  const hasMetadata = normalized.split('\n').some(line => nameLabel.test(line.replace(/^\s*\d+[.)]\s+/, '')));
  const blocks = paragraphs.length > 1 ? paragraphs : hasMetadata
    ? normalized.split(/\n(?=\s*(?:\d+[.)]\s+|(?:Tên\s*(?:ảnh|anh|video|t[eệ]p|file)|Filename|File name|Name|Title)\s*[:=]))/i)
    : normalized.split('\n');
  return blocks.map(extractScriptEntry).filter(entry => entry.prompt);
}
