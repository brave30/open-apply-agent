import { describe, expect, it } from 'vitest'
import { applications, fieldsFor } from './catalog'
import { matchProfile } from './profile-matching'
import { emptyProfile } from './types'

describe('application coverage', () => {
  it('contains exactly five distinct applications per platform', () => {
    expect(applications).toHaveLength(20)
    expect(new Set(applications.map(a => a.id)).size).toBe(20)
    for (const p of ['Workday','Greenhouse','Lever','Other']) expect(applications.filter(a => a.platform === p)).toHaveLength(5)
    expect(new Set(applications.map(a => fieldsFor(a).find(f => f.id === 'custom_answer')!.label)).size).toBe(5)
  })
})
describe('profile matching', () => {
  it('leaves unknown questions unanswered and refuses ambiguous education', () => {
    const p = emptyProfile('candidate', 'person@example.test')
    p.personal.full_name = 'Test Person'
    p.education = [{school:'A',degree:'BA',field:'Art',graduation_year:2020},{school:'B',degree:'MA',field:'Art',graduation_year:2022}]
    const result = matchProfile(fieldsFor(applications[0]), p)
    expect(result.full_name).toBe('Test Person')
    expect(result.email).toBe('person@example.test')
    expect(result.school).toBeUndefined()
    expect(result.salary).toBeUndefined()
    expect(result.motivation).toBeUndefined()
  })
  it('only uses dated verified answers and rejects conflicting verified answers', () => {
    const p = emptyProfile()
    const a = {question:'Are you authorized to work in the United States?',value:'Yes',verified:true,verified_at:'2026-10-21',source:'Candidate'}
    p.verified_answers = [{...a,verified:false}]
    expect(matchProfile(fieldsFor(applications[0]),p).work_authorization).toBeUndefined()
    p.verified_answers = [a]
    expect(matchProfile(fieldsFor(applications[0]),p).work_authorization).toBe('Yes')
    p.verified_answers.push({...a,value:'No'})
    expect(matchProfile(fieldsFor(applications[0]),p).work_authorization).toBeUndefined()
  })
})
