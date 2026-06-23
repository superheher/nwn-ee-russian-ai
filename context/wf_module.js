export const meta = {
  name: 'nwn-translate-module',
  description: 'Translate a premium NWN module\'s embedded text (batches) EN→RU with glossary + code validation',
  phases: [ { title: 'Load' }, { title: 'Translate' }, { title: 'Repair' } ],
}

const PROOT = '/Users/heh/Downloads/neverwi/nwn_ru_mac'
let A = args
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }
A = A || {}
const inDir = A.inDir || `${PROOT}/ddf/batches`
const outDir = A.outDir || `${PROOT}/ddf/translated`
const glossPath = `${PROOT}/context/glossary_active.json`
log(`inDir=${inDir}`)

const LIST_SCHEMA = { type:'object', properties:{ batches:{ type:'array', items:{type:'string'} }, done:{ type:'array', items:{type:'string'} } }, required:['batches'] }
const TR_SCHEMA = { type:'object', properties:{ translations:{ type:'array', items:{ type:'object', properties:{ strref:{type:'integer'}, en:{type:'string'}, ru:{type:'string'} }, required:['strref','en','ru'] } } }, required:['translations'] }

function tagsOf(s){ return (String(s).match(/<[^>\n]+>/g) || []).filter(t=>!t.includes('/')).slice().sort() }
function phOf(s){ return (String(s).match(/%[-+ 0-9.]*[sdifcuxXeg%]/g) || []).slice().sort() }
function nl(s){ return (String(s).match(/\n/g) || []).length }
function eqArr(a,b){ return a.length===b.length && a.every((x,i)=>x===b[i]) }
function validate(translations){
  const issues=[]
  for(const t of (translations||[])){
    const en=t.en||'', ru=t.ru||''
    if(!String(ru).trim()){ issues.push({strref:t.strref, problem:'empty RU'}); continue }
    if(!eqArr(tagsOf(en),tagsOf(ru))) issues.push({strref:t.strref, problem:`tag mismatch EN ${JSON.stringify(tagsOf(en))} vs RU ${JSON.stringify(tagsOf(ru))}`})
    if(!eqArr(phOf(en),phOf(ru))) issues.push({strref:t.strref, problem:`placeholder mismatch EN ${JSON.stringify(phOf(en))} vs RU ${JSON.stringify(phOf(ru))}`})
    if(nl(en)!==nl(ru)) issues.push({strref:t.strref, problem:`newline count EN=${nl(en)} RU=${nl(ru)}`})
  }
  return issues
}

const RULES = `These are strings from a Neverwinter Nights premium MODULE: NPC dialogue lines, journal/quest entries, area names, creature & item names and descriptions (mixed together, one batch may span several). Translate into natural, literary Russian — dialogue as natural speech (keep each character's register), names as concise noun phrases, descriptions preserving game meaning. Forgotten Realms proper nouns in standard Russian forms (Neverwinter→Невервинтер, Waterdeep→Глубоководье, etc.); transliterate invented names sensibly and consistently.`

phase('Load')
const listed = await agent(
  `List .json basenames (WITHOUT .json) in two directories via shell ls.
Return "batches": every basename in ${inDir}; "done": every basename in ${outDir} (if it errors/missing, empty list). Do not translate.`,
  { label:'list', phase:'Load', schema:LIST_SCHEMA, agentType:'general-purpose' }
)
let batches = (listed && listed.batches) || []
const doneSet = new Set((listed && listed.done) || [])
const already = batches.filter(b => doneSet.has(b)).length
batches = batches.filter(b => !doneSet.has(b))
if (A.limit) batches = batches.slice(0, A.limit)
log(`${batches.length} batches queued (${already} already done, skipped)`)

const COMMON = `Preserve identifier <...> tags EXACTLY (same count/spelling): e.g. <FirstName>, <CUSTOM103>, <StartAction>…</Start>. Preserve printf %s/%d/%c placeholders and literal newlines exactly. EXCEPTION: gender-fork tokens like <he/she>, <his/her>, <lord/lady> must be replaced with natural Russian (they print English by gender). Action labels inside brackets (e.g. <StartAction>[Attack.]</Start>) — translate the bracketed text, keep the tags. Russian typography: «ёлочки», em dash —, use ё. ${RULES}`

let repaired = 0
const results = await pipeline(
  batches,
  (b) => agent(
`Translate a batch of Neverwinter Nights module strings EN→RU.

Read:
1. ${inDir}/${b}.json — has "terms":[{strref, en}]. Translate EVERY term. (Strings from the same conversation are adjacent — use that context.)
2. ${glossPath} — mandatory glossary; use the exact Russian whenever an English term appears.

${COMMON}

Then DO BOTH:
A) Write a JSON object mapping each strref (string key) to its Russian string to ${outDir}/${b}.json (compact, UTF-8, only the map).
B) Return {translations:[{strref, en, ru}]} for every term (en verbatim).`,
    { label:`tr:${b}`, phase:'Translate', schema:TR_SCHEMA, agentType:'general-purpose' }
  ),
  (tr, b) => {
    if(!tr || !tr.translations) throw new Error('translate failed for '+b)
    const issues = validate(tr.translations)
    if(!issues.length) return { batch:b, n:tr.translations.length, repaired:0 }
    repaired += issues.length
    const issuesText = issues.map(i=>`@${i.strref}: ${i.problem}`).join('\n')
    return agent(
`Repair tag/placeholder/newline errors in a translated NWN module batch.

Read:
1. ${inDir}/${b}.json — source terms (strref, en).
2. ${outDir}/${b}.json — the draft Russian (strref→ru).
3. ${glossPath} — mandatory terms.

Code-validation flagged these (fix ALL — make every <...> tag, %s/%d placeholder and newline in RU match the EN exactly):
${issuesText}

${COMMON}

Then OVERWRITE ${outDir}/${b}.json with the corrected strref→ru object (ALL terms) and return {translations:[{strref, en, ru}]}.`,
      { label:`fix:${b}`, phase:'Repair', schema:TR_SCHEMA, agentType:'general-purpose' }
    ).then(()=>({ batch:b, n:tr.translations.length, repaired:issues.length }))
  }
)

const done = results.filter(Boolean)
const failed = batches.filter((b,i)=>!results[i])
log(`done ${done.length}/${batches.length}; repaired strings: ${repaired}; failed: ${failed.length}`)
return { batches: batches.length, done: done.length, total_strings: done.reduce((s,r)=>s+r.n,0), repaired, failed }
