/* Partial adaptation of ComfyUI-Autocomplete-Plus, Copyright (c) 2025 newtextdoc1111, MIT.
 * Neo integration, guarded formatting, and cooperative Japanese matching.
 */
(() => {
    const selector='#txt2img_prompt textarea,#txt2img_neg_prompt textarea,#img2img_prompt textarea,#img2img_neg_prompt textarea';
    const option=(key,fallback)=>typeof opts!=='undefined' ? (opts['tacplus_'+key] ?? fallback) : fallback;
    const enabled=()=>option('enabled',true);
    const kana=s=>String(s??'').normalize('NFKC').toLowerCase().replace(/[ァ-ヶ]/g,c=>String.fromCharCode(c.charCodeAt(0)-0x60));
    function segments(text) {
        const out=[];let start=0,stack=[],escape=false,quote=false;
        const pairs={'(':')','[':']','{':'}','<':'>'};
        for(let i=0;i<text.length;i++) {
            const c=text[i];if(escape){escape=false;continue}if(c==='\\'){escape=true;continue}
            if(c==='"'){quote=!quote;continue}if(quote)continue;
            if(pairs[c])stack.push(pairs[c]);else if(stack.length&&c===stack[stack.length-1])stack.pop();
            else if(!stack.length&&(c===','||c==='\n')){out.push({start,end:i,text:text.slice(start,i),separator:c});start=i+1}
        }
        out.push({start,end:text.length,text:text.slice(start),separator:''});
        return {items:out,balanced:!stack.length&&!quote&&!escape};
    }
    function normalizeTag(text) {
        let t=text.trim();
        if(/^\([^,]*:-?\d+(?:\.\d+)?\)$/.test(t))t=t.slice(1,-1).replace(/:-?\d+(?:\.\d+)?$/,'');
        return t.replace(/\\([()[\]])/g,'$1').replace(/^@/,'').replace(/\s+/g,'_').toLowerCase();
    }
    function existing(area,text) {const name=normalizeTag(text);return segments(area.value).items.find(s=>normalizeTag(s.text)===name);}
    function selectExisting(area,text) {
        if(!enabled()||!option('duplicate_select',true))return false;
        const found=existing(area,text);if(!found)return false;
        area.focus();area.setSelectionRange(found.start,found.end);if(typeof hideResults==='function')hideResults(area);return true;
    }
    function decorate(li,area,result) {
        if(!enabled()||!option('duplicates',true)||result.type!==ResultType.tag)return;
        if(existing(area,result.text)){li.classList.add('tacplus-used');li.title='入力済みのタグ';}
    }
    function format(text,trim=option('format_trim',true),trailing=option('format_trailing',false)) {
        if(!text.trim())return trim?'':text;
        if(trim)text=text.trim();
        const parsed=segments(text);if(!parsed.balanced)return text;
        let result='',line=[];
        for(const part of parsed.items){if(part.text.trim())line.push(part.text.trim());
            if(part.separator==='\n'||part.separator==='') {
                const body=line.join(', ');result+=body+(trailing&&body&&!/^(BREAK|AND)$/.test(body)?',':'')+(part.separator==='\n'?'\n':'');line=[];
            }
        }
        if(!trim){const lead=text.match(/^\s*/)[0],tail=text.match(/\s*$/)[0];result=lead+result.trim()+tail;}
        return result;
    }
    function replace(area,start,end,value) {
        area.focus();area.setSelectionRange(start,end);
        const ok=document.execCommand('insertText',false,value);
        if(!ok)area.setRangeText(value,start,end,'end');
        area.dispatchEvent(new Event('input',{bubbles:true}));
    }
    function formatArea(area) {
        if(!enabled()||!option('format',true))return;
        const old=area.value,newText=format(old);if(newText===old)return;
        const pos=area.selectionStart;replace(area,0,old.length,newText);area.setSelectionRange(Math.min(pos,newText.length),Math.min(pos,newText.length));
    }
    let cache=new WeakMap(),translationSource,translationCount;
    function kanaFilter(query) {
        if(translationSource!==translations||translationCount!==translations.size){cache=new WeakMap();translationSource=translations;translationCount=translations.size;}
        const needle=kana(query.replace(/^\*/, '')).replace(/\s+/g,'_');
        const alias=TAC_CFG.alias.searchByAlias,translation=TAC_CFG.translation.searchByTranslation;
        return row=>{
            let entry=cache.get(row);
            if(!entry){entry=[kana(row[0]),kana(row[3]||''),kana([translations.get(row[0])||'',...(row[3]||'').split(',').map(x=>translations.get(x)||'')].join(','))];cache.set(row,entry);}
            return entry[0].includes(needle)||(alias&&entry[1].includes(needle))||(translation&&entry[2].includes(needle));
        };
    }
    async function filterAsync(rows,filter,area,prompt) {
        const found=[];let deadline=performance.now()+4;
        for(let i=0;i<rows.length;i++) {
            if(filter(rows[i]))found.push(rows[i]);
            if(i%256===0&&performance.now()>deadline){await new Promise(r=>setTimeout(r,0));if(area.value!==prompt)return null;deadline=performance.now()+4;}
        }
        return area.value===prompt?found:null;
    }
    let panel,activeArea,request=0,skipFormatBlur=false;
    function close(){request++;panel?.remove();panel=null;activeArea=null;}
    function normalVisible() {
        return [...document.querySelectorAll('.autocompleteParent')].some(e=>getComputedStyle(e).display!=='none'&&e.getClientRects().length&&e.offsetHeight>0);
    }
    function completedPart(area) {
        const parts=segments(area.value).items;
        let index=parts.findIndex(s=>s.start<=area.selectionStart&&s.end>=area.selectionStart);
        if(index>0&&!parts[index].text.trim())index--;
        const part=parts[index];return part?.separator===','&&part.text.trim()?part:null;
    }
    window.addEventListener('input',event=>{if(panel&&event.target.matches?.(selector))close();},true);
    function positionPanel() {
        if(!panel||!activeArea)return;
        const area=activeArea, rect=area.getBoundingClientRect();
        const mode=(document.querySelector('.dark')||gradioApp().querySelector('.dark'))?0:1;
        for(const [name,values] of Object.entries(styleColors))panel.style.setProperty(name,values[mode]);
        // Use Neo's own cursor/fixed-popup placement, including its configured offset.
        showResults(area, true);
        const native=document.querySelector('.autocompleteResults'+getTextAreaIdentifier(area));
        const anchor=native?.getBoundingClientRect();
        const nativeStyle=getComputedStyle(native);
        panel.style.font=nativeStyle.font;
        panel.style.lineHeight=nativeStyle.lineHeight;
        const nativeRow=native.querySelector('li');
        panel.style.setProperty('--tacplus-row-padding',nativeRow?getComputedStyle(nativeRow).padding:'10px');
        const nativeMaxHeight=parseFloat(nativeStyle.maxHeight)||innerHeight;
        hideResults(area);
        const right=Math.min(rect.right,innerWidth-8);
        const minimum=Math.min(320,Math.max(0,rect.width));
        const x=Math.max(8,Math.min(anchor?.left??rect.left,right-minimum));
        // Grow to the longest row; wrap only at the prompt's right edge.
        panel.style.boxSizing='border-box';
        panel.style.width='max-content';
        panel.style.maxWidth=Math.max(0,right-x)+'px';
        let y=anchor?.top??(rect.bottom+10);
        const height=Math.min(panel.scrollHeight,nativeMaxHeight);
        if(innerHeight-y<Math.min(height,160))y=Math.max(8,y-height-20);
        panel.style.left=x+'px';panel.style.top=Math.max(8,y)+'px';
        panel.style.maxHeight=Math.max(80,Math.min(nativeMaxHeight,innerHeight-y-8))+'px';
    }
    window.addEventListener('resize',positionPanel);
    document.addEventListener('scroll',event=>{if(panel&&!panel.contains(event.target))positionPanel();},true);
    function button(text,fn){const b=document.createElement('button');b.type='button';b.textContent=text;b.onclick=fn;return b;}
    function wikiLink(tag) {
        const link=document.createElement('a');link.className='tacplus-wiki';
        link.href='https://danbooru.donmai.us/wiki_pages/'+encodeURIComponent(tag);
        link.target='_blank';link.rel='noopener noreferrer';link.textContent='📖';
        link.title=tag+' — Danbooru Wiki';link.setAttribute('aria-label',link.title);
        link.addEventListener('click',event=>event.stopPropagation());return link;
    }
    async function related(area) {
        if(!enabled()||!option('related',true)||normalVisible()){close();return;}
        const part=completedPart(area);
        if(!part){close();return;}
        const tag=normalizeTag(part.text);
        if(!tag||tag.length>256||/[<>{}|,]/.test(tag))return;
        close();activeArea=area;const token=++request;
        panel=document.createElement('div');panel.className='tacplus-related';panel.setAttribute('role','dialog');panel.setAttribute('aria-label','関連タグ');
        const head=document.createElement('div');head.className='tacplus-related-head';const title=document.createElement('span');title.textContent='関連タグ: '+tag;head.append(title,wikiLink(tag),button('×',close));panel.append(head);
        const status=document.createElement('div');status.textContent='検索中…';panel.append(status);document.body.append(panel);
        positionPanel();
        try {
            const response=await fetch('/tac-plus/related?tag='+encodeURIComponent(tag));if(!response.ok)throw Error('HTTP '+response.status);
            const data=await response.json();if(token!==request)return;
            if(normalVisible()){close();return;}
            status.textContent=data.error||(!data.items.length?'関連データがありません':'');
            for(const item of data.items){
                const translated=typeof translations!=='undefined'?translations.get(item.tag):'';
                const row=button(item.tag+(translated?'['+translated+']':''),()=>{
                    if(selectExisting(area,item.tag))return;
                    const current=segments(area.value).items.find(s=>normalizeTag(s.text)===tag);
                    if(!current){status.textContent='元のタグが変更されています。関連タグを開き直してください。';return;}
                    let text=TAC_CFG.replaceUnderscores?item.tag.replaceAll('_',' '):item.tag;
                    if(TAC_CFG.escapeParentheses)text=text.replace(/[()[\]]/g,'\\$&');
                    replace(area,current.end,current.end,', '+text);row.classList.add('tacplus-used');
                });row.className='tacplus-related-row';if(option('duplicates',true)&&existing(area,item.tag))row.classList.add('tacplus-used');
                row.title='共起: '+item.cooccurrence+' / Jaccard: '+item.score.toFixed(4);const itemRow=document.createElement('div');itemRow.className='tacplus-related-item';itemRow.append(wikiLink(item.tag),row);panel.append(itemRow);
            }
            positionPanel();
        } catch(error){if(token===request)status.textContent='関連タグを取得できません: '+error.message;}
    }
    document.addEventListener('keydown',event=>{
        const area=event.target.matches?.(selector)?event.target:activeArea;
        if(event.key==='Escape'&&panel){close();return;}
        if(!area||event.isComposing)return;
        if(event.ctrlKey&&event.shiftKey&&event.code==='Space'){event.preventDefault();event.stopImmediatePropagation();related(area);}
        else if(event.altKey&&event.shiftKey&&event.code==='KeyF'){event.preventDefault();event.stopImmediatePropagation();formatArea(area);}
        else if(panel&&['ArrowDown','ArrowUp','Enter','Tab'].includes(event.key)){
            const rows=[...panel.querySelectorAll('.tacplus-related-row')];if(!rows.length)return;
            event.preventDefault();event.stopImmediatePropagation();let index=rows.indexOf(document.activeElement);
            if(event.key==='Enter'||event.key==='Tab'){if(index>=0)rows[index].click();else rows[0].focus();}
            else rows[(index+(event.key==='ArrowDown'?1:-1)+rows.length)%rows.length].focus();
        }
    },true);
    document.addEventListener('click',event=>{
        const area=event.target;if(!area.matches?.(selector))return;
        const trigger=option('related_trigger','Ctrl+Click');if(trigger==='Click'||(trigger==='Ctrl+Click'&&event.ctrlKey))related(area);
    });
    document.addEventListener('focusout',event=>{
        const area=event.target;if(skipFormatBlur||!area.matches?.(selector)||!enabled()||!option('format',true)||option('format_mode','Manual')!=='On blur')return;
        // Update directly without moving focus back from the clicked control.
        const value=format(area.value);if(value!==area.value){area.value=value;area.dispatchEvent(new Event('input',{bubbles:true}));}
    },true);
    document.addEventListener('pointerdown',event=>{skipFormatBlur=!!event.target.closest?.('.autocompleteParent,.tacplus-related');setTimeout(()=>{skipFormatBlur=false},0);if(panel&&!panel.contains(event.target)&&event.target!==activeArea)close();},true);
    const style=document.createElement('style');style.textContent=`
.tacplus-used{opacity:.48}
.tacplus-related{position:fixed;z-index:10000;max-height:320px;overflow:auto;padding:0;background:var(--results-bg);color:var(--results-neutral-text);border:var(--results-border-width) solid var(--results-border-color);border-radius:12px;font:inherit}
.tacplus-related-head{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px;position:sticky;top:0;z-index:1;background:var(--results-bg);border-bottom:1px solid var(--results-border-color)}
.tacplus-related button{opacity:1!important;color:var(--results-neutral-text);background:var(--results-bg);font:inherit;transition:none;filter:none}
.tacplus-related-row{display:block;width:100%;text-align:left;padding:var(--tacplus-row-padding,10px);border:0;cursor:pointer;white-space:normal;overflow-wrap:anywhere}
.tacplus-related-item{display:flex;align-items:stretch;background:var(--results-bg)}
.tacplus-related-item:nth-child(odd),.tacplus-related-item:nth-child(odd) button{background:var(--results-bg-odd)}
.tacplus-related-item .tacplus-related-row{flex:1;min-width:0;width:auto}
.tacplus-wiki{flex:none;display:flex;align-items:center;justify-content:center;padding:4px;color:var(--results-neutral-text)!important;opacity:1!important;text-decoration:none}
.tacplus-wiki:hover,.tacplus-wiki:focus-visible{background:var(--results-hover);outline:1px solid var(--results-border-color);outline-offset:-1px}
.tacplus-related-head>span{flex:1;min-width:0;overflow-wrap:anywhere}
.tacplus-related .tacplus-used{opacity:1;color:var(--meta-text-color)}
.tacplus-related .tacplus-used::after{content:'（入力済み）';font-size:.85em}
.tacplus-related button:hover{background:var(--results-hover)!important;color:var(--results-neutral-text)!important;opacity:1!important}
.tacplus-related button:focus-visible{background:var(--results-selected)!important;color:var(--results-neutral-text)!important;outline:1px solid var(--results-border-color);outline-offset:-1px;opacity:1!important}
`;document.head.append(style);
    if(typeof onOptionsChanged==='function')onOptionsChanged(()=>{cache=new WeakMap();if(!enabled()||!option('related',true))close();});
    window.tacPlus={normalVisible,completedPart,selectExisting,decorate,format,normalizeTag,segments,kana,kanaFilter,filterAsync,related,close,
        kanaActive:q=>enabled()&&option('kana',true)&&/[\u3040-\u30ff\uff61-\uff9f]/.test(q)};
})();

/* Local asynchronous dictionary search. Keeps Gradio's prompt synchronization independent. */
(() => {
    function workerMain() {
        let rows=[],translations=new Map();
        const kana=s=>s.normalize('NFKC').toLowerCase().replace(/[ァ-ヶ]/g,c=>String.fromCharCode(c.charCodeAt(0)-0x60));
        self.onmessage=({data:d})=>{
            if(d.kind==='translations'){for(const pair of d.rows)translations.set(pair[0],pair[1].toLowerCase());return;}
            if(d.kind==='rows'){for(const row of d.rows){const name=row[0],alias=(row[1]||'').toLowerCase();rows.push([name.toLowerCase(),alias,[translations.get(name)||'',...alias.split(',').map(a=>translations.get(a)||'')].join('\n')]);}return;}
            if(d.kind==='ready'){self.postMessage({id:d.id,result:true});return;}
            if(d.kind==='query'){
                const regex=new RegExp(d.source,d.flags),needle=d.kana?kana(d.query.replace(/^\*/, '')).replace(/\s+/g,'_'):'';
                const match=row=>{
                    if(d.kana){row[3]??=row.map(kana);return row[3][0].includes(needle)||(d.alias&&row[3][1].includes(needle))||(d.translation&&row[3][2].includes(needle));}
                    return regex.test(row[0])||(d.alias&&regex.test(row[1]))||(d.translation&&regex.test(row[2]));
                };
                function scan(ids){const out=[];for(let j=0;j<(ids?ids.length:rows.length);j++){const i=ids?ids[j]:j;if(match(rows[i])){out.push(i);if(d.limit&&out.length>=d.limit)break;}}return out;}
                let result=scan(d.indices);if(!result.length&&d.indices)result=scan(null);
                self.postMessage({id:d.id,result});
            }
        };
    }
    let worker,sourceRows,sourceTranslations,translationCount,indices,ready=false,generation=0,serial=0;
    const requests=new Map();
    function call(data){return new Promise((resolve,reject)=>{const id=++serial;const timeout=setTimeout(()=>{requests.delete(id);reject(Error('Dictionary worker timed out'));},10000);requests.set(id,{resolve,reject,timeout});worker.postMessage({...data,id});});}
    async function prepare(rows,tr) {
        if(sourceRows===rows&&sourceTranslations===tr&&translationCount===tr.size)return;
        const gen=++generation;ready=false;worker?.terminate();for(const p of requests.values()){clearTimeout(p.timeout);p.reject(Error('Dictionary changed'));}requests.clear();
        sourceRows=rows;sourceTranslations=tr;translationCount=tr.size;indices=new WeakMap();
        const url=URL.createObjectURL(new Blob(['('+workerMain.toString()+')()'],{type:'application/javascript'}));worker=new Worker(url);URL.revokeObjectURL(url);
        worker.onmessage=({data:d})=>{const p=requests.get(d.id);if(p){clearTimeout(p.timeout);requests.delete(d.id);p.resolve(d.result);}};
        worker.onerror=()=>{ready=false;};
        const yieldTask=()=>new Promise(r=>setTimeout(r,0));
        const trans=Array.from(tr);
        for(let i=0;i<trans.length;i+=2000){if(gen!==generation)return;worker.postMessage({kind:'translations',rows:trans.slice(i,i+2000)});await yieldTask();}
        for(let i=0;i<rows.length;i+=2000){if(gen!==generation)return;const batch=rows.slice(i,i+2000);batch.forEach((r,j)=>indices.set(r,i+j));worker.postMessage({kind:'rows',rows:batch.map(r=>[r[0],r[3]])});await yieldTask();}
        await call({kind:'ready'});if(gen===generation)ready=true;
    }
    async function search(subset,regex,query,kanaSearch,limit) {
        if(!ready||sourceRows!==allTags||sourceTranslations!==translations||translationCount!==translations.size)return null;
        const gen=generation;
        const ids=await call({kind:'query',indices:subset===sourceRows?null:subset.map(r=>indices.get(r)),source:regex.source,flags:regex.flags,query,kana:!!kanaSearch,alias:TAC_CFG.alias.searchByAlias,translation:TAC_CFG.translation.searchByTranslation,limit});
        return gen===generation?ids.map(i=>sourceRows[i]):null;
    }
    window.tacFastSearch={prepare,search,get ready(){return ready&&sourceRows===allTags&&sourceTranslations===translations&&translationCount===translations.size;}};
})();
