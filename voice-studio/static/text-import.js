/* Decode local text files before subtitle parsing; keep the user's words intact. */
async function readScriptFileText(file){
  if(!file||typeof file.arrayBuffer!=='function')throw Error('Chọn tệp TXT hoặc SRT cần nhập.');
  const bytes=new Uint8Array(await file.arrayBuffer());
  let encoding='utf-8',offset=0;
  if(bytes.length>=3&&bytes[0]===0xef&&bytes[1]===0xbb&&bytes[2]===0xbf)offset=3;
  else if(bytes.length>=2&&bytes[0]===0xff&&bytes[1]===0xfe){encoding='utf-16le';offset=2;}
  else if(bytes.length>=2&&bytes[0]===0xfe&&bytes[1]===0xff){encoding='utf-16be';offset=2;}
  else if(bytes.length>=4&&bytes.length%2===0){
    // Windows can save UTF-16 without a BOM. Recognize only a clear byte
    // pattern from ordinary Latin/RPA text; do not guess a legacy code page.
    const pairs=Math.min(bytes.length/2,2048);
    let even=0,odd=0;
    for(let i=0;i<pairs;i++){if(bytes[i*2]===0)even++;if(bytes[i*2+1]===0)odd++;}
    if(odd/pairs>.6&&even/pairs<.2)encoding='utf-16le';
    else if(even/pairs>.6&&odd/pairs<.2)encoding='utf-16be';
  }
  if(encoding.startsWith('utf-16')&&(bytes.length-offset)%2!==0)throw Error('Tệp UTF-16 chưa đầy đủ. Lưu lại tệp ở UTF-8 hoặc UTF-16 rồi nhập lại.');
  let text;
  try{text=new TextDecoder(encoding,{fatal:true}).decode(bytes.subarray(offset));}
  catch(e){throw Error('Không đọc được mã hóa tệp. Lưu TXT/SRT ở UTF-8 hoặc UTF-16 rồi nhập lại; lời đang soạn được giữ nguyên.');}
  if(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(text))throw Error('Tệp có dữ liệu không phải văn bản. Lưu TXT/SRT ở UTF-8 hoặc UTF-16 rồi nhập lại; lời đang soạn được giữ nguyên.');
  return text.replace(/^\uFEFF/,'');
}
