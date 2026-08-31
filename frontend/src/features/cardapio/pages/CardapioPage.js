import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useCardapioHoje } from "../viewmodels/useCardapioHoje";
import { ItemCardapioCard } from "../components/ItemCardapioCard";
// Camada Page: monta a tela usando o viewmodel + componentes — sem chamar API direto.
export function CardapioPage() {
    const { cardapio, carregando, erro } = useCardapioHoje();
    if (carregando)
        return _jsx("p", { className: "p-4", children: "Carregando card\u00E1pio..." });
    if (erro)
        return _jsx("p", { className: "p-4 text-red-600", children: erro });
    if (!cardapio || cardapio.itens.length === 0) {
        return _jsx("p", { className: "p-4", children: "Nenhum item dispon\u00EDvel no momento." });
    }
    return (_jsxs("main", { className: "mx-auto max-w-xl space-y-3 p-4", children: [_jsx("h1", { className: "text-xl font-semibold", children: "Card\u00E1pio de hoje" }), cardapio.itens.map((item) => (_jsx(ItemCardapioCard, { item: item, onAdicionar: () => { } }, item.id)))] }));
}
