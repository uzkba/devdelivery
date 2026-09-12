import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Address, CartItem } from '../types/checkout'
import { suggestChangeAmounts } from '../utils/sugestoesValoresTroco'

function formatMoney(value: number): string {
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

export default function DinheiroPage() {
  const navigate = useNavigate()
  const { state } = useLocation()
  const { cartItems = [], address = null, method = 'DINHEIRO', total = 0 } =
    (state ?? {}) as { cartItems: CartItem[]; address: Address | null; method: string; total: number }

  const [mode, setMode] = useState<'exact' | 'quick' | 'custom' | null>(null)
  const [customInput, setCustomInput] = useState('')

  // Antes era uma lista fixa ([50, 100]) que não fazia sentido pra qualquer
  // total; agora as sugestões são calculadas em cima do valor cobrado.
  const quickValues = suggestChangeAmounts(total, 2)

  function getAmount(): number {
    if (mode === 'exact') return total
    if (mode === 'quick') return parseFloat(customInput) || 0
    if (mode === 'custom') return parseFloat(customInput.replace(',', '.')) || 0
    return 0
  }

  const amount = getAmount()
  const change = amount > 0 ? amount - total : 0
  const isValid = amount >= total
  const isInsufficient = amount > 0 && amount < total

  function selectQuick(value: number) {
    setMode('quick')
    setCustomInput(String(value))
  }

  function handleContinue() {
    if (!isValid) return
    navigate('/pedido/revisao', {
      state: {
        cartItems, address, payment: method, paymentStatus: 'cash',
        total, change: mode === 'exact' ? 0 : change, amountPaid: amount,
      },
    })
  }

  return (
    <div className="px-4 pt-5 pb-36 flex flex-col gap-4">
      {/* Valor do pedido */}
      <div
        className="rounded-2xl p-5 flex items-center justify-between"
        style={{ border: '1.5px solid #E8D5C4', background: '#fff', boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}
      >
        <div>
          <p className="text-xs font-bold text-[#B0967E] uppercase tracking-wide mb-1">Valor do pedido</p>
          <p className="text-3xl font-bold text-[#1A0A00]" style={{ fontFamily: 'Fraunces, serif' }}>
            {formatMoney(total)}
          </p>
        </div>
        <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: '#FFF1E0' }}>
          <svg viewBox="0 0 24 24" className="w-6 h-6" fill="none">
            <rect x="2" y="6" width="20" height="12" rx="2" stroke="#F97316" strokeWidth="2"/>
            <circle cx="12" cy="12" r="2.5" stroke="#F97316" strokeWidth="2"/>
            <path d="M6 12h.01M18 12h.01" stroke="#F97316" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </div>
      </div>

      {/* Quanto você vai pagar */}
      <div className="rounded-2xl p-5 flex flex-col gap-3" style={{ border: '1.5px solid #E8D5C4', background: '#fff' }}>
        <p className="font-bold text-[#1A0A00]">Quanto você vai pagar?</p>

        <div className="flex flex-col gap-2">
          <button
            onClick={() => { setMode('exact'); setCustomInput('') }}
            className="flex items-center justify-between px-4 py-3.5 rounded-xl transition-all active:scale-[0.97]"
            style={{
              border: mode === 'exact' ? '2px solid #F97316' : '1.5px solid #E8D5C4',
              background: mode === 'exact' ? '#FFF1E0' : '#FFF8EF',
            }}
          >
            <span className="font-bold text-[#1A0A00]">Valor exato</span>
            <span className="font-bold text-[#6B5B4E]">{formatMoney(total)}</span>
          </button>

          {quickValues.map((value) => (
            <button
              key={value}
              onClick={() => selectQuick(value)}
              className="flex items-center justify-between px-4 py-3.5 rounded-xl transition-all active:scale-[0.97]"
              style={{
                border: mode === 'quick' && customInput === String(value) ? '2px solid #F97316' : '1.5px solid #E8D5C4',
                background: mode === 'quick' && customInput === String(value) ? '#FFF1E0' : '#fff',
              }}
            >
              <span className="font-bold text-[#1A0A00]">{formatMoney(value)}</span>
              <span className="text-sm text-[#6B5B4E]">Troco: {formatMoney(value - total)}</span>
            </button>
          ))}

          <button
            onClick={() => { setMode('custom'); setCustomInput('') }}
            className="flex items-center px-4 py-3.5 rounded-xl text-left transition-all active:scale-[0.97]"
            style={{
              border: mode === 'custom' ? '2px solid #F97316' : '1.5px solid #E8D5C4',
              background: mode === 'custom' ? '#FFF1E0' : '#fff',
            }}
          >
            <span className="font-bold text-[#1A0A00]">Digitar outro valor</span>
          </button>
        </div>

        {mode === 'custom' && (
          <div className="relative mt-1">
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-base font-bold text-[#B0967E]">R$</span>
            <input
              type="number" inputMode="decimal" min={0} step="0.01"
              value={customInput} autoFocus
              onChange={(e) => setCustomInput(e.target.value)}
              placeholder="0,00"
              className="w-full pl-12 pr-4 py-3.5 rounded-xl text-[#1A0A00] text-xl font-bold focus:outline-none focus:ring-2 focus:ring-[#F97316]/40"
              style={{ border: '2px solid #E8D5C4', background: '#FFF8EF' }}
            />
          </div>
        )}

        {isValid && mode !== 'exact' && (
          <div className="flex justify-between items-center px-4 py-3 rounded-xl" style={{ background: '#DCFCE7', border: '1px solid #86EFAC' }}>
            <p className="text-sm font-semibold text-green-700">Troco</p>
            <p className="font-bold text-green-800 text-lg" style={{ fontFamily: 'Fraunces, serif' }}>{formatMoney(change)}</p>
          </div>
        )}
        {mode === 'exact' && (
          <div className="flex justify-between items-center px-4 py-3 rounded-xl" style={{ background: '#F0FDF4', border: '1px solid #86EFAC' }}>
            <p className="text-sm font-semibold text-green-700">Sem troco</p>
          </div>
        )}
        {isInsufficient && (
          <p className="text-xs font-semibold text-red-500">
            O valor informado não é suficiente para pagar o pedido.
          </p>
        )}
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
          <button
            onClick={handleContinue} disabled={!isValid && mode !== null}
            className="flex-1 py-3.5 rounded-2xl font-bold text-base transition-all active:scale-[0.98]"
            style={{
              fontFamily: 'Fraunces, serif',
              background: isValid ? 'linear-gradient(135deg,#F97316,#EA580C)' : '#E8D5C4',
              color: isValid ? '#fff' : '#B0967E',
              boxShadow: isValid ? '0 4px 16px rgba(249,115,22,0.3)' : 'none',
              cursor: !isValid ? 'not-allowed' : 'pointer',
            }}
          >
            Continuar
          </button>
        </div>
      </div>
    </div>
  )
}
