const publicSegments = new Set(['api','auth','login','signin','sign-in','sign-up','email','email-otp','otp','code','send','send-code','request','verify','verify-email','verify-otp','confirm','callback','session','check','status','logout']);
const methods = new Set(['GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS']);

export function loginRecorder(serviceURL) {
  const service = new URL(serviceURL);
  const events = [];
  function route(raw) {
    try {
      const url = new URL(raw);
      const same = url.origin === service.origin;
      const subdomain = service.protocol === 'https:' && url.protocol === 'https:' && url.hostname.endsWith(`.${service.hostname}`);
      if (!same && !subdomain) return null;
      const path = '/' + url.pathname.split('/').filter(Boolean).slice(0,8).map(part => {
        try { const word = decodeURIComponent(part).toLowerCase(); return publicSegments.has(word) ? word : '[ẩn]'; } catch { return '[ẩn]'; }
      }).join('/');
      return { origin: same ? service.origin : '*.muse.ai', route: path };
    } catch { return null; }
  }
  function append(details, failed = false) {
    const safe = route(details.url);
    if (!safe || (!/auth|otp|verify|login|signin|session|callback|code/i.test(new URL(details.url).pathname) && details.resourceType !== 'mainFrame')) return;
    const event = { time: new Date().toISOString(), ...safe, method: methods.has(details.method) ? details.method : 'OTHER' };
    if (failed) event.error = /^net::ERR_[A-Z0-9_]+$/.test(details.error || '') ? details.error : 'NETWORK_ERROR';
    else {
      event.status = Number.isInteger(details.statusCode) && details.statusCode >= 100 && details.statusCode <= 599 ? details.statusCode : null;
      // Only the existence of this header is recorded. Never read its values.
      event.setCookie = Object.keys(details.responseHeaders || {}).some(key => key.toLowerCase() === 'set-cookie');
    }
    events.push(event); if (events.length > 24) events.shift();
  }
  return {
    completed: details => append(details),
    failed: details => append(details,true),
    snapshot: ({ version, loginVisible, account }) => ({ version, loginVisible: Boolean(loginVisible), state: typeof account?.state === 'string' ? account.state : 'disconnected', verified: Boolean(account?.sessionAuthenticated ?? account?.authenticated), events: events.map(event => ({ ...event })) }),
  };
}
