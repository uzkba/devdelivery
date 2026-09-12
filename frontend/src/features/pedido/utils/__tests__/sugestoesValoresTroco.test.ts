import { describe, it, expect } from 'vitest'
import { suggestChangeAmounts } from '../sugestoesValoresTroco'


describe('suggestChangeAmounts', () => {
  it('sugere as duas cédulas mais próximas acima do total', () => {
    expect(suggestChangeAmounts(27)).toEqual([50, 100])
  })

  it('pula cédulas menores ou iguais ao total', () => {
    expect(suggestChangeAmounts(45)).toEqual([50, 100])
    expect(suggestChangeAmounts(50)).toEqual([100, 200])
  })

  it('cai no fallback de +50 quando não sobram cédulas suficientes na lista', () => {
    // só sobra a cédula de 200 acima do total; a segunda sugestão vem do fallback
    expect(suggestChangeAmounts(180)).toEqual([200, 250])
  })

  it('usa só o fallback quando nenhuma cédula é maior que o total', () => {
    expect(suggestChangeAmounts(250)).toEqual([300, 350])
  })

  it('respeita a quantidade pedida', () => {
    expect(suggestChangeAmounts(27, 1)).toEqual([50])
    expect(suggestChangeAmounts(27, 3)).toEqual([50, 100, 200])
  })

  it('nunca sugere um valor menor ou igual ao total', () => {
    const total = 63.5
    const sugestoes = suggestChangeAmounts(total, 3)
    sugestoes.forEach((valor) => expect(valor).toBeGreaterThan(total))
  })
})
