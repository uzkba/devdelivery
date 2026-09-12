import type {
    CardapioDoDia,
    CategoriaCardapio,
    ItemCardapio,
    GrupoComplemento,
    OpcaoComplemento,
} from "../types/cardapio";

interface OpcaoComplementoApi {
    id: string;
    nome: string;
    preco_adicional: string;
    disponivel: boolean;
}

interface GrupoComplementoApi {
    id: string;
    nome: string;
    min_choices: number;
    max_choices: number;
    opcoes: OpcaoComplementoApi[];
}

interface ItemCardapioApi {
    item_id: string;
    alimento_id: string;
    nome: string;
    descricao: string | null;
    preco: string;
    grupos_complemento: GrupoComplementoApi[];
}

interface CategoriaCardapioApi {
    categoria_id: string;
    categoria_nome: string;
    itens: ItemCardapioApi[];
}

export interface CardapioDoDiaApi {
    data: string;
    categorias: CategoriaCardapioApi[];
}

function mapOpcao(opcao: OpcaoComplementoApi): OpcaoComplemento {
    return {
        id: opcao.id,
        nome: opcao.nome,
        precoAdicional: Number(opcao.preco_adicional),
        disponivel: opcao.disponivel,
    };
}

function mapGrupo(grupo: GrupoComplementoApi): GrupoComplemento {
    return {
        id: grupo.id,
        nome: grupo.nome,
        minChoices: grupo.min_choices,
        maxChoices: grupo.max_choices,
        opcoes: grupo.opcoes.map(mapOpcao),
    };
}

function mapItem(item: ItemCardapioApi): ItemCardapio {
    return {
        itemId: item.item_id,
        alimentoId: item.alimento_id,
        nome: item.nome,
        descricao: item.descricao,
        preco: Number(item.preco),
        gruposComplemento: item.grupos_complemento.map(mapGrupo),
    };
}

function mapCategoria(categoria: CategoriaCardapioApi): CategoriaCardapio {
    return {
        categoriaId: categoria.categoria_id,
        categoriaNome: categoria.categoria_nome,
        itens: categoria.itens.map(mapItem),
    };
}

export function mapCardapioDoDia(api: CardapioDoDiaApi): CardapioDoDia {
    return {
        data: api.data,
        categorias: api.categorias.map(mapCategoria),
    };
}
