import { useMemo, useState } from "react";
import type { CardapioDoDia } from "../types/cardapio";
import type { CartItem } from "@/features/pedido/types/checkout";

const TAXA_ENTREGA = 5;

export function useCardapioCarrinho(cardapio: CardapioDoDia | null) {
    const [quantidades, setQuantidades] = useState<Record<string, number>>({});

    function definirQuantidade(itemId: string, quantidade: number) {
        setQuantidades((atual) => {
            if (quantidade <= 0) {
                const novo = { ...atual };
                delete novo[itemId];
                return novo;
            }
            return { ...atual, [itemId]: quantidade };
        });
    }

    const itensCarrinho: CartItem[] = useMemo(() => {
        if (!cardapio) return [];
        return cardapio.categorias.flatMap((categoria) =>
            categoria.itens
                .filter((item) => (quantidades[item.itemId] ?? 0) > 0)
                .map((item) => ({
                    id: item.itemId,
                    nome: item.nome,
                    preco: item.preco,
                    quantidade: quantidades[item.itemId],
                })),
        );
    }, [cardapio, quantidades]);

    const totalItens = itensCarrinho.reduce(
        (soma, item) => soma + item.quantidade,
        0,
    );
    const subtotal = itensCarrinho.reduce(
        (soma, item) => soma + item.preco * item.quantidade,
        0,
    );
    const total = totalItens > 0 ? subtotal + TAXA_ENTREGA : 0;

    return {
        quantidades,
        definirQuantidade,
        itensCarrinho,
        totalItens,
        subtotal,
        total,
    };
}
