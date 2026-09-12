import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import CartaoPage from '../CartaoPage'
import type { CartItem, Address } from '../../types/checkout'

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

vi.mock('../../services/pagamentoService', () => ({
  pagarComCartao: vi.fn(),
}))

// stub simples pra não depender da renderização real da lib de ícones
vi.mock('react-svg-credit-card-payment-icons', () => ({
  PaymentIcon: ({ type }: { type: string }) => <div data-testid="bandeira-icone">{type}</div>,
}))

import { pagarComCartao } from '../../services/pagamentoService'

const cartItems: CartItem[] = [{ id: '1', nome: 'Marmita tradicional', preco: 22, quantidade: 1 }]
const address: Address = {
  id: 'end-1',
  street: 'Rua das Flores',
  number: '100',
  neighborhood: 'Centro',
  primary_address: true,
}

function renderPage(method: 'CARTAO_CREDITO' | 'CARTAO_DEBITO' = 'CARTAO_CREDITO', total = 27) {
  return render(
    <MemoryRouter
      initialEntries={[{ pathname: '/pedido/pagamento/cartao', state: { cartItems, address, method, total } }]}
    >
      <Routes>
        <Route path="/pedido/pagamento/cartao" element={<CartaoPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

async function preencherFormularioValido(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByPlaceholderText('0000 0000 0000 0000'), '4532015112830366')
  await user.type(screen.getByPlaceholderText('NOME COMPLETO'), 'FULANO DE TAL')
  await user.type(screen.getByPlaceholderText('MM/AA'), '1228')
  await user.type(screen.getByPlaceholderText('CVV'), '123')
}

describe('CartaoPage', () => {
  beforeEach(() => {
    mockNavigate.mockReset()
    vi.mocked(pagarComCartao).mockReset()
  })

  it('não chama a API com formulário inválido, mas mostra os erros ao tentar pagar', async () => {
    const user = userEvent.setup()
    renderPage()

    // ainda não tocou em nada: nenhum erro visível de cara
    expect(screen.queryByText('Número de cartão inválido')).not.toBeInTheDocument()

    // número de cartão inválido (não passa no Luhn)
    await user.type(screen.getByPlaceholderText('0000 0000 0000 0000'), '4532015112830367')
    await user.type(screen.getByPlaceholderText('NOME COMPLETO'), 'FU')
    await user.type(screen.getByPlaceholderText('MM/AA'), '1228')
    // CVV fica em branco de propósito

    await user.click(screen.getByText('Pagar pedido'))

    expect(pagarComCartao).not.toHaveBeenCalled()
    expect(screen.getByText('Número de cartão inválido')).toBeInTheDocument()
    expect(screen.getByText('Digite o nome completo como está no cartão')).toBeInTheDocument()
    expect(screen.getByText('Confira os campos destacados acima antes de continuar.')).toBeInTheDocument()
  })

  it('mostra erro de campo individual ao sair do campo (blur), mesmo antes de clicar em pagar', async () => {
    const user = userEvent.setup()
    renderPage()

    const campoValidade = screen.getByPlaceholderText('MM/AA')
    await user.type(campoValidade, '01/20')
    await user.tab() // dispara blur

    expect(screen.getByText('Cartão vencido ou data inválida')).toBeInTheDocument()
  })

  it('identifica e mostra o ícone da bandeira do cartão enquanto o usuário digita', async () => {
    const user = userEvent.setup()
    renderPage()

    expect(screen.queryByTestId('bandeira-icone')).not.toBeInTheDocument()

    await user.type(screen.getByPlaceholderText('0000 0000 0000 0000'), '4532015112830366')
    expect(screen.getByTestId('bandeira-icone')).toHaveTextContent('visa')
  })

  it('envia os dados corretos pra API e mostra a tela de aprovado', async () => {
    vi.mocked(pagarComCartao).mockResolvedValueOnce({
      status: 'APROVADO',
      transaction_id: 'tx-1',
      message: 'Pagamento aprovado.',
    })
    const user = userEvent.setup()
    renderPage('CARTAO_CREDITO', 27)

    await preencherFormularioValido(user)
    await user.click(screen.getByText('Pagar pedido'))

    expect(pagarComCartao).toHaveBeenCalledWith({
      method: 'CARTAO_CREDITO',
      number: '4532015112830366',
      name: 'FULANO DE TAL',
      expiration: '12/28',
      cvv: '123',
      amount: 27,
    })

    await waitFor(() => expect(screen.getByText('Pagamento aprovado')).toBeInTheDocument())

    await user.click(screen.getByText('Continuar'))
    expect(mockNavigate).toHaveBeenCalledWith('/pedido/revisao', {
      state: { cartItems, address, payment: 'CARTAO_CREDITO', paymentStatus: 'approved', total: 27 },
    })
  })

  it('mostra a tela de recusado com a mensagem do backend quando o pagamento é recusado', async () => {
    vi.mocked(pagarComCartao).mockResolvedValueOnce({
      status: 'RECUSADO',
      message: 'Saldo insuficiente.',
    })
    const user = userEvent.setup()
    renderPage()

    await preencherFormularioValido(user)
    await user.click(screen.getByText('Pagar pedido'))

    await waitFor(() => expect(screen.getByText('Não foi possível realizar o pagamento')).toBeInTheDocument())
    expect(screen.getByText('Saldo insuficiente.')).toBeInTheDocument()

    await user.click(screen.getByText('Tentar novamente'))
    expect(screen.getByText('Pagar pedido')).toBeInTheDocument()
  })

  it('mostra mensagem genérica de erro quando a chamada à API falha', async () => {
    vi.mocked(pagarComCartao).mockRejectedValueOnce(new Error('network error'))
    const user = userEvent.setup()
    renderPage()

    await preencherFormularioValido(user)
    await user.click(screen.getByText('Pagar pedido'))

    await waitFor(() =>
      expect(screen.getByText('Não foi possível conectar ao servidor de pagamento.')).toBeInTheDocument(),
    )
  })
})
