export function formatarNumeroCartao(valor: string): string {
  return valor.replace(/\D/g, '').slice(0, 16).replace(/(.{4})/g, '$1 ').trim()
}

export function formatarValidade(valor: string): string {
  const digitos = valor.replace(/\D/g, '').slice(0, 4)
  return digitos.length > 2 ? `${digitos.slice(0, 2)}/${digitos.slice(2)}` : digitos
}

// Mesma checagem de Luhn feita no backend; usada aqui só pra dar feedback
// imediato no formulário antes de chamar a API.
export function numeroCartaoValido(numeroCartao: string): boolean {
  const digitos = numeroCartao.replace(/\s/g, '')
  if (digitos.length < 13 || digitos.length > 19) return false

  let soma = 0
  let dobrar = false
  for (let i = digitos.length - 1; i >= 0; i--) {
    let digito = parseInt(digitos[i], 10)
    if (dobrar) {
      digito *= 2
      if (digito > 9) digito -= 9
    }
    soma += digito
    dobrar = !dobrar
  }
  return soma % 10 === 0
}

export type BandeiraCartao =
  | 'visa'
  | 'mastercard'
  | 'amex'
  | 'elo'
  | 'hipercard'
  | 'diners'
  | 'desconhecida'

// Detecção por faixa de BIN (os primeiros dígitos do cartão). Cobre as
// bandeiras mais comuns no Brasil; Elo em particular não publica uma tabela
// de BIN oficial completa, então essa lista pega os prefixos mais usuais,
// não é exaustiva.
export function detectarBandeira(numeroCartao: string): BandeiraCartao {
  const digitos = numeroCartao.replace(/\D/g, '')
  if (digitos.length === 0) return 'desconhecida'

  // Elo tem vários BINs que começam com 4 (mesmo prefixo genérico da Visa) -
  // por isso precisa ser checado antes do teste genérico "^4" da Visa,
  // senão esses cartões nunca seriam identificados como Elo.
  if (/^(4011|4312|4389|4514|4573|4576|5041|5066|5067|509\d|6362|6363|6500|6504|6505|6509|6516|6550)/.test(digitos)) return 'elo'
  if (/^3[47]/.test(digitos)) return 'amex'
  if (/^3(0[0-5]|[68]\d)/.test(digitos)) return 'diners'
  if (/^606282/.test(digitos)) return 'hipercard'
  if (/^4/.test(digitos)) return 'visa'
  if (/^(5[1-5]\d{2}|222[1-9]|22[3-9]\d|2[3-6]\d{2}|27[01]\d|2720)/.test(digitos)) return 'mastercard'
  return 'desconhecida'
}

const NOME_BANDEIRA: Record<BandeiraCartao, string> = {
  visa: 'Visa',
  mastercard: 'Mastercard',
  amex: 'American Express',
  elo: 'Elo',
  hipercard: 'Hipercard',
  diners: 'Diners Club',
  desconhecida: '',
}

export function nomeBandeira(bandeira: BandeiraCartao): string {
  return NOME_BANDEIRA[bandeira]
}

export function validadeFutura(validade: string): boolean {
  const match = validade.match(/^(\d{2})\/(\d{2})$/)
  if (!match) return false

  const mes = parseInt(match[1], 10)
  const ano = 2000 + parseInt(match[2], 10)
  if (mes < 1 || mes > 12) return false

  const agora = new Date()
  const anoAtual = agora.getFullYear()
  const mesAtual = agora.getMonth() + 1

  if (ano < anoAtual) return false
  if (ano === anoAtual && mes < mesAtual) return false
  return true
}
