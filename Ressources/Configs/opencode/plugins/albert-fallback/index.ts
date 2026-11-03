import { Plugin } from "@opencode/plugin"

// Bascule automatique quand un modèle Albert épuise son quota de tokens
// (TPM/TPD), son nombre de requêtes (RPM/RPD), ou renvoie un 429.
// Chaque modèle Albert a son propre compteur, donc changer de modèle suffit
// à repartir immédiatement.
//
// L'ordre du repli se configure dans opencode.json :
//   "plugins": [{ "package": ".../albert-fallback", "options": { "chain": [...] } }]
const DEFAULT_CHAIN = [
  "albert/gpt-oss-120b",
  "albert/gemma-4-31b-it",
  "albert/mistral-small-3-2-24b-instruct-2506",
  "albert/ministral-3-8b-instruct-2512",
]

const QUOTA_ERROR =
  /rate.?limit|quota|too many requests|usage limit|tokens? (?:limit|exceeded)|capacity|exhausted|exceeded/i

function parseRef(ref: string) {
  const i = ref.indexOf("/")
  if (i <= 0) return undefined
  return { providerID: ref.slice(0, i), id: ref.slice(i + 1) }
}

export default Plugin.define({
  id: "albert-fallback",
  async setup(ctx) {
    const configured = ctx.options.chain
    const chain =
      Array.isArray(configured) && configured.length > 0
        ? configured.filter((value): value is string => typeof value === "string")
        : DEFAULT_CHAIN

    // Dernier modèle de la boucle principale par session. Les appels
    // techniques (titre, compaction, résumé) utilisent d'autres modèles :
    // on ne veut pas qu'un 429 sur ceux-ci change le modèle de la session.
    const primary = new Map<string, string>()

    await ctx.session.hook("context", (event) => {
      primary.set(event.sessionID, `${event.model.providerID}/${event.model.id}`)
    })

    await ctx.session.hook("retry", async (event) => {
      if (event.error.status !== 429 && !QUOTA_ERROR.test(event.error.message ?? "")) return

      const failed = `${event.model.providerID}/${event.model.id}`
      if (primary.get(event.sessionID) !== failed) return

      const index = chain.indexOf(failed)
      const nextRef = index >= 0 ? chain[index + 1] : chain[0]
      if (!nextRef) return
      const next = parseRef(nextRef)
      if (!next) return
      if (next.providerID === event.model.providerID && next.id === event.model.id) return

      console.log(`albert-fallback: quota atteint sur ${failed} -> bascule vers ${nextRef}`)
      await ctx.session.switchModel({ sessionID: event.sessionID, model: next })
      primary.set(event.sessionID, nextRef)
      event.decision = { retry: true, delay: 1000 }
    })
  },
})
