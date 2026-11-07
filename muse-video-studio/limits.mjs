export const MAX_SLOTS = 40;
export const DEFAULT_SLOTS = 10;
export const STREAM_OPTIONS = Object.freeze([1, 2, 3, 5, 10, 20, 30, 40]);
export const isSlotCount = value => Number.isInteger(value) && value >= 1 && value <= MAX_SLOTS;
