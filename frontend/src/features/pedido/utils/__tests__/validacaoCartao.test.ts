import { describe, it, expect, vi } from 'vitest'
import {
  formatarNumeroCartao,
  formatarValidade,
  numeroCartaoValido,
  validadeFutura,
  detectarBandeira,
  nomeBandeira,
} from '../validacaoCartao'

describe('formatarNumeroCartao', () => {
  it('agrupa os dígitos em blocos de 4', () => {
    expect(formatarNumeroCartao('4532015112830366')).toBe('4532 0151 1283 0366')
  })

  it('ignora caracteres que não são dígitos', () => {
    expect(formatarNumeroCartao('4532-0151-1283-0366')).toBe('4532 0151 1283 0366')
  })

  it('limita a 16 dígitos', () => {
    expect(formatarNumeroCartao('45320151128303661234')).toBe('4532 0151 1283 0366')
  })
})

describe('formatarValidade', () => {
  it('insere a barra depois do mês', () => {
    expect(formatarValidade('1228')).toBe('12/28')
  })

  it('não insere a barra com menos de 3 dígitos', () => {
    expect(formatarValidade('1')).toBe('1')
    expect(formatarValidade('12')).toBe('12')
  })

  it('ignora caracteres não numéricos e limita a 4 dígitos', () => {
    expect(formatarValidade('12/2028')).toBe('12/20')
  })
})

describe('numeroCartaoValido', () => {
  it('aceita um número que passa no algoritmo de Luhn', () => {
    expect(numeroCartaoValido('4532 0151 1283 0366')).toBe(true)
  })

  it('rejeita um número que não passa no Luhn', () => {
    expect(numeroCartaoValido('4532 0151 1283 0367')).toBe(false)
  })

  it('rejeita números curtos ou longos demais', () => {
    expect(numeroCartaoValido('123456789012')).toBe(false)
    expect(numeroCartaoValido('12345678901234567890')).toBe(false)
  })
})

describe('detectarBandeira', () => {
  it('identifica Visa pelo prefixo genérico 4', () => {
    expect(detectarBandeira('4532015112830366')).toBe('visa')
  })

  it('identifica Mastercard nas faixas 51-55 e 2221-2720', () => {
    expect(detectarBandeira('5412 3456 7890 1234')).toBe('mastercard')
    expect(detectarBandeira('2223000048400011')).toBe('mastercard')
  })

  it('identifica American Express (34/37)', () => {
    expect(detectarBandeira('374245455400126')).toBe('amex')
  })

  it('identifica Elo mesmo em BINs que começam com 4 (não deixa cair em Visa)', () => {
    expect(detectarBandeira('4011 7800 0000 0000')).toBe('elo')
    expect(detectarBandeira('5067 0000 0000 0000')).toBe('elo')
  })

  it('identifica Hipercard pelo BIN 606282', () => {
    expect(detectarBandeira('6062820000000000')).toBe('hipercard')
  })

  it('retorna desconhecida pra número vazio ou sem BIN reconhecido', () => {
    expect(detectarBandeira('')).toBe('desconhecida')
    expect(detectarBandeira('9999999999999999')).toBe('desconhecida')
  })
})

describe('nomeBandeira', () => {
  it('devolve o nome de exibição de cada bandeira', () => {
    expect(nomeBandeira('visa')).toBe('Visa')
    expect(nomeBandeira('mastercard')).toBe('Mastercard')
    expect(nomeBandeira('desconhecida')).toBe('')
  })
})

describe('validadeFutura', () => {
  it('aceita uma data no futuro', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-01-15'))
    expect(validadeFutura('06/28')).toBe(true)
    vi.useRealTimers()
  })

  it('rejeita uma data no passado', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-01-15'))
    expect(validadeFutura('12/25')).toBe(false)
    vi.useRealTimers()
  })

  it('rejeita o mês atual do ano atual como válido e o mês anterior como inválido', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-06-10'))
    expect(validadeFutura('06/26')).toBe(true)
    expect(validadeFutura('05/26')).toBe(false)
    vi.useRealTimers()
  })

  it('rejeita formato inválido', () => {
    expect(validadeFutura('2028')).toBe(false)
    expect(validadeFutura('13/28')).toBe(false)
  })
})
