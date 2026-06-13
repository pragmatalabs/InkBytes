/* InkWall — WebGL1 calligraphic ink / smoke shader engine for InkBytes.
 *
 * Vendored from the design-prototype `ink-shader.js` (Shader wallpapers) and
 * adapted for React/Next: the original auto-started a single global rAF loop
 * over InkWall.all; this version is per-instance with explicit start()/destroy()
 * so a component (the daily splash) can spin it up on mount and fully release
 * the WebGL context on unmount.
 *
 * A curl-noise velocity field advects a scalar ink-density field stored in a
 * ping-pong half-float texture. The display pass maps density through a
 * per-palette colour ramp with grain + vignette. Pointer drag stirs the field
 * and injects ink; a drifting ambient emitter keeps it flowing when idle.
 */
/* eslint-disable */

const QUAD = new Float32Array([-1, -1, 3, -1, -1, 3]);

const NOISE = `
float hash(vec2 p){ p=fract(p*vec2(123.34,345.45)); p+=dot(p,p+34.345); return fract(p.x*p.y); }
float vnoise(vec2 p){
  vec2 i=floor(p), f=fract(p);
  float a=hash(i), b=hash(i+vec2(1.0,0.0)), c=hash(i+vec2(0.0,1.0)), d=hash(i+vec2(1.0,1.0));
  vec2 u=f*f*(3.0-2.0*f);
  return mix(mix(a,b,u.x),mix(c,d,u.x),u.y);
}
float fbm(vec2 p){
  float v=0.0, a=0.55; mat2 m=mat2(1.6,1.2,-1.2,1.6);
  for(int i=0;i<5;i++){ v+=a*vnoise(p); p=m*p; a*=0.5; }
  return v;
}`;

const VERT = `
attribute vec2 aPos;
varying vec2 vUv;
void main(){ vUv=aPos*0.5+0.5; gl_Position=vec4(aPos,0.0,1.0); }`;

const SIM = `
precision highp float;
varying vec2 vUv;
uniform sampler2D uPrev;
uniform vec2 uRes;
uniform float uTime, uSpeed, uDissip, uFlow, uInit;
uniform vec2 uMouse, uMouseVel; uniform float uMouseStr;
uniform vec2 uEmit, uEmit2; uniform float uEmitStr, uAmbient;
${NOISE}

vec2 curl(vec2 p){
  float e=0.018;
  float xp=fbm(p+vec2(e,0.0)), xm=fbm(p-vec2(e,0.0));
  float yp=fbm(p+vec2(0.0,e)), ym=fbm(p-vec2(0.0,e));
  return vec2((yp-ym), -(xp-xm))/(2.0*e);
}

void main(){
  float asp = uRes.x/uRes.y;
  vec2 uv = vUv;
  vec2 p = vec2(uv.x*asp, uv.y);

  if(uInit > 0.5){
    float f = fbm(p*3.2 + 11.0);
    float g = fbm(p*1.7 - 5.0);
    float ribbon = smoothstep(0.46,0.5,abs(fbm(p*2.4+vec2(f,g)*1.4)-0.5)*1.0);
    float d = (1.0-ribbon)*0.6*smoothstep(0.0,0.25,uv.y)*smoothstep(1.0,0.75,uv.y);
    gl_FragColor = vec4(d*0.7,0.0,0.0,d);
    return;
  }

  vec2 fp = p*uFlow + vec2(0.0, uTime*0.06);
  vec2 vel = curl(fp) * 1.0;
  vel += curl(fp*2.1 + 7.0) * 0.35;

  vec2 dm = (uv-uMouse)*vec2(asp,1.0);
  float md = exp(-dot(dm,dm)*42.0);
  vel += uMouseVel * md * 26.0;

  vec2 prevUv = uv - vel * uSpeed;
  vec4 prev = texture2D(uPrev, prevUv);
  vec4 col = prev * uDissip;

  // primary drifting emitter → alpha (the indigo ink stream)
  vec2 de = (uv-uEmit)*vec2(asp,1.0);
  float ed = exp(-dot(de,de)*78.0);
  ed *= 0.62 + 0.38*fbm(p*6.0 + uTime*0.3);
  col.a += ed * uEmitStr;

  // secondary drifting emitter on a different path → green channel (warm ink)
  vec2 de2 = (uv-uEmit2)*vec2(asp,1.0);
  float ed2 = exp(-dot(de2,de2)*88.0);
  ed2 *= 0.60 + 0.40*fbm(p*5.5 - uTime*0.26 + 14.0);
  col.g += ed2 * uEmitStr;

  // ambient flowing ribbons — primary + a phase-shifted secondary
  float amb = smoothstep(0.48, 0.82, fbm(p*1.7 + vec2(uTime*0.05, uTime*0.085)));
  col.a += amb * uAmbient;
  float amb2 = smoothstep(0.52, 0.86, fbm(p*1.5 + vec2(-uTime*0.062, uTime*0.05) + 23.0));
  col.g += amb2 * uAmbient * 0.8;

  // pointer ink injection (primary stream)
  float inj = md * uMouseStr;
  col.a += inj;

  col = clamp(col, 0.0, 1.4);
  gl_FragColor = col;
}`;

const DISP = `
precision highp float;
varying vec2 vUv;
uniform sampler2D uState;
uniform vec2 uRes;
uniform float uTime;
uniform int uPalette;
${NOISE}

vec3 ramp(int pal, float d, float flow, vec2 uv){
  d = clamp(d,0.0,1.0);
  float s = smoothstep(0.0,1.0,d);
  if(pal==0){
    vec3 paper=vec3(0.953,0.937,0.902), ink=vec3(0.04,0.043,0.05);
    return mix(paper, ink, pow(s,0.85));
  }
  if(pal==1){
    vec3 paper=vec3(0.949,0.933,0.890);
    vec3 mid=vec3(0.196,0.345,0.760), deep=vec3(0.055,0.094,0.298);
    vec3 c=mix(paper,mid,smoothstep(0.0,0.55,d));
    return mix(c,deep,smoothstep(0.45,1.0,d));
  }
  if(pal==2){
    vec3 bg=vec3(0.02,0.027,0.047);
    vec3 cyan=vec3(0.15,0.92,0.96), mag=vec3(0.96,0.18,0.66), hot=vec3(1.0,0.95,0.98);
    vec3 c=bg + cyan*smoothstep(0.0,0.72,d)*1.0;
    c=mix(c, c*0.45+mag*0.9, smoothstep(0.55,0.92,d));
    c=mix(c, hot, smoothstep(0.9,1.0,d));
    return c;
  }
  if(pal==3){
    vec3 bg=vec3(0.015,0.016,0.024);
    float t = d*1.1 + flow*0.5 + uv.y*0.6 + uTime*0.02;
    vec3 a=vec3(0.5), b=vec3(0.5), cc=vec3(1.0,1.0,1.0), dd=vec3(0.0,0.33,0.67);
    vec3 irid = a + b*cos(6.28318*(cc*t+dd));
    return mix(bg, irid, smoothstep(0.05,0.55,d));
  }
  if(pal==5){
    // InkBytes brand — deep navy field, luminous indigo ink. The warm
    // (coral) tone is a SEPARATE drifting stream applied in main() from the
    // green channel, so the two colours move independently. Kept dark-dominant
    // so white foreground text stays legible.
    vec3 bg=vec3(0.043,0.043,0.082);          // ~#0b0b15, just under --accent
    vec3 indigo=vec3(0.235,0.282,0.64);       // luminous indigo ink
    return mix(bg, indigo, smoothstep(0.12,0.9,d));
  }
  // pal 4 — vermillion editorial
  vec3 paper=vec3(0.965,0.937,0.890);
  vec3 verm=vec3(0.835,0.270,0.165), maroon=vec3(0.369,0.071,0.047);
  vec3 c=mix(paper,verm,smoothstep(0.0,0.55,d));
  return mix(c,maroon,smoothstep(0.5,1.0,d));
}

void main(){
  vec4 st = texture2D(uState, vUv);
  float d = st.a;
  float flow = fbm(vUv*4.0 + uTime*0.05);
  vec3 col = ramp(uPalette, d, flow, vUv);

  // Second colour motion (palette 5): a warm coral ink stream from the green
  // channel that drifts on its own path, blended over the indigo primary.
  if(uPalette==5){
    float d2 = clamp(st.g, 0.0, 1.0);
    vec3 second = vec3(0.91, 0.39, 0.42);   // coral, --accent-dot family
    col = mix(col, col*0.32 + second, smoothstep(0.06, 0.78, d2) * 0.70);
    col += second * d2 * 0.14;              // soft warm glow
  }

  if(uPalette==2 || uPalette==3 || uPalette==5){
    col += col * d * 0.38;
  }
  float g = hash(vUv*uRes + uTime*60.0);
  col += (g-0.5)*0.022;
  vec2 q = vUv-0.5;
  col *= 1.0 - dot(q,q)*0.55;
  gl_FragColor = vec4(col,1.0);
}`;

const RED = `
precision highp float;
varying vec2 vUv;
uniform sampler2D uState;
uniform vec2 uTexel;
void main(){
  float d = texture2D(uState,vUv).a*2.0;
  d += texture2D(uState,vUv+vec2(uTexel.x,0.0)).a;
  d += texture2D(uState,vUv-vec2(uTexel.x,0.0)).a;
  d += texture2D(uState,vUv+vec2(0.0,uTexel.y)).a;
  d += texture2D(uState,vUv-vec2(0.0,uTexel.y)).a;
  d += texture2D(uState,vUv+uTexel).a;
  d += texture2D(uState,vUv-uTexel).a;
  d /= 8.0;
  gl_FragColor = vec4(d,d,d,1.0);
}`;

function compile(gl, type, src) {
  const s = gl.createShader(type);
  gl.shaderSource(s, src);
  gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS))
    throw new Error(gl.getShaderInfoLog(s));
  return s;
}
function program(gl, fs) {
  const p = gl.createProgram();
  gl.attachShader(p, compile(gl, gl.VERTEX_SHADER, VERT));
  gl.attachShader(p, compile(gl, gl.FRAGMENT_SHADER, fs));
  gl.bindAttribLocation(p, 0, 'aPos');
  gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS))
    throw new Error(gl.getProgramInfoLog(p));
  return p;
}

export class InkWall {
  constructor(canvas, opts) {
    this.canvas = canvas;
    this.opts = Object.assign(
      { palette: 0, speed: 0.0016, dissip: 0.991, flow: 2.4, emit: 0.0, ambient: 0.007 },
      opts || {}
    );
    this.mouse = [0.5, 0.5];
    this.mv = [0, 0];
    this.mStr = 0;
    this.scale = 0.62;
    this.t0 = performance.now();
    this._raf = 0;
    this._destroyed = false;
    this._init();
  }

  _init() {
    const attrs = { antialias: false, alpha: false, premultipliedAlpha: false, preserveDrawingBuffer: true };
    const gl = this.canvas.getContext('webgl', attrs) || this.canvas.getContext('experimental-webgl', attrs);
    if (!gl) throw new Error('WebGL unavailable');
    this.gl = gl;
    this.hf = gl.getExtension('OES_texture_half_float');
    gl.getExtension('OES_texture_half_float_linear');
    this.cbf = gl.getExtension('EXT_color_buffer_half_float');
    this.texType = this.hf && this.cbf ? this.hf.HALF_FLOAT_OES : gl.UNSIGNED_BYTE;
    this.linear = this.texType === gl.UNSIGNED_BYTE || gl.getExtension('OES_texture_half_float_linear');

    this.vbo = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, this.vbo);
    gl.bufferData(gl.ARRAY_BUFFER, QUAD, gl.STATIC_DRAW);

    this.simP = program(gl, SIM);
    this.dispP = program(gl, DISP);
    this.redP = program(gl, RED);
    this.U = (p, n) => gl.getUniformLocation(p, n);

    this.rw = 11;
    this.rh = 22;
    this.R = this._texByte(this.rw, this.rh);
    this.rbuf = new Uint8Array(this.rw * this.rh * 4);
    this.dense = { x: 0.5, y: 0.55, v: 0 };
    this._fc = (Math.random() * 4) | 0;

    this.resize(true);
    for (let i = 0; i < 60; i++) this.step(1 / 60, true);
  }

  resize(force) {
    const c = this.canvas;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.max(2, Math.round(c.clientWidth * dpr));
    const h = Math.max(2, Math.round(c.clientHeight * dpr));
    if (!force && w === c.width && h === c.height) return;
    c.width = w;
    c.height = h;
    this.sw = Math.max(2, Math.round(c.clientWidth * this.scale));
    this.sh = Math.max(2, Math.round(c.clientHeight * this.scale));
    this._buildFBOs();
    this._seeded = false;
  }

  _tex(w, h) {
    const gl = this.gl;
    const t = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, t);
    const f = this.linear ? gl.LINEAR : gl.NEAREST;
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, f);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, f);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, this.texType, null);
    const fb = gl.createFramebuffer();
    gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, t, 0);
    if (gl.checkFramebufferStatus(gl.FRAMEBUFFER) !== gl.FRAMEBUFFER_COMPLETE && this.texType !== gl.UNSIGNED_BYTE) {
      this.texType = gl.UNSIGNED_BYTE;
      this.linear = true;
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, this.texType, null);
    }
    return { t, fb };
  }

  _texByte(w, h) {
    const gl = this.gl;
    const t = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    const fb = gl.createFramebuffer();
    gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, t, 0);
    return { t, fb };
  }

  densest() {
    const gl = this.gl;
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.R.fb);
    gl.viewport(0, 0, this.rw, this.rh);
    gl.useProgram(this.redP);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, this.A.t);
    gl.uniform1i(this.U(this.redP, 'uState'), 0);
    gl.uniform2f(this.U(this.redP, 'uTexel'), 3.0 / this.sw, 3.0 / this.sh);
    this._draw(this.redP);
    gl.readPixels(0, 0, this.rw, this.rh, gl.RGBA, gl.UNSIGNED_BYTE, this.rbuf);
    let best = -1, bx = this.rw / 2, by = this.rh / 2;
    for (let y = 0; y < this.rh; y++) {
      for (let x = 0; x < this.rw; x++) {
        const v = this.rbuf[(y * this.rw + x) * 4];
        if (v > best) { best = v; bx = x; by = y; }
      }
    }
    const fx = (bx + 0.5) / this.rw, fy = (by + 0.5) / this.rh;
    const k = best / 255 > this.dense.v ? 0.16 : 0.06;
    this.dense.x += (fx - this.dense.x) * k;
    this.dense.y += (fy - this.dense.y) * k;
    this.dense.v += (best / 255 - this.dense.v) * 0.09;
    return this.dense;
  }

  _buildFBOs() {
    this.A = this._tex(this.sw, this.sh);
    this.B = this._tex(this.sw, this.sh);
  }

  _draw(prog) {
    const gl = this.gl;
    gl.bindBuffer(gl.ARRAY_BUFFER, this.vbo);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
    gl.useProgram(prog);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }

  step() {
    const gl = this.gl, o = this.opts;
    const time = (performance.now() - this.t0) / 1000;
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.B.fb);
    gl.viewport(0, 0, this.sw, this.sh);
    gl.useProgram(this.simP);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, this.A.t);
    gl.uniform1i(this.U(this.simP, 'uPrev'), 0);
    gl.uniform2f(this.U(this.simP, 'uRes'), this.sw, this.sh);
    gl.uniform1f(this.U(this.simP, 'uTime'), time);
    gl.uniform1f(this.U(this.simP, 'uSpeed'), o.speed);
    gl.uniform1f(this.U(this.simP, 'uDissip'), o.dissip);
    gl.uniform1f(this.U(this.simP, 'uFlow'), o.flow);
    gl.uniform1f(this.U(this.simP, 'uInit'), this._seeded ? 0.0 : 1.0);
    gl.uniform2f(this.U(this.simP, 'uMouse'), this.mouse[0], this.mouse[1]);
    gl.uniform2f(this.U(this.simP, 'uMouseVel'), this.mv[0], this.mv[1]);
    gl.uniform1f(this.U(this.simP, 'uMouseStr'), this.mStr);
    const ex = 0.5 + 0.33 * Math.sin(time * 0.5 + this.opts.palette);
    const ey = 0.5 + 0.37 * Math.cos(time * 0.39 + this.opts.palette * 2.0);
    gl.uniform2f(this.U(this.simP, 'uEmit'), ex, ey);
    // Second emitter — different frequencies + phase so the warm ink stream
    // drifts on an independent Lissajous path from the indigo primary.
    const ex2 = 0.5 + 0.34 * Math.sin(time * 0.33 + 2.1);
    const ey2 = 0.5 + 0.30 * Math.cos(time * 0.47 + 4.2);
    gl.uniform2f(this.U(this.simP, 'uEmit2'), ex2, ey2);
    gl.uniform1f(this.U(this.simP, 'uEmitStr'), o.emit);
    gl.uniform1f(this.U(this.simP, 'uAmbient'), o.ambient || 0.0);
    this._draw(this.simP);
    this._seeded = true;
    const tmp = this.A; this.A = this.B; this.B = tmp;

    this.mv[0] *= 0.86; this.mv[1] *= 0.86;
    this.mStr *= 0.9;
  }

  render() {
    const gl = this.gl;
    const time = (performance.now() - this.t0) / 1000;
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    gl.useProgram(this.dispP);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, this.A.t);
    gl.uniform1i(this.U(this.dispP, 'uState'), 0);
    gl.uniform2f(this.U(this.dispP, 'uRes'), this.canvas.width, this.canvas.height);
    gl.uniform1f(this.U(this.dispP, 'uTime'), time);
    gl.uniform1i(this.U(this.dispP, 'uPalette'), this.opts.palette);
    this._draw(this.dispP);
  }

  // pointer drag in normalised coords (y up); inject ink + velocity
  pointer(x, y, dx, dy) {
    this.mouse[0] = x;
    this.mouse[1] = y;
    this.mv[0] += dx;
    this.mv[1] += dy;
    this.mStr = Math.min(this.mStr + 0.45, 0.9);
  }

  // Begin the per-instance animation loop (idempotent).
  start() {
    if (this._raf || this._destroyed) return;
    let last = performance.now();
    const loop = (now) => {
      if (this._destroyed) return;
      const dt = Math.min((now - last) / 1000, 1 / 30);
      last = now;
      this.resize(false);
      this.step(dt);
      this.render();
      this._fc = (this._fc + 1) % 4;
      if (this._fc === 0) this.densest();
      this._raf = requestAnimationFrame(loop);
    };
    this._raf = requestAnimationFrame(loop);
  }

  // Stop the loop and release GPU resources. Deliberately does NOT call
  // WEBGL_lose_context.loseContext(): that permanently poisons the canvas's
  // context, so a remount on the same <canvas> (React StrictMode double-invoke
  // in dev, or any re-render) would fail to compile shaders. Deleting the
  // resources is enough — the browser reclaims the context when the canvas
  // element leaves the DOM.
  destroy() {
    this._destroyed = true;
    if (this._raf) cancelAnimationFrame(this._raf);
    this._raf = 0;
    const gl = this.gl;
    if (!gl) return;
    try {
      [this.A, this.B, this.R].forEach((o) => {
        if (o) { gl.deleteTexture(o.t); gl.deleteFramebuffer(o.fb); }
      });
      gl.deleteBuffer(this.vbo);
      [this.simP, this.dispP, this.redP].forEach((p) => p && gl.deleteProgram(p));
    } catch {
      /* context already gone — nothing to release */
    }
  }
}
