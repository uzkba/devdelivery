import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import PagamentoPage from '../PagamentoPage'
import { Address, CartItem } from '../../types/checkout'


const mockNavigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

const cartItems: CartItem[] = [{ id: '1', nome: 'Marmita tradicional', preco: 22, quantidade: 1 }]
const address: Address = {
  id: 'end-1',
  street: 'Rua das Flores',
  number: '100',
  neighborhood: 'Centro',
  primary_address: true,
}

function renderPage(state: unknown = { cartItems, address }) {
  return render(
    <MemoryRouter initialEntries={[{ pathname: '/pedido/pagamento', state }]}>
      <Routes>
        <Route path="/pedido/pagamento" element={<PagamentoPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('PagamentoPage', () => {
  beforeEach(() => {
    mockNavigate.mockReset()
  })

  it('mostra o total do pedido (subtotal do carrinho + taxa de entrega)', () => {
    renderPage()
    // 22 (item) + 5 (entrega) = 27
    // regex em vez de string exata: toLocaleString('pt-BR') pode usar
    // espaço não separável (U+00A0) entre "R$" e o valor, dependendo do ambiente
    expect(screen.getByText(/R\$\s*27,00/)).toBeInTheDocument()
  })

  it('lida com carrinho vazio sem quebrar (mostra só a taxa de entrega)', () => {
    renderPage({ cartItems: [], address: null })
    expect(screen.getByText(/R\$\s*5,00/)).toBeInTheDocument()
  })

  it('renderiza as quatro opções de pagamento', () => {
    renderPage()
    expect(screen.getByText('PIX')).toBeInTheDocument()
    expect(screen.getByText('Cartão de crédito')).toBeInTheDocument()
    expect(screen.getByText('Cartão de débito')).toBeInTheDocument()
    expect(screen.getByText('Dinheiro')).toBeInTheDocument()
  })

  it('navega para a rota do Pix com o método e o total no state', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByText('PIX'))

    expect(mockNavigate).toHaveBeenCalledWith('/pedido/pagamento/pix', {
      state: { cartItems, address, method: 'PIX', total: 27 },
    })
  })

  it('navega para a rota do cartão com CARTAO_CREDITO ao clicar em cartão de crédito', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByText('Cartão de crédito'))

    expect(mockNavigate).toHaveBeenCalledWith('/pedido/pagamento/cartao', {
      state: { cartItems, address, method: 'CARTAO_CREDITO', total: 27 },
    })
  })

  it('navega para a rota de dinheiro ao clicar em dinheiro', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByText('Dinheiro'))

    expect(mockNavigate).toHaveBeenCalledWith('/pedido/pagamento/dinheiro', {
      state: { cartItems, address, method: 'DINHEIRO', total: 27 },
    })
  })
})
