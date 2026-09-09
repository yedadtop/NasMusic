// 生成 MDI 图标子集：扫描 src 中实际用到的 mdi:* 图标名，
// 从 @iconify-json/mdi 全量集合中抽取，生成 src/icons-subset.ts
// 新增图标后重新执行：npm run generate:icons（dev/build 已自动执行）
import { readFileSync, writeFileSync, readdirSync, statSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const srcDir = join(root, 'src')

// 1. 扫描源码，收集所有 mdi: 图标名
const used = new Set()
function scan(dir) {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name)
    if (statSync(full).isDirectory()) {
      scan(full)
    } else if (/\.(vue|ts|tsx|js|jsx)$/.test(name)) {
      const content = readFileSync(full, 'utf8')
      for (const m of content.matchAll(/mdi:([a-z0-9-]+)/g)) {
        used.add(m[1])
      }
    }
  }
}
scan(srcDir)

// 2. 从全量集合中抽取（含别名及别名指向的父级图标）
const full = JSON.parse(
  readFileSync(join(root, 'node_modules', '@iconify-json/mdi', 'icons.json'), 'utf8')
)
const icons = {}
const aliases = {}
const included = new Set()

function resolve(name) {
  if (included.has(name)) return
  included.add(name)
  if (full.icons[name]) {
    icons[name] = full.icons[name]
  } else if (full.aliases[name]) {
    aliases[name] = full.aliases[name]
    const parent = full.aliases[name].parent
    if (parent) resolve(parent)
  } else {
    console.warn(`[generate-icons] 警告: 未在 MDI 集合中找到图标 "${name}"`)
  }
}
for (const name of used) resolve(name)

const subset = { prefix: full.prefix, icons }
if (Object.keys(aliases).length) subset.aliases = aliases

// 3. 输出为 TS 模块（避免依赖 resolveJsonModule）
const out = join(root, 'src', 'icons-subset.ts')
const body = JSON.stringify(subset)
writeFileSync(out, `// 本文件由 scripts/generate-icons.mjs 自动生成，请勿手动编辑\nexport default ${body}\n`)

console.log(
  `[generate-icons] 用到 ${used.size} 个图标，生成子集：` +
  `${Object.keys(icons).length} 个图标 + ${Object.keys(aliases).length} 个别名 -> src/icons-subset.ts`
)
