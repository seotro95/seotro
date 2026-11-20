// Only classify completed assistant replies, never the submitted scene prompt.
// A visible user message acknowledges delivery; it is not a render/job receipt.
export function replyProblem(text) {
  const value=String(text||'').replace(/\bMUSE_[a-f0-9]{32}\b/g,'').trim();
  if(!value)return null;
  if(/too many (?:active|parallel|simultaneous)|only one (?:generation|request|video)[\s\S]{0,35}at (?:a|one) time|already (?:generating|processing)[\s\S]{0,50}(?:wait|finish)|chỉ (?:được|có thể)[\s\S]{0,35}một[\s\S]{0,35}(?:mỗi lần|tại một thời điểm)/i.test(value))return 'MUSE_PARALLEL_LIMIT';
  if(/(?:please|could you|can you)\s+(?:clarify|provide|describe|explain)|(?:don't|do not|cannot|can't)\s+understand|vui lòng\s*(?:mô tả|làm rõ|cung cấp)|không\s*hiểu/i.test(value))return 'MUSE_PROMPT_CLARIFICATION';
  if(/(?:would you like|shall I|should I|do you want me to)|(?:please|need (?:you )?to)\s+confirm|(?:bạn có muốn|bạn muốn tôi|vui lòng xác nhận|cần bạn xác nhận|hãy xác nhận)/i.test(value))return 'MUSE_ACTION_REQUIRED';
  if(/(?:can't|cannot|unable to|not able to|do not have access to|don't have access to)[\s\S]{0,100}(?:generat|creat|render|video|image)|(?:không thể|không hỗ trợ|chưa hỗ trợ|không có quyền)[\s\S]{0,100}(?:tạo|video|hình ảnh|mô hình)|(?:model|mô hình)[\s\S]{0,70}(?:unavailable|not available|not supported|không có sẵn|không khả dụng)/i.test(value))return 'MUSE_GENERATION_REFUSED';
  if(/(?:quota|credit|balance)[\s\S]{0,70}(?:exhausted|insufficient|not enough)|(?:insufficient|not enough)[\s\S]{0,50}(?:credit|balance)|(?:không đủ|hết)[\s\S]{0,30}(?:credit|tín dụng|số dư)/i.test(value))return 'MUSE_GENERATION_REFUSED';
  return null;
}

export function replyPreview(text) {
  return String(text||'').replace(/\bMUSE_[a-f0-9]{32}\b/g,'[mã cảnh]').replace(/studio-request-[a-f0-9-]+/g,'[mã gửi]')
    .replace(/(?:https?:\/\/|blob:)[^\s<>"']+/gi,'[đường dẫn]')
    .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi,'[email]').slice(-1600);
}
