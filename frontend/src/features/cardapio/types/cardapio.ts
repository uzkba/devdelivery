export interface OpcaoComplemento {
  id: string
  nome: string
  precoAdicional: number
  disponivel: boolean
}

export interface GrupoComplemento {
  id: string
  nome: string
  minChoices: number
  maxChoices: number
  opcoes: OpcaoComplemento[]
}

export interface ItemCardapio {
  itemId: string
  alimentoId: string
  nome: string
  descricao: string | null
  preco: number
  gruposComplemento: GrupoComplemento[]
}

export interface CategoriaCardapio {
  categoriaId: string
  categoriaNome: string
  itens: ItemCardapio[]
}

export interface CardapioDoDia {
  data: string
  categorias: CategoriaCardapio[]
}