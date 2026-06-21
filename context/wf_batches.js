export const meta = {
  name: 'nwn-translate-batches',
  description: 'Translate NWN system/other text in category batches with glossary + code validation',
  phases: [
    { title: 'Load' },
    { title: 'Translate' },
    { title: 'Repair' },
  ],
}

const PROOT = '/Users/heh/Downloads/neverwi/nwn_ru_mac'
let A = args
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }
A = A || {}
const kind = A.kind || 'sys'                 // 'sys' | 'other'
const inDir = kind === 'sys' ? `${PROOT}/context/sysbatches` : `${PROOT}/context/otherbatches`
const outDir = `${PROOT}/context/translated/${kind}`
const glossPath = `${PROOT}/context/glossary_active.json`
log(`kind=${kind}; inDir=${inDir}`)

const LIST_SCHEMA = { type:'object', properties:{ batches:{ type:'array', items:{type:'string'} } }, required:['batches'] }
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

const KIND_RULES = kind === 'sys'
  ? `These are Dungeons & Dragons game terms from 2da tables: spell/feat names & descriptions, item-property labels, class/skill labels. Use established Russian D&D (3.5e) terminology, consistent with the glossary. Names: concise noun phrases. Descriptions: preserve game-mechanic meaning precisely.`
  : `These are player-facing strings with NO conversation context: item names & descriptions, creature & placeable names, journal/quest entries, combat barks, UI/system messages. Translate into natural literary Russian; keep barks short and punchy.`

phase('Load')
const listed = await agent(
  `List the .json files in ${inDir} (use shell: ls). Return their basenames WITHOUT the .json extension as "batches". Do not translate anything.`,
  { label:`list:${kind}`, phase:'Load', schema:LIST_SCHEMA, agentType:'general-purpose' }
)
let batches = (listed && listed.batches) || []
if (A.limit) batches = batches.slice(0, A.limit)
log(`${kind}: ${batches.length} batches queued`)

const COMMON = `Preserve identifier <...> tags, printf %s/%d/%c placeholders, literal newlines and numbers EXACTLY (same count, same spelling). EXCEPTION: gender-fork tokens like <man/woman>, <he/she>, <his/her> must be replaced with natural Russian (they print English by gender). Russian typography: «ёлочки», em dash —, use ё. ${KIND_RULES}`

let repaired = 0
const results = await pipeline(
  batches,
  (b) => agent(
`Translate a batch of Neverwinter Nights game strings EN→RU.

Read:
1. ${inDir}/${b}.json — has "terms":[{strref, en}] (sys batches also carry "cat"/"role"). Translate EVERY term.
2. ${glossPath} — mandatory glossary terms; use the exact Russian whenever an English term appears.

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
`Repair tag/placeholder/newline errors in a translated NWN batch.

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
log(`${kind}: done ${done.length}/${batches.length}; repaired strings: ${repaired}; failed: ${failed.length}`)
return {
  kind,
  batches: batches.length,
  done: done.length,
  total_strings: done.reduce((s,r)=>s+r.n,0),
  repaired,
  failed,
}
