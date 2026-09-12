import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import DinheiroPage from '../DinheiroPage'
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

function renderPage(total = 27) {
  return render(
    <MemoryRouter
      initialEntries={[{ pathname: '/pedido/pagamento/dinheiro', state: { cartItems, address, method: 'DINHEIRO', total } }]}
    >
      <Routes>
        <Route path="/pedido/pagamento/dinheiro" element={<DinheiroPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('DinheiroPage', () => {
  beforeEach(() => {
    mockNavigate.mockReset()
  })

  it('mostra o valor do pedido e as sugestões de troco baseadas no total', () => {
    renderPage(27)
    expect(screen.getAllByText(/R\$\s*27,00/).length).toBeGreaterThan(0)
    // sugestões dinâmicas pra 27: 50 e 100
    expect(screen.getByText(/R\$\s*50,00/)).toBeInTheDocument()
    expect(screen.getByText(/R\$\s*100,00/)).toBeInTheDocument()
  })

  it('valor exato: não mostra troco e navega com troco zero', async () => {
    const user = userEvent.setup()
    renderPage(27)

    await user.click(screen.getByText('Valor exato'))
    expect(screen.getByText('Sem troco')).toBeInTheDocument()

    await user.click(screen.getByText('Continuar'))
    expect(mockNavigate).toHaveBeenCalledWith('/pedido/revisao', {
      state: {
        cartItems, address, payment: 'DINHEIRO', paymentStatus: 'cash',
        total: 27, change: 0, amountPaid: 27,
      },
    })
  })

  it('valor rápido: calcula e mostra o troco correto', async () => {
    const user = userEvent.setup()
    renderPage(27)

    await user.click(screen.getByText(/R\$\s*50,00/))
    // "Troco" (label exato do banner de resultado) - o botão da cédula tem
    // "Troco: R$ 23,00" como texto único, então não bate com match exato
    expect(screen.getByText('Troco')).toBeInTheDocument()

    await user.click(screen.getByText('Continuar'))
    expect(mockNavigate).toHaveBeenCalledWith('/pedido/revisao', {
      state: {
        cartItems, address, payment: 'DINHEIRO', paymentStatus: 'cash',
        total: 27, change: 23, amountPaid: 50,
      },
    })
  })

  it('valor customizado insuficiente mostra aviso e não permite continuar', async () => {
    const user = userEvent.setup()
    renderPage(27)

    await user.click(screen.getByText('Digitar outro valor'))
    const input = screen.getByPlaceholderText('0,00')
    await user.type(input, '20')

    expect(screen.getByText(/não é suficiente/i)).toBeInTheDocument()
    expect(screen.getByText('Continuar')).toBeDisabled()
  })

  it('valor customizado suficiente calcula o troco', async () => {
    const user = userEvent.setup()
    renderPage(27)

    await user.click(screen.getByText('Digitar outro valor'))
    const input = screen.getByPlaceholderText('0,00')
    await user.type(input, '30')

    expect(screen.getByText(/R\$\s*3,00/)).toBeInTheDocument()
    expect(screen.getByText('Continuar')).not.toBeDisabled()
  })
})
