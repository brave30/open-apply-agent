import type { CandidateProfile, Field } from './types'
const normalized = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()
export function matchProfile(fields: Field[], p: CandidateProfile): Record<string, string> {
  const facts: Record<string, string> = { full_name: p.personal.full_name, email: p.personal.email, phone: p.personal.phone, city: p.personal.city, linkedin: p.personal.linkedin, skills: p.skills.join(', ') }
  if (p.education.length === 1) Object.assign(facts, { school: p.education[0].school, degree: p.education[0].degree })
  if (p.work_experience.length === 1) Object.assign(facts, { employer: p.work_experience[0].employer, job_title: p.work_experience[0].title })
  const result: Record<string, string> = {}
  for (const f of fields) {
    const answers = p.verified_answers.filter(a => a.verified && a.verified_at && a.value && normalized(a.question) === normalized(f.label))
    const candidates = new Set(answers.map(a => a.value))
    if (facts[f.id]) candidates.add(facts[f.id])
    if (candidates.size !== 1) continue
    const value = [...candidates][0]
    if (f.options && !f.options.includes(value)) continue
    result[f.id] = value
  }
  return result
}
