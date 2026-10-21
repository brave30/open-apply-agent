import { applications, fieldsFor } from '../src/catalog.ts'
import { writeFileSync } from 'node:fs'
const data = applications.map(a => ({ ...a, fields: fieldsFor(a) }))
writeFileSync(new URL('../../fixtures/applications.json', import.meta.url), JSON.stringify(data, null, 2) + '\n')
const quote = s => `'${String(s).replaceAll("'", "''")}'`
const keys = ['id','platform','company','title','location','salary','department','description','variant']
const sql = `-- Generated from web/src/catalog.ts by web/scripts/generate-fixtures.mjs\ninsert into public.applications (${keys.join(',')}) values\n${applications.map(a => `(${keys.map(k => typeof a[k] === 'number' ? a[k] : quote(a[k])).join(',')})`).join(',\n')}\non conflict (id) do update set ${keys.slice(1).map(k => `${k}=excluded.${k}`).join(',')};\n`
writeFileSync(new URL('../../supabase/migrations/202610210002_catalog.sql', import.meta.url), sql)
console.log(`Generated ${data.length} fixtures and database seed rows.`)
