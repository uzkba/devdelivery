export function agruparPorCategoria(itens) {
    return itens.reduce((grupos, item) => {
        grupos[item.categoria] = [...(grupos[item.categoria] ?? []), item];
        return grupos;
    }, {});
}
