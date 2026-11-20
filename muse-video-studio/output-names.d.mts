export function outputStem(value: unknown): string;
export function uniqueOutputFilename(stem: string, extension: string, used: Set<string>): string;
export function validOutputFilename(name: unknown, kind: string): boolean;
