import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { QRCodeSVG } from 'qrcode.react'
import { gerarPix } from '../services/pagamentoService'
import { Address, CartItem } from '../types/checkout'


function formatMoney(value: number): string {
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

type PixStatus = 'loading' | 'waiting' | 'confirmed' | 'error'

export default function PixPage() {
  const navigate = useNavigate()
  const { state } = useLocation()
  const { cartItems = [], address = null, method = 'PIX', total = 0 } =
    (state ?? {}) as { cartItems: CartItem[]; address: Address | null; method: string; total: number }

  const [copied, setCopied] = useState(false)
  const [status, setStatus] = useState<PixStatus>('loading')
  const [simulating, setSimulating] = useState(false)
  const [pixCode, setPixCode] = useState('')

  useEffect(() => {
    let cancelled = false
    gerarPix(total)
      .then((res) => {
        if (cancelled) return
        setPixCode(res.copy_and_paste_code)
        setStatus('waiting')
      })
      .catch(() => {
        if (!cancelled) setStatus('error')
      })
    return () => { cancelled = true }
  }, [total])

  function handleCopy() {
    navigator.clipboard?.writeText(pixCode).catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 2500)
  }

  // Ainda não há um webhook do banco confirmando o Pix automaticamente — o
  // código gerado é real (BR Code/EMV válido), mas a confirmação em si
  // continua simulada até existir essa integração.
  function simulatePayment() {
    setSimulating(true)
    setTimeout(() => { setStatus('confirmed'); setSimulating(false) }, 1800)
  }

  function handleContinue() {
    navigate('/pedido/revisao', {
      state: { cartItems, address, payment: method, paymentStatus: 'confirmed', total },
    })
  }

  if (status === 'error') {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] px-5 text-center gap-4">
        <p className="text-lg font-bold text-[#1A0A00]">Não foi possível gerar o código Pix.</p>
        <p className="text-sm text-[#6B5B4E]">Verifique sua conexão e tente novamente.</p>
        <button
          onClick={() => navigate(-1)}
          className="px-6 py-3 rounded-xl font-bold text-white"
          style={{ background: '#1A0A00' }}
        >
          Voltar
        </button>
      </div>
    )
  }

  if (status === 'loading') {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] px-5 text-center gap-4">
        <svg className="w-8 h-8 animate-spin" viewBox="0 0 24 24" fill="none" stroke="#F97316" strokeWidth="2.5">
          <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" strokeLinecap="round" />
        </svg>
        <p className="text-sm text-[#6B5B4E]">Gerando código Pix...</p>
      </div>
    )
  }

  if (status === 'confirmed') {
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
            Pagamento confirmado
          </p>
          <p className="text-sm text-[#6B5B4E] mt-2">
            PIX de <strong>{formatMoney(total)}</strong> recebido com sucesso.
          </p>
        </div>
        <button
          onClick={handleContinue}
          className="w-full max-w-sm py-4 rounded-2xl font-bold text-base text-white transition-all active:scale-[0.98]"
          style={{
            fontFamily: 'Fraunces, serif',
            background: 'linear-gradient(135deg,#F97316,#EA580C)',
            boxShadow: '0 4px 16px rgba(249,115,22,0.3)',
          }}
        >
          Continuar
        </button>
      </div>
    )
  }

  return (
    <div className="px-4 pt-5 pb-10 flex flex-col gap-5">
      <div
        className="flex items-center gap-3 px-4 py-3 rounded-2xl"
        style={{ background: '#FFFBEB', border: '1.5px solid #FDE68A' }}
      >
        <span className="w-2.5 h-2.5 rounded-full bg-amber-400 shrink-0" style={{ animation: 'pulse 1.4s infinite' }} />
        <p className="text-sm font-bold text-amber-800">Aguardando pagamento</p>
        <p className="text-sm text-amber-700 ml-auto font-bold">{formatMoney(total)}</p>
      </div>

      <div
        className="rounded-2xl p-6 flex flex-col items-center gap-4"
        style={{ border: '1.5px solid #E8D5C4', background: '#fff', boxShadow: '0 2px 10px rgba(0,0,0,0.05)' }}
      >
        <p className="text-xs font-bold text-[#B0967E] uppercase tracking-wide">Escaneie o QR Code para pagar</p>
        <div className="inline-block p-3 rounded-xl bg-white" style={{ boxShadow: '0 0 0 1px #E8D5C4' }}>
          <QRCodeSVG value={pixCode} size={189} />
        </div>
        <p className="text-xs text-[#B0967E] text-center">
          Abra o aplicativo do seu banco e escaneie o código acima.
        </p>
      </div>

      <div className="rounded-2xl p-5 flex flex-col gap-3" style={{ border: '1.5px solid #E8D5C4', background: '#fff' }}>
        <p className="text-xs font-bold text-[#B0967E] uppercase tracking-wide">Ou copie o código abaixo</p>
        <div
          className="px-3 py-2.5 rounded-xl text-xs font-mono text-[#6B5B4E] break-all select-all"
          style={{ background: '#FFF8EF', border: '1px solid #E8D5C4' }}
        >
          {pixCode}
        </div>
        <button
          onClick={handleCopy}
          className="w-full py-3 rounded-xl font-bold text-sm transition-all active:scale-[0.97]"
          style={{
            background: copied ? '#DCFCE7' : '#FFF1E0',
            color: copied ? '#166534' : '#EA6C0A',
            border: `1.5px solid ${copied ? '#86EFAC' : '#F5CFA0'}`,
          }}
        >
          {copied ? 'Código copiado' : 'Copiar código'}
        </button>
      </div>

      <div className="rounded-2xl p-4 text-center" style={{ background: '#F5EDE3', border: '1px solid #E8D5C4' }}>
        <p className="text-xs text-[#6B5B4E] mb-3">Para demonstração, simule o recebimento do pagamento:</p>
        <button
          onClick={simulatePayment} disabled={simulating}
          className="px-6 py-2.5 rounded-xl font-bold text-sm transition-all active:scale-[0.97]"
          style={{
            background: simulating ? '#E8D5C4' : '#1A0A00',
            color: simulating ? '#B0967E' : '#fff',
          }}
        >
          {simulating ? 'Aguardando...' : 'Simular pagamento recebido'}
        </button>
      </div>

      <style>{`@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}`}</style>
    </div>
  )
}
