const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'manifest.json'), 'utf8'));
const operation = manifest.components.find(c => c.id === 'prompt-sync').files.find(f => f.path.endsWith('.js'));
const source = fs.readFileSync(path.join(root, operation.payload), 'utf8');

function setup() {
  const handlers = {}, timers = new Map(), microtasks = [];
  let id = 0;
  class Event { constructor(type, options={}) { this.type=type; Object.assign(this, options); } }
  const context = {document:{addEventListener(type, callback) { (handlers[type] ??= []).push(callback); }},
    window:{}, opts:{tacplus_input_delay:120}, InputEvent:Event, CustomEvent:Event, MouseEvent:Event,
    setTimeout(fn) { timers.set(++id, fn); return id; }, clearTimeout(id) { timers.delete(id); },
    queueMicrotask(fn) { microtasks.push(fn); }};
  vm.createContext(context); vm.runInContext(source, context);
  const events = [];
  const area = {matches:()=>true, classList:{contains:()=>false}, dispatchEvent(event) { events.push(event); }};
  const fire = (type, extra={}) => { const event={target:area,isTrusted:true,isComposing:false,
    stopImmediatePropagation(){this.stopped=true;},preventDefault(){this.prevented=true;}, ...extra};
    for (const fn of handlers[type] || []) fn(event); return event; };
  const tick = () => { const pending=[...timers.values()]; timers.clear(); pending.forEach(fn=>fn()); };
  return {context,area,events,fire,tick,timers,microtasks};
}

test('rapid typing coalesces without losing final input', () => {
  const t=setup(); t.fire('input',{data:'a'}); t.fire('input',{data:'b'});
  assert.equal(t.events.length,0); t.tick(); assert.equal(t.events.length,1); assert.equal(t.events[0].data,'b');
  assert.equal(t.events[0].fnmUserInput,true);
});
test('IME input waits for composition end', () => {
  const t=setup(); t.fire('input',{isComposing:true,data:'ね'}); t.tick(); assert.equal(t.events.length,0);
  t.fire('compositionend'); t.tick(); assert.equal(t.events.length,1);
});
test('generate pointer action flushes pending prompt', () => {
  const t=setup(); t.fire('input',{data:'x'}); t.fire('pointerdown',{target:{matches:()=>false}});
  assert.equal(t.events.length,1); assert.equal(t.context.window.forgePromptInputSync.pending(),0);
});
test('programmatic click waits for synchronization microtask', () => {
  const t=setup(); const clicks=[]; t.fire('input',{data:'x'});
  const event=t.fire('click',{target:{matches:()=>false,dispatchEvent:e=>clicks.push(e)}});
  assert.equal(event.prevented,true); assert.equal(t.events.length,1); assert.equal(clicks.length,0);
  t.microtasks.forEach(f=>f()); assert.equal(clicks.length,1);
});
test('Ctrl+Enter flushes without waiting for debounce', () => {
  const t=setup(); t.fire('input'); t.fire('keydown',{key:'Enter',ctrlKey:true}); assert.equal(t.events.length,1);
});
test('synthetic autocomplete input cancels stale pending event', () => {
  const t=setup(); t.fire('input',{data:'x'}); t.fire('input',{isTrusted:false}); t.tick(); assert.equal(t.events.length,0);
});
test('loading twice does not register duplicate listeners', () => {
  const t=setup(); vm.runInContext(source,t.context); t.fire('input'); t.tick(); assert.equal(t.events.length,1);
});
