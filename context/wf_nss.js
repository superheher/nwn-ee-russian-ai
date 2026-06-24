export const meta = {
  name: 'nwn-translate-nss',
  description: 'Translate a premium NWN module\'s SCRIPT display strings (cutscene speech, floating/feedback text, custom tokens) EN→RU with glossary + code validation',
  phases: [ { title: 'Load' }, { title: 'Translate' }, { title: 'Repair' } ],
}

const PROOT = '/Users/heh/games/neverwinter-russian/nwn-ee-russian-ai'
let A = args
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }
A = A || {}
const inDir = A.inDir
const outDir = A.outDir
const glossPath = `${PROOT}/context/glossary_active.json`
if (!inDir || !outDir) throw new Error('need args.inDir and args.outDir')
log(`inDir=${inDir}`)

const LIST_SCHEMA = { type:'object', properties:{ batches:{ type:'array', items:{type:'string'} }, done:{ type:'array', items:{type:'string'} } }, required:['batches'] }
const TR_SCHEMA = { type:'object', properties:{ translations:{ type:'array', items:{ type:'object', properties:{ strref:{type:'integer'}, en:{type:'string'}, ru:{type:'string'} }, required:['strref','en','ru'] } } }, required:['translations'] }

function tagsOf(s){ return (String(s).match(/<[^>\n]+>/g) || []).filter(t=>!t.includes('/')).slice().sort() }
function braceOf(s){ return (String(s).match(/\{\d+\}/g) || []).slice().sort() }
function escN(s){ return (String(s).match(/\\n/g) || []).length }
function eqArr(a,b){ return a.length===b.length && a.every((x,i)=>x===b[i]) }
function validate(translations){
  const issues=[]
  for(const t of (translations||[])){
    const en=t.en||'', ru=t.ru||''
    if(!String(ru).trim()){ issues.push({strref:t.strref, problem:'empty RU'}); continue }
    if(!eqArr(braceOf(en),braceOf(ru))) issues.push({strref:t.strref, problem:`placeholder mismatch EN ${JSON.stringify(braceOf(en))} vs RU ${JSON.stringify(braceOf(ru))} — keep every {0},{1}… verbatim`})
    if(!eqArr(tagsOf(en),tagsOf(ru))) issues.push({strref:t.strref, problem:`tag mismatch EN ${JSON.stringify(tagsOf(en))} vs RU ${JSON.stringify(tagsOf(ru))}`})
    if(escN(en)!==escN(ru)) issues.push({strref:t.strref, problem:`\\n escape count EN=${escN(en)} RU=${escN(ru)} — keep the same number of \\n line breaks`})
    if(ru.includes('"')) issues.push({strref:t.strref, problem:'contains a " double-quote — use «ёлочки» instead (a literal " breaks the script string)'})
  }
  return issues
}

const RULES = `These strings are hard-coded inside a Neverwinter Nights premium module's SCRIPTS (NWScript). They are shown to the player at runtime: cutscene/NPC spoken lines, floating combat & feedback text above creatures, on-screen messages, area/round announcements, and custom tokens that get substituted into dialogue. Translate into natural, literary Russian, matching each speaker's register (peasants speak plainly/colloquially; knights & nobles formally; the "spirit/ring" lines are archaic — thou/thee → возвышенное «ты/тебе», старинный слог). Forgotten Realms proper nouns in standard Russian forms (Neverwinter→Невервинтер, Cormyr→Кормир, Waterdeep→Глубоководье); transliterate invented names consistently (use the glossary).`

const PLACEHOLDERS = `CRITICAL — {0}, {1}, … are runtime insertions (player name, a number, a creature name) spliced in by the game. Keep EVERY {N} EXACTLY (same digits, same count) and DO NOT reorder them. The surrounding Russian must read naturally AROUND the inserted value. When {N} is the player's NAME you CANNOT know its gender or case — phrase so NO verb/adjective agrees with it: put the name as a bare subject in the nominative + genderless predicate ("когда {0} снова дома"), or future tense ("{0} скоро вернётся"), or an invariant turn ("{0} — точь-в-точь как отец"). Never bend {0} into an oblique case (it is raw text, it will not decline).`

const COMMON = `${PLACEHOLDERS}
Keep literal \\n line breaks (backslash-n) exactly as in the source (same count). NEVER put a real double-quote " in the Russian — use «ёлочки»; a " would terminate the script string and break compilation. Preserve any <...> color/token tags verbatim. Russian typography: «ёлочки», em dash —, use ё. ${RULES}`

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

let repaired = 0
const results = await pipeline(
  batches,
  (b) => agent(
`Translate a batch of Neverwinter Nights module SCRIPT strings EN→RU.

Read:
1. ${inDir}/${b}.json — has "terms":[{strref, en}]. Translate EVERY term. (Strings from the same script are adjacent — use that context; a run of lines is usually one cutscene conversation.)
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
`Repair placeholder/quote/newline errors in a translated NWN script batch.

Read:
1. ${inDir}/${b}.json — source terms (strref, en).
2. ${outDir}/${b}.json — the draft Russian (strref→ru).
3. ${glossPath} — mandatory terms.

Code-validation flagged these (fix ALL):
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
