import { useCallback, useEffect, useState } from "react";
import { useRestauranteInfo } from "@/features/cliente/hooks/useRestauranteInfo";
import { obterCardapioDoDia } from "../services/cardapioService";
import type { CardapioDoDia } from "../types/cardapio";

interface UseCardapioDoDiaResult {
    cardapio: CardapioDoDia | null;
    carregando: boolean;
    erro: string | null;
    recarregar: () => void;
}

export function useCardapioDoDia(): UseCardapioDoDiaResult {
    const { restaurante, loading: carregandoRestaurante } =
        useRestauranteInfo();
    const [cardapio, setCardapio] = useState<CardapioDoDia | null>(null);
    const [carregando, setCarregando] = useState(true);
    const [erro, setErro] = useState<string | null>(null);
    const [tentativa, setTentativa] = useState(0);

    const recarregar = useCallback(() => setTentativa((t) => t + 1), []);

    useEffect(() => {
        if (carregandoRestaurante) return;

        if (!restaurante) {
            setCarregando(false);
            setErro("Não foi possível identificar o restaurante.");
            return;
        }

        let ativo = true;
        setCarregando(true);
        setErro(null);

        obterCardapioDoDia(restaurante.id)
            .then((resultado) => {
                if (ativo) setCardapio(resultado);
            })
            .catch(() => {
                if (ativo)
                    setErro(
                        "Não foi possível carregar o cardápio de hoje. Tente novamente.",
                    );
            })
            .finally(() => {
                if (ativo) setCarregando(false);
            });

        return () => {
            ativo = false;
        };
    }, [restaurante, carregandoRestaurante, tentativa]);

    return { cardapio, carregando, erro, recarregar };
}
