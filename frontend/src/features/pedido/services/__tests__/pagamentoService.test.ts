import { describe, it, expect, vi, beforeEach } from 'vitest'
import { gerarPix, pagarComCartao } from '../pagamentoService'
import { clientApi } from '@/shared/api/clientApi'

vi.mock('@/shared/api/clientApi', () => ({
  clientApi: {
    post: vi.fn(),
  },
}))

describe('pagamentoService', () => {
  beforeEach(() => {
    vi.mocked(clientApi.post).mockReset()
  })

  describe('gerarPix', () => {
    it('chama POST /pagamentos/pix com o valor e devolve os dados da resposta', async () => {
      const respostaMock = {
        copy_and_paste_code: '000201...6304ABCD',
        pix_key: 'chave@exemplo.com',
        account_holder: 'FULANO DE TAL',
        amount: 27,
      }
      vi.mocked(clientApi.post).mockResolvedValueOnce({ data: respostaMock })

      const resultado = await gerarPix(27)

      expect(clientApi.post).toHaveBeenCalledWith('/pagamentos/pix', { amount: 27 })
      expect(resultado).toEqual(respostaMock)
    })

    it('propaga o erro quando a chamada falha', async () => {
      vi.mocked(clientApi.post).mockRejectedValueOnce(new Error('falha de rede'))
      await expect(gerarPix(27)).rejects.toThrow('falha de rede')
    })
  })

  describe('pagarComCartao', () => {
    it('chama POST /pagamentos/cartao com os dados do cartão e devolve o resultado', async () => {
      const dados = {
        method: 'CARTAO_CREDITO' as const,
        number: '4532015112830366',
        name: 'FULANO DE TAL',
        expiration: '12/28',
        cvv: '123',
        amount: 27,
      }
      const respostaMock = {
        status: 'APROVADO' as const,
        transaction_id: 'abc-123',
        message: 'Pagamento aprovado.',
      }
      vi.mocked(clientApi.post).mockResolvedValueOnce({ data: respostaMock })

      const resultado = await pagarComCartao(dados)

      expect(clientApi.post).toHaveBeenCalledWith('/pagamentos/cartao', dados)
      expect(resultado).toEqual(respostaMock)
    })

    it('propaga o erro quando a chamada falha', async () => {
      vi.mocked(clientApi.post).mockRejectedValueOnce(new Error('falha de rede'))
      await expect(
        pagarComCartao({
          method: 'CARTAO_DEBITO',
          number: '4532015112830366',
          name: 'FULANO',
          expiration: '12/28',
          cvv: '123',
          amount: 27,
        }),
      ).rejects.toThrow('falha de rede')
    })
  })
})
