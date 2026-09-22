import {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useState,
    type ReactNode,
} from "react";

export interface ItemCarrinho {
    id: string;
    name: string;
    catName: string;
    price: number;
    qty: number;
}

type ItemBase = Omit<ItemCarrinho, "qty">;

interface CarrinhoContextValue {
    itens: ItemCarrinho[];
    totalItens: number;
    subtotal: number;
    getQuantidade: (id: string) => number;
    definirQuantidade: (item: ItemBase, qty: number) => void;
    limparCarrinho: () => void;
}

const CarrinhoContext = createContext<CarrinhoContextValue | undefined>(
    undefined,
);
const STORAGE_KEY = "devdelivery:carrinho";

function carregarInicial(): Record<string, ItemCarrinho> {
    try {
        const raw = sessionStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : {};
    } catch {
        return {};
    }
}

export function CarrinhoProvider({ children }: { children: ReactNode }) {
    const [itensMap, setItensMap] =
        useState<Record<string, ItemCarrinho>>(carregarInicial);

    useEffect(() => {
        try {
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify(itensMap));
        } catch {
            // sessionStorage indisponível — segue só em memória
        }
    }, [itensMap]);

    const definirQuantidade = useCallback((item: ItemBase, qty: number) => {
        setItensMap((prev) => {
            if (qty <= 0) {
                const { [item.id]: _removido, ...resto } = prev;
                return resto;
            }
            return { ...prev, [item.id]: { ...item, qty } };
        });
    }, []);

    const limparCarrinho = useCallback(() => setItensMap({}), []);

    const itens = useMemo(() => Object.values(itensMap), [itensMap]);
    const totalItens = useMemo(
        () => itens.reduce((soma, i) => soma + i.qty, 0),
        [itens],
    );
    const subtotal = useMemo(
        () => itens.reduce((soma, i) => soma + i.qty * i.price, 0),
        [itens],
    );
    const getQuantidade = useCallback(
        (id: string) => itensMap[id]?.qty ?? 0,
        [itensMap],
    );

    const value = useMemo(
        () => ({
            itens,
            totalItens,
            subtotal,
            getQuantidade,
            definirQuantidade,
            limparCarrinho,
        }),
        [
            itens,
            totalItens,
            subtotal,
            getQuantidade,
            definirQuantidade,
            limparCarrinho,
        ],
    );

    return (
        <CarrinhoContext.Provider value={value}>
            {children}
        </CarrinhoContext.Provider>
    );
}

export function useCarrinho() {
    const ctx = useContext(CarrinhoContext);
    if (!ctx)
        throw new Error(
            "useCarrinho precisa estar dentro de um CarrinhoProvider",
        );
    return ctx;
}
