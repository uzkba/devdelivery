import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import type { CartItem, Address } from '../types/checkout'
import { pagarComCartao } from '../services/pagamentoService'
import {
  formatarNumeroCartao,
  formatarValidade,
  numeroCartaoValido,
  validadeFutura,
  detectarBandeira,
} from '../utils/validacaoCartao'
import { BandeiraCartaoIcon } from '../components/BandeiraCartaoIcon'


type CardMethod = 'CARTAO_CREDITO' | 'CARTAO_DEBITO'
type CardStatus = 'form' | 'processing' | 'approved' | 'declined'

const METHOD_LABEL: Record<CardMethod, string> = {
  CARTAO_CREDITO: 'Cartão de crédito',
  CARTAO_DEBITO: 'Cartão de débito',
}

function formatMoney(value: number): string {
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

interface CamposTocados {
  number: boolean
  name: boolean
  expiry: boolean
  cvv: boolean
}

export default function CartaoPage() {
  const navigate = useNavigate()
  const { state } = useLocation()
  const { cartItems = [], address = null, method = 'CARTAO_CREDITO', total = 0 } =
    (state ?? {}) as { cartItems: CartItem[]; address: Address | null; method: CardMethod; total: number }

  const [cardNumber, setCardNumber] = useState('')
  const [cardName, setCardName] = useState('')
  const [expiry, setExpiry] = useState('')
  const [cvv, setCvv] = useState('')
  const [status, setStatus] = useState<CardStatus>('form')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [touched, setTouched] = useState<CamposTocados>({
    number: false, name: false, expiry: false, cvv: false,
  })

  function marcarTocado(campo: keyof CamposTocados) {
    setTouched((t) => ({ ...t, [campo]: true }))
  }

  const numDigits = cardNumber.replace(/\s/g, '').length
  const bandeira = detectarBandeira(cardNumber)

  // Validado campo a campo, pra dar feedback específico em vez de só travar
  // o botão sem dizer o motivo.
  const numeroOk = numDigits >= 13 && numDigits <= 16 && numeroCartaoValido(cardNumber)
  const nomeOk = cardName.trim().length >= 3
  const validadeOk = expiry.length === 5 && validadeFutura(expiry)
  const cvvOk = cvv.length >= 3

  const numeroErro = touched.number && cardNumber.length > 0 && !numeroOk
    ? 'Número de cartão inválido'
    : undefined
  const nomeErro = touched.name && cardName.length > 0 && !nomeOk
    ? 'Digite o nome completo como está no cartão'
    : undefined
  const validadeErro = touched.expiry && expiry.length > 0 && !validadeOk
    ? (expiry.length < 5 ? 'Data incompleta' : 'Cartão vencido ou data inválida')
    : undefined
  const cvvErro = touched.cvv && cvv.length > 0 && !cvvOk
    ? 'Código incompleto'
    : undefined

  const isValid = numeroOk && nomeOk && validadeOk && cvvOk
  const algumCampoInvalido = Object.values(touched).some(Boolean) && !isValid

  async function handlePay() {
    // Marca tudo como "tocado" no clique: se tinha campo vazio ou errado que
    // o usuário nunca chegou a tocar, os erros aparecem agora em vez do
    // botão simplesmente não fazer nada.
    setTouched({ number: true, name: true, expiry: true, cvv: true })
    if (!isValid) return

    setStatus('processing')
    setErrorMessage(null)
    try {
      const resultado = await pagarComCartao({
        method,
        number: cardNumber.replace(/\s/g, ''),
        name: cardName,
        expiration: expiry,
        cvv,
        amount: total,
      })
      if (resultado.status === 'APROVADO') {
        setStatus('approved')
      } else {
        setErrorMessage(resultado.message)
        setStatus('declined')
      }
    } catch {
      setErrorMessage('Não foi possível conectar ao servidor de pagamento.')
      setStatus('declined')
    }
  }

  function handleContinue() {
    navigate('/pedido/revisao', {
      state: { cartItems, address, payment: method, paymentStatus: 'approved', total },
    })
  }

  function handleRetry() {
    setStatus('form')
    setCvv('')
    setTouched((t) => ({ ...t, cvv: false }))
  }

  if (status === 'approved') {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] px-5 text-center gap-6">
        <div
          className="w-20 h-20 rounded-full flex items-center justify-center"
          style={{ background: 'linear-gradient(135deg,#16A34A,#15803D)', boxShadow: '0 8px 24px rgba(22,163,74,0.28)' }}
        >
          <svg className="w-9 h-9 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 6L9 17l-5-5" />
          </svg>
        </div>
        <div>
          <p className="text-2xl font-bold text-[#1A0A00]" style={{ fontFamily: 'Fraunces, serif' }}>
            Pagamento aprovado
          </p>
          <p className="text-sm text-[#6B5B4E] mt-2">
            {METHOD_LABEL[method]} · <strong>{formatMoney(total)}</strong>
          </p>
        </div>
        <button
          onClick={handleContinue}
          className="w-full max-w-sm py-4 rounded-2xl font-bold text-base text-white transition-all active:scale-[0.98]"
          style={{ fontFamily: 'Fraunces, serif', background: 'linear-gradient(135deg,#F97316,#EA580C)', boxShadow: '0 4px 16px rgba(249,115,22,0.3)' }}
        >
          Continuar
        </button>
      </div>
    )
  }

  if (status === 'declined') {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] px-5 text-center gap-6">
        <div
          className="w-20 h-20 rounded-full flex items-center justify-center"
          style={{ background: '#FEE2E2', border: '2px solid #FECACA' }}
        >
          <svg className="w-9 h-9 text-red-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </div>
        <div>
          <p className="text-2xl font-bold text-[#1A0A00]" style={{ fontFamily: 'Fraunces, serif' }}>
            Não foi possível realizar o pagamento
          </p>
          <p className="text-sm text-[#6B5B4E] mt-2">{errorMessage ?? 'Verifique os dados e tente novamente.'}</p>
        </div>
        <button
          onClick={handleRetry}
          className="w-full max-w-sm py-4 rounded-2xl font-bold text-base text-white transition-all active:scale-[0.98]"
          style={{ fontFamily: 'Fraunces, serif', background: '#1A0A00' }}
        >
          Tentar novamente
        </button>
      </div>
    )
  }

  if (status === 'processing') {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] px-5 text-center gap-5">
        <div className="w-16 h-16 rounded-full flex items-center justify-center" style={{ background: '#FFF1E0' }}>
          <svg className="w-8 h-8 animate-spin" viewBox="0 0 24 24" fill="none" stroke="#F97316" strokeWidth="2.5">
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" strokeLinecap="round" />
          </svg>
        </div>
        <div>
          <p className="text-xl font-bold text-[#1A0A00]" style={{ fontFamily: 'Fraunces, serif' }}>Processando pagamento...</p>
          <p className="text-sm text-[#6B5B4E] mt-1">{METHOD_LABEL[method]} · {formatMoney(total)}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="px-4 pt-5 pb-36 flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0" style={{ background: '#FFF1E0' }}>
          <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none">
            <rect x="2" y="5" width="20" height="14" rx="2" stroke="#F97316" strokeWidth="2"/>
            <path d="M2 10h20" stroke="#F97316" strokeWidth="2"/>
            <path d="M6 15h4" stroke="#F97316" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </div>
        <div>
          <p className="font-bold text-[#1A0A00]">{METHOD_LABEL[method]}</p>
          <p className="text-sm text-[#6B5B4E]">{formatMoney(total)}</p>
        </div>
      </div>

      <div className="rounded-2xl p-5 flex flex-col gap-4" style={{ border: '1.5px solid #E8D5C4', background: '#fff' }}>
        <Field
          label="Número do cartão"
          error={numeroErro}
          right={bandeira !== 'desconhecida' ? <BandeiraCartaoIcon bandeira={bandeira} /> : undefined}
        >
          <input
            type="text" inputMode="numeric" value={cardNumber}
            onChange={(e) => setCardNumber(formatarNumeroCartao(e.target.value))}
            onBlur={() => marcarTocado('number')}
            placeholder="0000 0000 0000 0000" maxLength={19}
            className="w-full px-4 py-3.5 rounded-xl text-[#1A0A00] font-bold text-lg tracking-widest placeholder:text-[#C4A882] placeholder:font-normal placeholder:tracking-normal focus:outline-none focus:ring-2 focus:ring-[#F97316]/40"
            style={{ border: campoBorda(numeroErro, touched.number && numeroOk), background: '#FFF8EF' }}
          />
        </Field>

        <Field label="Nome no cartão" error={nomeErro}>
          <input
            type="text" value={cardName} onChange={(e) => setCardName(e.target.value.toUpperCase())}
            onBlur={() => marcarTocado('name')}
            placeholder="NOME COMPLETO"
            className="w-full px-4 py-3.5 rounded-xl text-[#1A0A00] font-bold tracking-wide placeholder:text-[#C4A882] placeholder:font-normal placeholder:tracking-normal focus:outline-none focus:ring-2 focus:ring-[#F97316]/40"
            style={{ border: campoBorda(nomeErro, touched.name && nomeOk), background: '#FFF8EF' }}
          />
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Validade" error={validadeErro}>
            <input
              type="text" inputMode="numeric" value={expiry}
              onChange={(e) => setExpiry(formatarValidade(e.target.value))}
              onBlur={() => marcarTocado('expiry')}
              placeholder="MM/AA" maxLength={5}
              className="w-full px-4 py-3.5 rounded-xl text-[#1A0A00] font-bold text-lg placeholder:text-[#C4A882] placeholder:font-normal focus:outline-none focus:ring-2 focus:ring-[#F97316]/40"
              style={{ border: campoBorda(validadeErro, touched.expiry && validadeOk), background: '#FFF8EF' }}
            />
          </Field>
          <Field label="Código de segurança" error={cvvErro}>
            <input
              type="text" inputMode="numeric" value={cvv}
              onChange={(e) => setCvv(e.target.value.replace(/\D/g, '').slice(0, 4))}
              onBlur={() => marcarTocado('cvv')}
              placeholder="CVV" maxLength={4}
              className="w-full px-4 py-3.5 rounded-xl text-[#1A0A00] font-bold text-lg placeholder:text-[#C4A882] placeholder:font-normal focus:outline-none focus:ring-2 focus:ring-[#F97316]/40"
              style={{ border: campoBorda(cvvErro, touched.cvv && cvvOk), background: '#FFF8EF' }}
            />
          </Field>
        </div>

        {algumCampoInvalido && (
          <p className="text-xs font-semibold text-red-500 text-center">
            Confira os campos destacados acima antes de continuar.
          </p>
        )}

        <p className="text-xs text-[#B0967E] text-center pt-1">
          Seus dados de pagamento são processados com segurança.
        </p>
      </div>

      <div
        className="fixed bottom-0 left-0 right-0 z-30 px-4 py-4"
        style={{ background: 'rgba(255,248,239,0.97)', backdropFilter: 'blur(12px)', borderTop: '1.5px solid #E8D5C4' }}
      >
        <div className="max-w-lg mx-auto flex gap-3">
          <button
            onClick={() => navigate(-1)}
            className="px-5 py-3.5 rounded-2xl border font-semibold text-[#6B5B4E] text-sm active:scale-95 transition-all"
            style={{ borderColor: '#E8D5C4' }}
          >
            Voltar
          </button>
          {/*
            O botão fica sempre clicável (não usa `disabled`): clicar com o
            formulário inválido/incompleto dispara handlePay, que marca todos
            os campos como tocados e mostra os erros na hora, em vez de só
            ficar travado sem dizer o motivo (era essa a reclamação original).
            O estilo (cor/gradiente) continua indicando visualmente se está
            pronto pra enviar ou não.
          */}
          <button
            onClick={handlePay}
            className="flex-1 py-3.5 rounded-2xl font-bold text-base transition-all active:scale-[0.98]"
            style={{
              fontFamily: 'Fraunces, serif',
              background: isValid ? 'linear-gradient(135deg,#F97316,#EA580C)' : '#E8D5C4',
              color: isValid ? '#fff' : '#B0967E',
              boxShadow: isValid ? '0 4px 16px rgba(249,115,22,0.3)' : 'none',
            }}
          >
            Pagar pedido
          </button>
        </div>
      </div>
    </div>
  )
}

function campoBorda(erro: string | undefined, ok: boolean): string {
  if (erro) return '1.5px solid #FCA5A5'
  if (ok) return '1.5px solid #86EFAC'
  return '1.5px solid #E8D5C4'
}

function Field({
  label, error, right, children,
}: { label: string; error?: string; right?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <label className="block text-sm font-bold text-[#3D1A00]">{label}</label>
        {right}
      </div>
      {children}
      {error && <p className="text-xs font-semibold text-red-500 mt-1">{error}</p>}
    </div>
  )
}
