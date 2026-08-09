class MihiMuraPcmCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.targetRate = 16000;
    this.chunkMs = 100;
    this.pending = [];
    this.pendingLength = 0;
    this.nativeChunkSize = Math.max(128, Math.round(sampleRate * this.chunkMs / 1000));
  }

  flushChunk() {
    if (this.pendingLength < this.nativeChunkSize) return;

    const input = new Float32Array(this.pendingLength);
    let offset = 0;
    for (const part of this.pending) {
      input.set(part, offset);
      offset += part.length;
    }

    this.pending = [];
    this.pendingLength = 0;

    const ratio = sampleRate / this.targetRate;
    const outputLength = Math.max(1, Math.floor(input.length / ratio));
    const pcm = new Int16Array(outputLength);

    for (let i = 0; i < outputLength; i += 1) {
      const sourceIndex = i * ratio;
      const left = Math.floor(sourceIndex);
      const right = Math.min(left + 1, input.length - 1);
      const frac = sourceIndex - left;
      const sample = input[left] * (1 - frac) + input[right] * frac;
      const clipped = Math.max(-1, Math.min(1, sample));
      pcm[i] = clipped < 0 ? clipped * 0x8000 : clipped * 0x7fff;
    }

    this.port.postMessage(pcm.buffer, [pcm.buffer]);
  }

  process(inputs) {
    const channel = inputs[0]?.[0];
    if (!channel || !channel.length) return true;
    this.pending.push(new Float32Array(channel));
    this.pendingLength += channel.length;
    this.flushChunk();
    return true;
  }
}

registerProcessor('mihimura-pcm-capture', MihiMuraPcmCaptureProcessor);
