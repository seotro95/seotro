const messages = {
  loading: 'Đang mở giao diện Studio…',
  ready: 'Studio đã sẵn sàng.',
  STUDIO_TIMEOUT: 'Giao diện Studio chưa khởi động xong. Bấm Tải lại Studio để thử lại.',
  STUDIO_LOAD_FAILED: 'Không tải được giao diện Studio trên máy này.',
  STUDIO_RENDERER_EXITED: 'Tiến trình giao diện Studio đã dừng.',
  STUDIO_RENDERER_OUT_OF_MEMORY: 'Tiến trình Studio đã hết bộ nhớ. Thử Khôi phục Studio để mở mà chưa tải thư viện cũ.',
  STUDIO_PRELOAD_FAILED: 'Không tải được cầu nối giao diện Studio.',
  STUDIO_RENDER_FAILED: 'Giao diện Studio gặp lỗi khi hiển thị.',
};

// Diagnostics deliberately contain no URLs, file paths, prompts, or account data.
export class StudioStartup {
  constructor({ onChange, timeout = 20000 }) {
    this.onChange = onChange;
    this.timeout = timeout;
    this.state = { phase: 'loading', code: 'loading', message: messages.loading };
    this.listeners = [];
  }
  snapshot() { return { ...this.state, stage: this.stage || 'navigation', ...(this.lastExit ? { lastExit: { ...this.lastExit } } : {}) }; }
  setStage(stage) {
    if (!['navigation','bootstrap','workspace','interface','media-library','ready'].includes(stage)) return;
    if (this.state.phase === 'error') return;
    this.stage = stage;
    this.onChange(this.snapshot());
  }
  change(phase, code) {
    clearTimeout(this.timer);
    this.state = { phase, code, message: messages[code] };
    this.onChange(this.snapshot());
  }
  loading() {
    this.stage = 'navigation';
    this.change('loading', 'loading');
    this.timer = setTimeout(() => this.fail('STUDIO_TIMEOUT'), this.timeout);
    this.timer.unref?.();
  }
  ready() {
    // A late ready event may recover a slow load, but not a crashed renderer.
    if (this.state.phase !== 'error' || this.state.code === 'STUDIO_TIMEOUT') this.change('ready', 'ready');
  }
  fail(code) {
    if (!Object.hasOwn(messages, code) || !code.startsWith('STUDIO_')) code = 'STUDIO_RENDER_FAILED';
    this.change('error', code);
  }
  observe(contents) {
    const listen = (event, handler) => { contents.on(event, handler); this.listeners.push(() => contents.removeListener(event, handler)); };
    listen('did-start-navigation', (_event, _url, inPlace, mainFrame) => { if (mainFrame && !inPlace) this.loading(); });
    listen('did-fail-load', (_event, code, _description, _url, mainFrame) => { if (mainFrame && code !== -3) this.fail('STUDIO_LOAD_FAILED'); });
    listen('preload-error', () => this.fail('STUDIO_PRELOAD_FAILED'));
    listen('render-process-gone', (_event, details) => {
      const reason = ['clean-exit','abnormal-exit','killed','crashed','oom','launch-failed','integrity-failure','memory-eviction'].includes(details?.reason) ? details.reason : 'unknown';
      const exitCode = Number.isInteger(details?.exitCode) && details.exitCode >= -2147483648 && details.exitCode <= 4294967295 ? details.exitCode : null;
      this.lastExit = { reason, exitCode, exitCodeHex: exitCode === null ? null : `0x${(exitCode >>> 0).toString(16).padStart(8,'0').toUpperCase()}`, stage: this.stage || 'navigation' };
      this.fail(reason === 'oom' ? 'STUDIO_RENDERER_OUT_OF_MEMORY' : 'STUDIO_RENDERER_EXITED');
    });
    listen('destroyed', () => this.dispose());
  }
  dispose() { clearTimeout(this.timer); for (const remove of this.listeners.splice(0)) remove(); }
}
