const WATCHED = new Set(["edit", "write", "patch"])
const RUNNER_TIMEOUT_MS = 120000

const PROJECT_DIR = new URL("../..", import.meta.url).pathname.replace(/\/$/, "")
const LOG_PATH = PROJECT_DIR + "/evidence/hook-runs.txt"

async function runCheck() {
  const { spawnSync } = await import("node:child_process")
  const result = spawnSync("sh", ["scripts/check.sh"], {
    cwd: PROJECT_DIR,
    encoding: "utf8",
    timeout: RUNNER_TIMEOUT_MS,
  })
  const text = [result.stdout, result.stderr].filter(Boolean).join("\n").trim()
  return { ok: result.status === 0, text: text || "(раннер не дал вывода)" }
}

async function append(line) {
  const fs = await import("node:fs")
  fs.appendFileSync(LOG_PATH, new Date().toISOString() + " " + line + "\n")
}

export default {
  id: "check-after-edit",
  async setup(ctx) {
    await ctx.tool.hook("execute.after", async (event) => {
      if (!WATCHED.has(event.tool)) return
      if (event.status !== "completed") return

      const check = await runCheck()
      const verdict = check.ok ? "PASS" : "FAIL"
      await append(`${verdict} после ${event.tool}`)

      const note =
        `\n\n[check-after-edit] ${verdict} — sh scripts/check.sh\n${check.text}\n` +
        (check.ok
          ? "Проверка проекта зелёная."
          : "Проверка проекта красная. Исправь причину, раннер ослаблять нельзя.")

      const parts = Array.isArray(event.result?.content) ? event.result.content : []
      const output = typeof event.result?.output === "string" ? event.result.output : ""

      event.result = {
        ...event.result,
        output: output + note,
        content: [...parts, { type: "text", text: note }],
        metadata: { ...(event.result?.metadata ?? {}), checkAfterEdit: verdict },
      }
    })
  },
}
