class PcmProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.inRate = sampleRate;
    this.outRate = 16000;
    this.ratio = this.inRate / this.outRate;
    this.pos = 0;
  }

  process(inputs) {
    const input = inputs[0] && inputs[0][0];
    if (!input || input.length === 0) return true;

    const out = [];
    let i = this.pos;
    while (i < input.length) {
      out.push(input[Math.floor(i)]);
      i += this.ratio;
    }
    this.pos = i - input.length;

    const int16 = new Int16Array(out.length);
    for (let j = 0; j < out.length; j++) {
      const s = Math.max(-1, Math.min(1, out[j]));
      int16[j] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }

    this.port.postMessage(int16.buffer, [int16.buffer]);
    return true;
  }
}

registerProcessor("pcm-processor", PcmProcessor);
