import { PaymentIcon } from 'react-svg-credit-card-payment-icons'
import type { BandeiraCartao } from '../../utils/validacaoCartao'

// Nome da nossa bandeira -> "type" que a lib de ícones espera. Quase todos
// batem 1:1; só "desconhecida" cai no ícone genérico dela.
const TIPO_ICONE: Record<BandeiraCartao, string> = {
  visa: 'visa',
  mastercard: 'mastercard',
  amex: 'amex',
  elo: 'elo',
  hipercard: 'hipercard',
  diners: 'diners',
  desconhecida: 'generic',
}

export function BandeiraCartaoIcon({ bandeira }: { bandeira: BandeiraCartao }) {
  return (
    <PaymentIcon
      type={TIPO_ICONE[bandeira]}
      format="flat"
      width={40}
      aria-label={bandeira !== 'desconhecida' ? bandeira : undefined}
    />
  )
}
