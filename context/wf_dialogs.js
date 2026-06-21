export const meta = {
  name: 'nwn-translate-dialogs',
  description: 'Translate NWN dialog conversations EN→RU with context; adversarial editor always runs',
  phases: [
    { title: 'Load' },
    { title: 'Translate' },
    { title: 'Edit' },
  ],
}

const PROOT = '/Users/heh/Downloads/neverwi/nwn_ru_mac'
let A = args
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }
A = A || {}
const manifestPath = A.manifest || null      // JSON array of {source, resref}
const safe = A.safe || 'Prelude'             // used when no manifest
const model = A.model || 'opus'
const glossPath = `${PROOT}/context/glossary_active.json`
log(`manifest=${manifestPath || '(single '+safe+')'}; model=${model}`)

const WORK_SCHEMA = { type:'object', properties:{ work:{ type:'array', items:{ type:'object', properties:{ source:{type:'string'}, resref:{type:'string'} }, required:['resref'] } } }, required:['work'] }
const TR_SCHEMA = { type:'object', properties:{ ok:{type:'boolean'}, count:{type:'integer'} }, required:['ok'] }
const ED_SCHEMA = { type:'object', properties:{ count:{type:'integer'}, edits:{ type:'array', items:{ type:'object', properties:{ strref:{type:'integer'}, problem:{type:'string'} } } } }, required:['count'] }

const RULES = `Rules (mandatory):
- Translate EVERY line in "lines" into natural, idiomatic literary Russian. The "script" field is CONTEXT ONLY — do not translate it.
- Preserve identifier tags EXACTLY (same count & spelling): <FullName>, <FirstName>, <CUSTOM0>, <Race>, <Deity>, <StartAction>...<Stop>, etc.; never translate or reorder text inside them. Also preserve printf %s %d %c %f %% and literal newlines.
- EXCEPTION — gender-fork tokens that print an English word by gender (<man/woman>, <boy/girl>, <he/she>, <his/her>, <him/her>, <lad/lass>, <brother/sister>, <sir/madam>, <lord/lady>) MUST be replaced with natural Russian (usually a neutral noun/pronoun, e.g. <man/woman>→«человек»), since leaving them prints English mid-sentence.
- Register: choose ты or вы per relationship and keep it CONSISTENT across the whole conversation (judge from the script). NPCs addressing the player-hero generally use ты unless noble/formal.
- Low-Intelligence "caveman" PC lines (broken English: "Me need spell-stuff", "Me not know what guild is") MUST be rendered as BROKEN Russian — «моя/твоя» + infinitive, broken agreement (e.g. "Моя не знать", "Твоя сказать?"). Never normalize them. The script shows correct-grammar siblings for contrast; keep the broken ones broken.
- Glossary terms (context/glossary_active.json "terms") are MANDATORY: use the exact Russian whenever the English term appears. Reserve "Чародей" for the Sorcerer class; translate the generic word "spellcasters" as "заклинатели".
- Proper nouns consistent with Forgotten Realms Russian tradition (Neverwinter→Невервинтер, Waterdeep→Глубоководье, Aribeth→Арибет, Luskan→Лускан).
- Russian typography: «ёлочки» quotes, em dash —, use ё. Do not add or drop sentences.`

phase('Load')
let work
if (manifestPath) {
  const loaded = await agent(
    `Read the JSON file ${manifestPath}. It is an array of objects {source, resref}. Return it verbatim as "work" (do not translate anything).`,
    { label:'load:manifest', phase:'Load', schema: WORK_SCHEMA, agentType:'general-purpose' }
  )
  work = (loaded && loaded.work) || []
} else {
  const loaded = await agent(
    `Read the JSON file ${PROOT}/context/worklists/${safe}.json. It has a "work" array of {resref, n}. Return each as {source:"${safe}", resref} in a "work" array.`,
    { label:`load:${safe}`, phase:'Load', schema: WORK_SCHEMA, agentType:'general-purpose' }
  )
  work = ((loaded && loaded.work) || []).map(w => ({ source: safe, resref: w.resref }))
}
log(`${work.length} conversations queued`)

let editTotal = 0
const editSamples = []

const results = await pipeline(
  work,
  // stage 1: translate with context, write the file (no redundant structured echo)
  (w) => {
    const cdir = `${PROOT}/context/convos/${w.source}`
    const odir = `${PROOT}/context/translated/${w.source}`
    return agent(
`You are translating ONE Neverwinter Nights conversation EN→RU for a context-aware fan translation.

Read:
1. ${cdir}/${w.resref}.json — the conversation. "script" = full NPC/PC tree (context, with @strref); "lines" = array of {strref, role, en} you must translate.
2. ${glossPath} — {"terms":{EN:RU}, "overrides":{...}} mandatory terminology.

${RULES}

Then Write a JSON object mapping each strref (string key) to its Russian string to ${odir}/${w.resref}.json (compact, UTF-8, ONLY the strref→ru map, every line in "lines"). Return {ok:true, count:<number of lines>}.`,
      { label:`tr:${w.source}/${w.resref}`, phase:'Translate', schema: TR_SCHEMA, agentType:'general-purpose', model }
    )
  },
  // stage 2: adversarial editor ALWAYS runs; reads the draft file directly
  (tr, w) => {
    const cdir = `${PROOT}/context/convos/${w.source}`
    const odir = `${PROOT}/context/translated/${w.source}`
    return agent(
`You are the ADVERSARIAL EDITOR for a Neverwinter Nights EN→RU fan translation. Review and FIX one conversation's draft.

Read:
1. ${cdir}/${w.resref}.json — source (script context + lines with en).
2. ${odir}/${w.resref}.json — the DRAFT Russian (strref→ru). If it is missing or incomplete, translate the missing lines yourself from the source.
3. ${glossPath} — mandatory terms.

${RULES}

Adversarially check EVERY line and FIX:
- TAG/PLACEHOLDER/NEWLINE integrity (hardest): every identifier <...>, %s/%d and \\n in EN present in RU with same count/spelling; gender-fork tokens replaced with Russian.
- Glossary compliance ("Чародей" only for Sorcerer; generic spellcasters→"заклинатели").
- ты/вы register CONSISTENT across the whole conversation; fix lone slips (e.g. a stray formal "Прощайте" in a ты conversation → "Прощай").
- Low-INT caveman lines stay broken Russian (моя/твоя), not normalized.
- Meaning drift, omissions, additions, unnatural calque; naturalness and tone; proper-noun consistency.

Then OVERWRITE ${odir}/${w.resref}.json with the corrected strref→ru JSON object (ALL lines, not only changed ones). Return {count:<lines>, edits:[{strref, problem}]} listing what you changed (may be empty).`,
      { label:`ed:${w.source}/${w.resref}`, phase:'Edit', schema: ED_SCHEMA, agentType:'general-purpose', model }
    ).then(ed => {
      const ne = (ed && ed.edits) ? ed.edits.length : 0
      editTotal += ne
      if(ne && editSamples.length < 15) editSamples.push({resref:`${w.source}/${w.resref}`, edits:ed.edits.slice(0,2)})
      return { resref:`${w.source}/${w.resref}`, lines:(ed&&ed.count)||0, edits:ne }
    })
  }
)

const done = results.filter(Boolean)
const failed = work.filter((w,i)=>!results[i]).map(w=>`${w.source}/${w.resref}`)
log(`done ${done.length}/${work.length}; editor edits: ${editTotal}; failed: ${failed.length}`)
return {
  manifest: manifestPath || safe, model,
  conversations: work.length,
  translated: done.length,
  editor_edits: editTotal,
  failed,
  edit_samples: editSamples,
}
