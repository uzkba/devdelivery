import { clientApi } from "@/shared/api/clientApi"


export type MetodoCartao = 'CARTAO_CREDITO' | 'CARTAO_DEBITO'

export interface PixGerarResponse {
  copy_and_paste_code: string
  pix_key: string
  account_holder: string
  amount: number
}

export interface CartaoPagamentoRequest {
  method: MetodoCartao
  number: string
  name: string
  expiration: string
  cvv: string
  amount: number
}

export interface PagamentoResultadoResponse {
  status: 'APROVADO' | 'RECUSADO'
  transaction_id?: string
  message: string
}

export async function gerarPix(amount: number): Promise<PixGerarResponse> {
  const { data } = await clientApi.post<PixGerarResponse>('/pagamentos/pix', { amount })
  return data
}

export async function pagarComCartao(dados: CartaoPagamentoRequest): Promise<PagamentoResultadoResponse> {
  const { data } = await clientApi.post<PagamentoResultadoResponse>('/pagamentos/cartao', dados)
  return data
}
