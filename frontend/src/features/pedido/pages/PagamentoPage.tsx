import { useNavigate, useLocation } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import { Address, CartItem } from '../types/checkout';
import { PixIcon } from '../components/PixICon';

type PaymentMethod = 'PIX' | 'CARTAO_CREDITO' | 'CARTAO_DEBITO' | 'DINHEIRO'

const OPTIONS: { id: PaymentMethod; label: string; sub: string; route: string }[] = [
  { id: 'PIX', label: 'PIX', sub: 'Pagamento instantâneo', route: '/pedido/pagamento/pix' },
  { id: 'CARTAO_CREDITO', label: 'Cartão de crédito', sub: 'Digite os dados do seu cartão', route: '/pedido/pagamento/cartao' },
  { id: 'CARTAO_DEBITO', label: 'Cartão de débito', sub: 'Digite os dados do seu cartão', route: '/pedido/pagamento/cartao' },
  { id: 'DINHEIRO', label: 'Dinheiro', sub: 'Informe quanto você vai pagar', route: '/pedido/pagamento/dinheiro' },
]

// TODO: taxa de entrega fixa por enquanto (mesma coisa do protótipo original);
// mover para vir do backend quando isso virar configurável.
const DELIVERY_FEE = 5

function formatMoney(value: number): string {
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

// TODO: ajustar os nomes dos campos (preco/quantidade) assim que eu souber
// o formato real de CartItem em CardapioPage — usei "any" aqui de propósito
// pra não travar a task nisso.
function calculateSubtotal(cartItems: CartItem[]): number {
  return cartItems.reduce((sum, item: any) => sum + (item.preco ?? 0) * (item.quantidade ?? 1), 0)
}

export default function PagamentoPage() {
  const navigate = useNavigate()
  const { state } = useLocation()
  const { cartItems = [], address = null } =
    (state ?? {}) as { cartItems: CartItem[]; address: Address | null }

  const total = calculateSubtotal(cartItems) + DELIVERY_FEE

  function handleSelect(opt: typeof OPTIONS[0]) {
    navigate(opt.route, { state: { cartItems, address, method: opt.id, total } })
  }

  return (
    <div className="px-4 pt-6 pb-16 flex flex-col gap-5">
      <div>
        <h2 className="text-xl font-bold text-[#1A0A00]" style={{ fontFamily: 'Fraunces, serif' }}>
          Como você quer pagar?
        </h2>
        <p className="text-sm text-[#6B5B4E] mt-1">
          Pedido no valor de <strong className="text-[#1A0A00]">{formatMoney(total)}</strong>
        </p>
      </div>

      <div className="flex flex-col gap-3">
        {OPTIONS.map((opt) => (
          <button
            key={opt.id}
            onClick={() => handleSelect(opt)}
            className="flex items-center gap-4 px-4 py-4 rounded-2xl text-left transition-all active:scale-[0.98]"
            style={{
              border: '1.5px solid #E8D5C4',
              background: '#fff',
              boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
            }}
          >
            <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ background: '#FFF1E0' }}>
              <PaymentIcon method={opt.id} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-bold text-[#1A0A00] text-base">{opt.label}</p>
              <p className="text-sm text-[#6B5B4E] mt-0.5">{opt.sub}</p>
            </div>
            <ChevronRight size={18} className="text-[#B0967E] shrink-0" />
          </button>
        ))}
      </div>
    </div>
  )
}

function PaymentIcon({ method }: { method: PaymentMethod }) {
  if (method === 'PIX') return (
    <PixIcon className="w-5 h-5" />
  )
  if (method === 'DINHEIRO') return (
    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none">
      <rect x="2" y="6" width="20" height="12" rx="2" stroke="#F97316" strokeWidth="2"/>
      <circle cx="12" cy="12" r="2.5" stroke="#F97316" strokeWidth="2"/>
      <path d="M6 12h.01M18 12h.01" stroke="#F97316" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  )
  return (
    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none">
      <rect x="2" y="5" width="20" height="14" rx="2" stroke="#F97316" strokeWidth="2"/>
      <path d="M2 10h20" stroke="#F97316" strokeWidth="2"/>
      <path d="M6 15h4" stroke="#F97316" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  )
}
