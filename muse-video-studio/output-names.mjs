// Shared Windows-safe names for renderer downloads and the native export gate.
export function outputStem(value) {
  if (typeof value !== 'string') return '';
  let name = value.normalize('NFC').trim().replace(/^["'`]+|["'`]+$/g, '')
    .replace(/\.(png|jpe?g|webp|mp4|webm|mov)$/i, '')
    .replace(/[<>:"/\\|?*\x00-\x1f\x7f]/g, '_').replace(/\s+/g, ' ')
    .replace(/^[. ]+|[. ]+$/g, '');
  name = Array.from(name).slice(0, 120).join('').replace(/[. ]+$/g, '');
  if (/^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(name)) name = '_' + name;
  return name;
}
export function uniqueOutputFilename(stem, extension, used) {
  let name = `${stem}.${extension}`;
  for (let n = 2; used.has(name.toLowerCase()); n++) name = `${stem} (${n}).${extension}`;
  used.add(name.toLowerCase());
  return name;
}
export function validOutputFilename(name, kind) {
  if (typeof name !== 'string' || name.length > 200) return false;
  const match = /^(.*)\.(png|mp4|webm|mov)$/.exec(name);
  return Boolean(match && match[1] && outputStem(match[1]) === match[1] &&
    (kind === 'image' ? match[2] === 'png' : ['mp4', 'webm', 'mov'].includes(match[2])));
}
