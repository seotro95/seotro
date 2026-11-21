export class MediaQueue {
  constructor(limit?:number);
  run<T>(work:()=>Promise<T>,signal?:AbortSignal):Promise<T>;
  snapshot():{active:number;queued:number;limit:number};
}
export const mediaQueue:MediaQueue;
