const slot={type:'integer',minimum:1,maximum:40};
const ids={type:'array',items:slot,minItems:1,maxItems:40,uniqueItems:true};
const output={type:'string',enum:['image','video']};
const uuid={type:'string',pattern:'^[a-fA-F0-9-]{36}$'};
const requestId={type:'string',pattern:'^[-a-zA-Z0-9_.]{1,128}$',description:'Mã riêng cho một yêu cầu; gửi lại cùng mã để không tạo thêm một bộ.'};
const object=properties=>({type:'object',properties,additionalProperties:false});
const entry=(name,title,description,properties,action,annotations={},required=[])=>({name,title,description,inputSchema:{...object(properties),...(required.length?{required}:{})},annotations:{readOnlyHint:false,destructiveHint:false,openWorldHint:false,...annotations},action});
const definitions=[
  entry('studio_status','Đọc trạng thái Studio','Đọc bố cục, prompt, số luồng yêu cầu/thực tế, tài khoản đã xác minh, tiến độ và media. Gọi trước khi thao tác.',{},'status',{readOnlyHint:true,idempotentHint:true}),
  entry('studio_configure_layout','Chọn số ô và chế độ','Thay đổi bố cục từ 1 đến 40 ô, số luồng yêu cầu, một/nhiều tài khoản và ảnh/video. Không tạo nội dung. Đợi tác vụ đang chạy trước khi đổi.',{slotCount:slot,requestedConcurrency:slot,accountMode:{type:'string',enum:['single','multiple']},output},'configure-layout',{idempotentHint:true}),
  entry('studio_set_scene','Sửa một ô','Sửa prompt, bật/tắt ô hoặc gán ảnh đã lưu qua sourceMediaId. sourceMediaId:null gỡ ảnh. Không nhập mật khẩu/OTP/cookie. Có thể mở thêm ô khi đang rảnh.',{sceneId:slot,prompt:{type:'string',maxLength:8000},enabled:{type:'boolean'},sourceMediaId:{anyOf:[uuid,{type:'null'}]}},'set-scene',{idempotentHint:true},['sceneId']),
  entry('studio_create_batch','Nhập và tạo bộ ảnh/video','Nạp 1–40 prompt hoặc script TXT/SRT rồi bắt đầu bộ. Studio phải rảnh, tài khoản Muse phải đăng nhập. Có thể tính phí Muse. Dùng requestId riêng để tránh tạo trùng; poll studio_status theo batchId. settings.mode=demo chỉ trả tệp mẫu có nhãn.',{output,prompts:{type:'array',items:{type:'string',minLength:1,maxLength:8000},minItems:1,maxItems:40},script:{type:'string',maxLength:2097152},sceneIds:ids,settings:{type:'object',description:'accountMode, requestedConcurrency, slotCount, model, aspectRatio, duration, resolution, imageResolution, videoInput, r2v, autoSync, modifier, mode; xem API-AUTOMATION.md.'},referenceImage:{type:'object',properties:{mimeType:{type:'string',enum:['image/png','image/jpeg','image/webp']},base64:{type:'string',maxLength:11200000}},required:['mimeType','base64'],additionalProperties:false},sourceMediaId:uuid,requestId},'batch',{openWorldHint:true}),
  entry('studio_run','Bấm tạo các ô đã nhập','Bắt đầu/tạo lại các ô đang bật, có prompt và tài khoản sẵn sàng. Không thay prompt của các ô khác. Bỏ sceneIds để chạy các ô còn thiếu kết quả. Có thể tính phí Muse; dùng requestId để tránh lặp.',{sceneIds:ids,output,requestId},'run',{openWorldHint:true}),
  entry('studio_stop','Dừng một ô hoặc cả bộ','Có sceneId: dừng ô đó. Bỏ sceneId: dừng cả bộ. Muse có thể đã nhận/tính phí cho yêu cầu trước khi dừng.',{sceneId:slot},'stop',{idempotentHint:true,openWorldHint:true}),
  entry('studio_list_media','Đọc thư viện kết quả','Liệt kê ID, batchId, loại, kích thước và đường dẫn tải của ảnh/video đã lưu. Không tạo lại nội dung.',{},'media-list',{readOnlyHint:true,idempotentHint:true}),
  entry('studio_save_results','Lưu ảnh/video về máy','Lưu các kết quả vào thư mục thường đã chọn trong Studio, dùng cùng bộ đếm tên tệp. Có thể lọc batchId, output và sceneIds. Lần đầu cần người dùng chọn Thư mục lưu trong Studio. Không gửi byte video lớn vào hội thoại.',{batchId:uuid,output,sceneIds:ids},'save-media'),
  entry('studio_clear_library','Xóa thư viện tool','Xóa toàn bộ kết quả/lịch sử trong tool, giữ prompt, tài khoản, ảnh tham chiếu và tệp đã xuất ra thư mục ngoài. Chỉ gọi khi người dùng yêu cầu xóa, sau khi tạo/tải đã xong.',{confirm:{type:'string',const:'DELETE_ALL_MEDIA'}},'clear-media',{destructiveHint:true,idempotentHint:true},['confirm']),
];
export const mcpTools=definitions.map(({action,...tool})=>tool);
const result=(id,value)=>({status:200,body:{jsonrpc:'2.0',id,result:value}});
const error=(id,code,message)=>({status:200,body:{jsonrpc:'2.0',id,error:{code,message}}});

export async function mcpResponse(message,{version,invoke}) {
  if(!message||Array.isArray(message)||message.jsonrpc!=='2.0'||typeof message.method!=='string')return error(message?.id??null,-32600,'Invalid JSON-RPC request');
  if(message.id===undefined)return {status:202,body:null};
  if(!['string','number'].includes(typeof message.id))return error(null,-32600,'Request id must be a string or number');
  const {id,method}=message;
  if(method==='initialize'){
    const supported=['2025-03-26','2025-06-18','2025-11-25'];const requested=message.params?.protocolVersion;
    return result(id,{protocolVersion:supported.includes(requested)?requested:supported[0],capabilities:{tools:{listChanged:false}},serverInfo:{name:'muse-ai-studio',version},instructions:'Bạn đang điều khiển Muse AI Studio trên cùng máy tính. Đọc studio_status trước. Chỉ tạo/xóa theo yêu cầu người dùng. Số ô không bảo đảm Muse render đồng thời; đọc executionConcurrency và cảnh báo. Dùng requestId riêng cho mỗi lệnh tạo. Nếu timeout/quota, đọc trạng thái trước khi thử lại. Tài khoản đăng nhập trực tiếp trong Studio; không yêu cầu mật khẩu, OTP, cookie hoặc token. Chọn Thư mục lưu trong Studio một lần rồi dùng studio_save_results.'});
  }
  if(method==='ping')return result(id,{});
  if(method==='tools/list')return result(id,{tools:mcpTools});
  if(method!=='tools/call')return error(id,-32601,'Method not found');
  const definition=definitions.find(tool=>tool.name===message.params?.name);
  if(!definition)return error(id,-32602,'Unknown tool');
  const args=message.params?.arguments??{};
  try{
    if(!args||typeof args!=='object'||Array.isArray(args)||Object.keys(args).some(key=>!Object.hasOwn(definition.inputSchema.properties,key))||(definition.inputSchema.required||[]).some(key=>args[key]===undefined))throw Object.assign(new Error('Tool arguments do not match its schema.'),{status:400});
    if(definition.action==='clear-media'&&args.confirm!=='DELETE_ALL_MEDIA')throw Object.assign(new Error('Cần confirm: DELETE_ALL_MEDIA.'),{status:400});
    const {requestId,...data}=args;const value=await invoke(definition.action,data,requestId);
    return result(id,{content:[{type:'text',text:JSON.stringify(value)}],structuredContent:value,isError:false});
  }catch(failure){return result(id,{content:[{type:'text',text:String(failure.message||'Studio request failed').slice(0,1000)}],structuredContent:{status:Number.isInteger(failure.status)?failure.status:500,error:String(failure.message||'Studio request failed').slice(0,1000)},isError:true});}
}
