import type { ItemCardapio } from "../types/cardapio.types";

export function agruparPorCategoria(itens: ItemCardapio[]) {
  return itens.reduce<Record<string, ItemCardapio[]>>((grupos, item) => {
    grupos[item.categoria] = [...(grupos[item.categoria] ?? []), item];
    return grupos;
  }, {});
}
