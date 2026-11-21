export const MAX_SLOTS: 400;
export const DEFAULT_SLOTS: 10;
export const STREAM_OPTIONS: readonly number[];
export function isSlotCount(value: unknown): value is number;
export const MAX_ACCOUNTS: 40;
export const MAX_ACCOUNT_LANES: 10;
export function isAccountId(value: unknown): value is number;
export function isLaneCount(value: unknown): value is number;

export const RENDER_TIMEOUT_MS: 240000;
export const UI_WAIT_LIMIT_MS: 250000;
export const LOCAL_RENDER_TIMEOUT_MS: 245000;
