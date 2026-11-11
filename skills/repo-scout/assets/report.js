/* Repo Scout reader. All source strings are assigned through textContent. */
(() => {
  'use strict';
  const report = JSON.parse(document.getElementById('report-data').textContent);
  const KEYS = ['relevance','stack_fit','completeness','maintenance','learning_fit','reuse','popularity'];
  const LABELS = {relevance:'需求相关',stack_fit:'技术匹配',completeness:'完整程度',maintenance:'维护状态',learning_fit:'学习适配',reuse:'复用价值',popularity:'社区热度'};
  const DEFAULT = {relevance:25,stack_fit:15,completeness:15,maintenance:10,learning_fit:15,reuse:15,popularity:5};
  const PRESETS = {balanced:DEFAULT,learning:{relevance:25,stack_fit:10,completeness:10,maintenance:10,learning_fit:25,reuse:15,popularity:5},reuse:{relevance:25,stack_fit:20,completeness:15,maintenance:10,learning_fit:5,reuse:20,popularity:5}};
  const AUDIENCES = {individual:'个人学习 / 使用',personal:'个人学习 / 使用',team:'团队协作',enterprise:'企业方向','enterprise-oriented':'企业方向',unknown:'尚未确认'};
  const CATEGORIES = {framework:'开发框架',tutorial:'教程 / 示例',application:'完整应用',platform:'平台项目',library:'组件 / 库',tool:'开发工具',unknown:'形态待确认'};
  const STATUS = {'source-reviewed':'源码 / 资料核验',heuristic:'结构或元数据判断',unknown:'缺少判断依据'};
  const SIGNALS = {tests:'测试',ci:'CI',docs:'文档',examples:'示例',deployment:'部署',manifest:'依赖声明'};
  const $ = id => document.getElementById(id);
  const items = (Array.isArray(report.items) ? report.items : []).filter(x => x && typeof x === 'object').map((item,index) => ({...item,_id:String(item.id || `${item.provider || 'repo'}:${item.name || index}`)}));
  const selected = new Set();
  let activePreset = '';
  let rawWeights = Object.fromEntries(KEYS.map(key => [key,validWeight((report.weights || {})[key]) ? Number(report.weights[key]) : DEFAULT[key]]));
  const initialWeights = {...rawWeights};
  let currentScores = new Map();
  let toastTimer;

  function validWeight(value) {return typeof value === 'number' && Number.isFinite(value) && value >= 0;}
  function node(tag, cls='', text) {const result=document.createElement(tag);if(cls)result.className=cls;if(text!==undefined&&text!==null)result.textContent=String(text);return result;}
  function string(value, fallback='') {return typeof value === 'string' ? value : fallback;}
  function list(value) {return Array.isArray(value) ? value.filter(x => typeof x === 'string') : [];}
  function format(value) {return typeof value==='number'&&Number.isFinite(value)&&value>=0 ? new Intl.NumberFormat('en-US').format(value) : '未知';}
  function compact(value) {return typeof value==='number'&&Number.isFinite(value)&&value>=0 ? (value>=1000 ? `${new Intl.NumberFormat('en-US',{maximumFractionDigits:1}).format(value/1000)}k` : String(value)) : '未知';}
  function date(value) {if(!value||typeof value!=='string')return '未知';const d=new Date(value);return Number.isNaN(d.getTime()) ? '未知' : d.toISOString().slice(0,10);}
  function percent(value) {return `${Math.round(value*100)}%`;}
  function scoreText(value) {return Number.isFinite(value) ? value.toFixed(1) : '未知';}
  function safeUrl(value) {try{const url=new URL(value);return ['http:','https:'].includes(url.protocol)&&!url.username&&!url.password ? url.href : null;}catch{return null;}}
  function link(label,url,cls='') {const href=safeUrl(url);if(!href)return node('span',cls||'non-link',label);const a=node('a',cls,label);a.href=href;a.target='_blank';a.rel='noopener noreferrer';return a;}
  function labelAudience(item) {return string(typeof item.audience==='object'&&item.audience ? item.audience.label : item.audience,'unknown');}
  function normalizeAudience(value) {return value==='enterprise-oriented'?'enterprise':value==='personal'?'individual':(AUDIENCES[value]?value:'unknown');}
  function evidenceLinks(parent, values) {list(values).forEach((url,index)=>{if(safeUrl(url))parent.append(link(`依据 ${index+1}`,url,'evidence-link'));});}
  function discoveryEntries(item) {return Array.isArray(item.discovery)?item.discovery.filter(value=>value&&typeof value==='object'):[];}
  function discoveryLabel(hit) {return hit.type==='supplied'?'明确提供的候选':hit.type==='search'?'检索命中':'发现方式未明确';}
  function searchUrl(provider,query) {if(typeof query!=='string'||!query.trim())return null;const value=encodeURIComponent(query);if(provider==='github')return `https://github.com/search?q=${value}&type=repositories`;if(provider==='gitee')return `https://gitee.com/search?q=${value}&type=repository`;if(provider==='gitlab')return `https://gitlab.com/explore/projects?name=${value}`;return null;}
  function normalizedWeights() {const sum=KEYS.reduce((a,key)=>a+(validWeight(rawWeights[key])?rawWeights[key]:0),0);return sum>0?Object.fromEntries(KEYS.map(key=>[key,rawWeights[key]/sum*100])):null;}
  function criterion(item,key) {const value=(item.criteria||{})[key];return value&&typeof value==='object'?value:{value:null,status:'unknown',reason:'尚未记录判断依据',evidence:[]};}
  function numericCriterion(item,key) {const c=criterion(item,key);return typeof c.value==='number'&&Number.isFinite(c.value)&&c.value>=0&&c.value<=5&&c.status!=='unknown'?c.value:null;}
  function compute(item,weights) {let low=0,unknown=0,covered=0,reviewed=0;KEYS.forEach(key=>{const c=criterion(item,key),value=numericCriterion(item,key),w=weights[key];if(value===null){unknown+=w;}else{low+=w*value/5;covered+=w;if(c.status==='source-reviewed')reviewed+=w;}});return {low,upper:low+unknown,coverage:covered/100,review:reviewed/100};}
  function notify(message) {$('toast').textContent=message;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>{$('toast').hidden=true;},3500);}

  function initBrief() {
    const profile=report.profile||{};
    $('reportTitle').textContent=string(report.title)||string(profile.title)||'开源项目参考报告';
    $('profileGoal').textContent=string(profile.goal)||'按同一组维度，对照需求、实现证据和复用成本，找到值得继续研究的项目。';
    const tags=$('profileTags');
    tags.append(node('span','chip audience',AUDIENCES[profile.target_audience]||'个人学习 / 使用'));
    list(profile.stack).forEach(value=>tags.append(node('span','chip stack',value)));
    list(profile.capabilities).slice(0,6).forEach(value=>tags.append(node('span','chip',value)));
    const providers=[...new Set(items.map(item=>string(item.provider,'unknown')))].sort();
    providers.forEach(provider=>{const option=node('option','',provider);option.value=provider;$('providerFilter').append(option);});
    const receipts=Array.isArray(report.source_receipts)?report.source_receipts:[];
    const errors=receipts.filter(r=>r&&r.status==='error');
    const summary=$('researchSummary');
    [[items.length,'候选项目'],[providers.length,'结果来源'],[errors.length,'来源请求失败']].forEach(([number,label])=>{const part=node('div','summary-part');part.append(node('strong','',number),node('span','',label));summary.append(part);});
    summary.append(node('span','summary-boundary',errors.length?'部分检索未完成，排名仅基于成功取得的候选和证据。':'本次排序服务于当前目标；高分不代表运行验收或企业级认证。'));
    const method=report.methodology;
    $('methodologyText').textContent=typeof method==='string'?method:method&&typeof method==='object'?[method.description,method.note].filter(x=>typeof x==='string').join(' '):'';
    KEYS.forEach((key,index)=>{const legend=node('span','legend-item');const dot=node('i','legend-dot');dot.style.background=`var(--c${index})`;legend.append(dot,node('span','',LABELS[key]));$('railLegend').append(legend);});
    $('sourceLogTitle').textContent=`检索记录与范围 · ${receipts.length} 次请求${errors.length?` / ${errors.length} 次未完成`:''}`;
    if(!receipts.length)$('sourceLog').append(node('p','scope-copy','这份报告未附检索收据；候选来源范围需进一步确认。'));
    receipts.forEach(receipt=>{
      if(!receipt||typeof receipt!=='object')return;
      const entry=node('div',`source-entry${receipt.status==='error'?' error':''}`);
      const origin=receipt.type==='supplied'?'明确提供：':'检索词：';
      entry.append(node('strong','',string(receipt.provider,'unknown')),node('code','',origin+string(receipt.query,'未记录')),node('span','source-state',receipt.status==='error'?'未完成':`${format(receipt.count)} 条`));
      if(receipt.status==='error')entry.append(node('p','',string(receipt.error,'请求失败，未取得可用结果。')));
      $('sourceLog').append(entry);
    });
  }

  function buildWeightControls() {
    $('weightControls').replaceChildren();
    KEYS.forEach(key=>{const box=node('div','weight-control');const label=node('label','',LABELS[key]);label.htmlFor=`weight-${key}`;const value=node('output','',String(Math.round(rawWeights[key]*10)/10));value.id=`weight-value-${key}`;value.setAttribute('for',`weight-${key}`);label.append(value);const input=node('input');input.type='range';input.min='0';input.max='100';input.step='1';input.id=`weight-${key}`;input.value=String(rawWeights[key]);input.addEventListener('input',()=>{rawWeights[key]=Number(input.value);activePreset='';updatePresetButtons();if(normalizedWeights())render();else $('weightStatus').textContent='至少为一个维度保留权重；当前结果保留上次有效设置。';updateWeightLabels();});box.append(label,input);$('weightControls').append(box);});
    updateWeightLabels();
  }
  function updateWeightLabels() {const weights=normalizedWeights();KEYS.forEach(key=>{$(`weight-value-${key}`).textContent=weights?`${weights[key].toFixed(0)}%`:'0%';});if(weights)$('weightStatus').textContent='已按当前比例归一化为 100。';}
  function updatePresetButtons() {document.querySelectorAll('[data-preset]').forEach(button=>{button.classList.toggle('active',button.dataset.preset===activePreset);button.setAttribute('aria-pressed',String(button.dataset.preset===activePreset));});}
  function setWeights(weights) {rawWeights={...weights};KEYS.forEach(key=>{$(`weight-${key}`).value=String(rawWeights[key]);});updateWeightLabels();render();}
  function clearFilters() {$('searchInput').value='';$('providerFilter').value='';$('audienceFilter').value='';render();}

  function makeRail(item,weights,scores) {
    const wrap=node('div','evidence-rail');wrap.setAttribute('role','img');wrap.setAttribute('aria-label',`保守分 ${scoreText(scores.low)}，可能上界 ${scoreText(scores.upper)}，证据覆盖 ${percent(scores.coverage)}`);
    KEYS.forEach((key,index)=>{const value=numericCriterion(item,key),segment=node('span',`rail-segment${value===null?' unknown':''}`);segment.style.flexGrow=String(weights[key]);segment.style.flexBasis='0';segment.title=`${LABELS[key]} · 权重 ${weights[key].toFixed(1)}% · ${value===null?'未知':`${value}/5`}`;if(value!==null){const fill=node('i','rail-fill');fill.style.width=`${value/5*100}%`;fill.style.background=`var(--c${index})`;segment.append(fill);}wrap.append(segment);});return wrap;
  }
  function addListSection(grid,title,values,ordered=false) {const section=node('section');section.append(node('h4','',title));const entries=list(values);if(entries.length){const ul=node(ordered?'ol':'ul');entries.forEach(value=>ul.append(node('li','',value)));section.append(ul);}else section.append(node('p','','尚未记录，建议继续核查。'));grid.append(section);}
  function details(item) {
    const detail=node('details','row-detail');detail.append(node('summary','','依据、差距与学习入口'));
    const grid=node('div','detail-grid');
    const provenance=node('section','detail-full');provenance.append(node('h4','','候选从哪里来'));
    const discoveries=discoveryEntries(item),seen=new Set();
    if(!discoveries.length)provenance.append(node('p','','未记录候选发现方式，无法区分检索命中与明确提供的候选。'));
    discoveries.forEach(hit=>{const marker=`${hit.type}:${hit.query||''}`;if(seen.has(marker))return;seen.add(marker);const p=node('p');p.append(node('strong','',discoveryLabel(hit)));if(hit.type==='supplied')p.append(document.createTextNode(' · 由输入或种子清单明确提供，未计为搜索发现。'));if(hit.type==='search'){const query=string(hit.query);p.append(document.createTextNode(' · '));p.append(query?link(query,searchUrl(item.provider,query)) : node('span','','未记录检索词'));}provenance.append(p);});
    grid.append(provenance);
    const criteriaSection=node('section','detail-full');criteriaSection.append(node('h4','','逐项判断'));
    const criteriaGrid=node('div','criterion-grid');
    KEYS.forEach(key=>{const c=criterion(item,key),value=numericCriterion(item,key),box=node('div','criterion'),heading=node('div','criterion-heading');heading.append(node('strong','',LABELS[key]),node('span','',value===null?'未知':`${value.toFixed(1)} / 5`));box.append(heading,node('span','status-label',STATUS[c.status]||'判断来源未标明'),node('p','',string(c.reason,'尚未记录判断依据')));evidenceLinks(box,c.evidence);criteriaGrid.append(box);});
    criteriaSection.append(criteriaGrid);grid.append(criteriaSection);
    addListSection(grid,'值得借鉴',item.strengths);
    addListSection(grid,'缺口与使用条件',item.gaps);
    if(list(item.learning_path).length)addListSection(grid,'建议学习顺序',item.learning_path,true);
    const factsSection=node('section');factsSection.append(node('h4','','时间、许可与项目形态'));
    const facts=node('dl','facts');
    [['建仓',date(item.created_at)],['最近代码提交',date(item.last_commit_at)],['最近 Release',date(item.latest_release_at)],['最近推送',date(item.pushed_at)],['数据取得',date(item.retrieved_at)],['许可证',string(item.license,'未知')||'未知'],['项目形态',CATEGORIES[item.category]||string(item.category,'形态待确认')],['归档状态',item.archived===true?'已归档':item.archived===false?'未归档':'未知']].forEach(([label,value])=>facts.append(node('dt','',label),node('dd','',value)));
    factsSection.append(facts);grid.append(factsSection);
    const audienceSection=node('section');audienceSection.append(node('h4','','适用对象判断'),node('p','',AUDIENCES[labelAudience(item)]||'尚未确认'));if(item.audience&&typeof item.audience==='object'){audienceSection.append(node('p','',string(item.audience.reason,'尚无足够依据')));evidenceLinks(audienceSection,item.audience.evidence);}grid.append(audienceSection);
    const structural=node('section');structural.append(node('h4','','仓库结构信号'));const signals=node('div','signal-list');Object.entries(SIGNALS).forEach(([key,label])=>{const value=(item.signals||{})[key];signals.append(node('span',`signal${typeof value!=='boolean'?' unknown':''}`,`${label} ${value===true?'有':value===false?'未发现':'未知'}`));});structural.append(signals,node('p','control-help','文件存在不等于功能已完成；没有执行候选项目。'));grid.append(structural);
    const evidence=node('section','detail-full');evidence.append(node('h4','','证据来源'));
    const sources=Array.isArray(item.evidence)?item.evidence:[];
    if(!sources.length)evidence.append(node('p','','尚未附来源链接。'));
    sources.forEach((source,index)=>{if(typeof source==='string'){if(safeUrl(source)){const p=node('p');p.append(link(`来源 ${index+1}`,source));evidence.append(p);}return;}if(!source||typeof source!=='object')return;const p=node('p');p.append(link(string(source.kind,`来源 ${index+1}`),source.url));if(source.note)p.append(document.createTextNode(` · ${string(source.note)}`));evidence.append(p);});
    list(item.inspection_errors).forEach(error=>evidence.append(node('p','inspection-warning',error)));
    grid.append(evidence);detail.append(grid);return detail;
  }
  function makeRow(item,index,weights,scores) {
    const article=node('article',`result-row${selected.has(item._id)?' selected':''}`);article.dataset.projectId=item._id;
    const rank=node('div','rank-number',String(index+1).padStart(2,'0'));rank.append(node('small','','当前排序'));
    const main=node('div','result-main');const title=node('h3','project-title');title.append(link(string(item.name,'未命名项目'),item.url),node('span','provider-label',string(item.provider,'unknown')));main.append(title,node('p','project-summary',string(item.summary)||string(item.description)||'尚未记录项目摘要。'));
    const meta=node('div','project-meta');meta.append(node('span','chip audience',AUDIENCES[labelAudience(item)]||'尚未确认'));
    const stacks=list(item.stack).length?list(item.stack):(item.language?[String(item.language)]:[]);
    stacks.slice(0,4).forEach(value=>meta.append(node('span','chip stack',value)));
    if(item.archived===true)meta.append(node('span','chip warning','已归档'));
    const stars=node('span','metric-note',`★ ${compact(item.stars)}`);stars.title=`${format(item.stars)} Stars · ${string(item.provider,'来源未标明')}`;meta.append(stars);
    if(item.license)meta.append(node('span','metric-note',String(item.license)));
    main.append(meta,makeRail(item,weights,scores));
    const coverage=node('div','coverage-row');const known=node('span');known.append(document.createTextNode('已知依据 '),node('strong','',percent(scores.coverage)));const reviewed=node('span');reviewed.append(document.createTextNode('源码 / 资料核验 '),node('strong','',percent(scores.review)));coverage.append(known,reviewed);main.append(coverage);
    const score=node('div','score-cell');score.append(node('span','score-label','保守参考分'));const number=node('div');number.append(node('span','score-value',scoreText(scores.low)),node('span','score-max','/100'));score.append(number,node('div','score-range',scores.upper-scores.low>.04?`可能区间 ${scoreText(scores.low)}–${scoreText(scores.upper)}`:'当前维度均有判断'));
    const compareLabel=node('label','select-project');const checkbox=node('input');checkbox.type='checkbox';checkbox.checked=selected.has(item._id);checkbox.setAttribute('aria-label',`选择 ${string(item.name,'项目')} 进行对比`);checkbox.addEventListener('change',()=>{if(checkbox.checked){if(selected.size>=3){checkbox.checked=false;notify('每次最多对比 3 个项目。');return;}selected.add(item._id);}else selected.delete(item._id);article.classList.toggle('selected',checkbox.checked);updateCompareDock();});compareLabel.append(checkbox,document.createTextNode('加入对比'));score.append(compareLabel);
    article.append(rank,main,score,details(item));return article;
  }

  function render() {
    const weights=normalizedWeights();if(!weights)return;
    currentScores=new Map(items.map(item=>[item._id,compute(item,weights)]));
    const query=$('searchInput').value.toLocaleLowerCase().trim(),provider=$('providerFilter').value,audience=$('audienceFilter').value,sort=$('sortSelect').value;
    const filtered=items.filter(item=>{const haystack=[item.name,item.summary,item.description,item.language,...list(item.stack),...list(item.topics)].filter(Boolean).join(' ').toLocaleLowerCase();return (!query||haystack.includes(query))&&(!provider||item.provider===provider)&&(!audience||normalizeAudience(labelAudience(item))===audience);});
    filtered.sort((a,b)=>{const as=currentScores.get(a._id),bs=currentScores.get(b._id);if(sort==='stars'){const aa=typeof a.stars==='number'?a.stars:-1,bb=typeof b.stars==='number'?b.stars:-1;if(aa!==bb)return bb-aa;}if(sort==='updated'){const aa=Date.parse(a.last_commit_at)||0,bb=Date.parse(b.last_commit_at)||0;if(aa!==bb)return bb-aa;}return bs.low-as.low||bs.coverage-as.coverage||string(a.name).localeCompare(string(b.name),'en');});
    const fragment=document.createDocumentFragment();filtered.forEach((item,index)=>fragment.append(makeRow(item,index,weights,currentScores.get(item._id))));$('results').replaceChildren(fragment);$('resultCount').textContent=filtered.length;$('emptyState').hidden=filtered.length>0;updateCompareDock();
    if($('compareDialog').open)buildComparison();
  }
  function updateCompareDock() {const chosen=items.filter(item=>selected.has(item._id));$('compareDock').hidden=chosen.length===0;$('compareCount').textContent=`已选 ${chosen.length} / 3 个项目`;$('compareNames').textContent=chosen.map(item=>string(item.name)).join(' · ');$('compareButton').disabled=chosen.length<2;}
  function buildComparison() {
    const chosen=items.filter(item=>selected.has(item._id));const table=node('table','comparison-table');const thead=node('thead'),head=node('tr');const corner=node('th','','维度');corner.scope='col';head.append(corner);chosen.forEach(item=>{const th=node('th');th.scope='col';th.append(link(string(item.name,'项目'),item.url));head.append(th);});thead.append(head);table.append(thead);const body=node('tbody');
    const row=(label,renderCell)=>{const tr=node('tr'),heading=node('th','',label);heading.scope='row';tr.append(heading);chosen.forEach(item=>{const td=node('td');renderCell(td,item);tr.append(td);});body.append(tr);};
    row('综合保守分',(td,item)=>{const s=currentScores.get(item._id);td.append(node('strong','compare-score',scoreText(s.low)),node('p','',`可能区间 ${scoreText(s.low)}–${scoreText(s.upper)} / 100`),node('p','',`已知依据 ${percent(s.coverage)} · 源码核验 ${percent(s.review)}`));});
    row('技术栈',(td,item)=>td.append(node('span','',list(item.stack).join(' / ')||string(item.language,'未知'))));
    row('适用对象',(td,item)=>{td.append(node('span','',AUDIENCES[labelAudience(item)]||'尚未确认'));if(item.audience&&typeof item.audience==='object')td.append(node('p','',string(item.audience.reason)));});
    row('发现方式',(td,item)=>{const entries=discoveryEntries(item);td.append(node('span','',entries.length?[...new Set(entries.map(discoveryLabel))].join(' / '):'未记录'));});
    KEYS.forEach(key=>row(LABELS[key],(td,item)=>{const c=criterion(item,key),v=numericCriterion(item,key);td.append(node('strong','',v===null?'未知':`${v.toFixed(1)} / 5`),node('p','',string(c.reason,'尚无判断依据')));evidenceLinks(td,c.evidence);}));
    [['建仓',item=>date(item.created_at)],['最近代码提交',item=>date(item.last_commit_at)],['最近 Release',item=>date(item.latest_release_at)],['Star / Fork',item=>`${format(item.stars)} / ${format(item.forks)}`],['许可证',item=>string(item.license,'未知')||'未知']].forEach(([label,get])=>row(label,(td,item)=>td.append(node('span','',get(item)))));
    [['可借鉴点','strengths'],['缺口与条件','gaps'],['学习顺序','learning_path']].forEach(([label,key])=>row(label,(td,item)=>{const values=list(item[key]);if(!values.length){td.append(node('span','','尚未记录'));return;}const ul=node('ul');values.forEach(value=>ul.append(node('li','',value)));td.append(ul);}));table.append(body);$('compareContent').replaceChildren(table);
  }
  function reset() {clearFilters();activePreset='';updatePresetButtons();setWeights(initialWeights);$('sortSelect').value='score';render();}

  initBrief();buildWeightControls();
  ['searchInput','providerFilter','audienceFilter','sortSelect'].forEach(id=>$(id).addEventListener(id==='searchInput'?'input':'change',render));
  document.querySelectorAll('[data-preset]').forEach(button=>button.addEventListener('click',()=>{activePreset=button.dataset.preset;updatePresetButtons();setWeights(PRESETS[activePreset]);}));
  $('resetButton').addEventListener('click',reset);$('emptyReset').addEventListener('click',clearFilters);
  $('clearCompare').addEventListener('click',()=>{selected.clear();render();});
  $('compareButton').addEventListener('click',()=>{if(selected.size<2)return;buildComparison();$('compareDialog').showModal();});
  $('closeCompare').addEventListener('click',()=>$('compareDialog').close());
  $('compareDialog').addEventListener('click',event=>{if(event.target===$('compareDialog')){const box=$('compareDialog').getBoundingClientRect();if(event.clientX<box.left||event.clientX>box.right||event.clientY<box.top||event.clientY>box.bottom)$('compareDialog').close();}});
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&$('compareDialog').open)$('compareDialog').close();});
  $('printButton').addEventListener('click',()=>window.print());
  let theme='light';try{const saved=localStorage.getItem('repo-scout-theme');if(saved==='dark'||saved==='light')theme=saved;}catch{/* Storage can be disabled for local files. */}
  function applyTheme(){document.documentElement.dataset.theme=theme;$('themeButton').textContent=theme==='light'?'深色':'浅色';$('themeButton').setAttribute('aria-label',theme==='light'?'切换深色主题':'切换浅色主题');}
  applyTheme();$('themeButton').addEventListener('click',()=>{theme=theme==='light'?'dark':'light';applyTheme();try{localStorage.setItem('repo-scout-theme',theme);}catch{/* Offline rendering does not depend on storage. */}});
  render();
})();
