// CartItem e Address ainda não existem em nenhum arquivo real do projeto —
// o protótipo original importava de './CardapioPage' e '../../contexts/ClientContext',
// mas nenhum dos dois existe. Centralizei os dois tipos aqui pra não duplicar
// em cada página de pagamento.
//
// Address foi montado a partir do schema real de endereço do backend
// (CustomerAddress / EnderecoOut) já usado em features/cliente.
// CartItem é uma suposição minha (id/nome/preco/quantidade) — como ainda não
// existe uma página de cardápio/carrinho real pra confirmar o formato, ajuste
// os nomes dos campos aqui assim que a feature de carrinho existir; é o único
// lugar que precisa mudar.

export interface Address {
  id: string
  street: string
  number: string
  neighborhood: string
  complement?: string | null
  reference_point?: string | null
  primary_address: boolean
  latitude?: number | null
  longitude?: number | null
}

export interface CartItem {
  id: string
  nome: string
  preco: number
  quantidade: number
}
