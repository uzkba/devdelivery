import { useEffect, useState } from "react";
import { cardapioService } from "../services/cardapio.service";
// Camada Viewmodel: estado e efeitos da tela, consumido pelo componente/página.
export function useCardapioHoje() {
    const [cardapio, setCardapio] = useState(null);
    const [carregando, setCarregando] = useState(true);
    const [erro, setErro] = useState(null);
    useEffect(() => {
        cardapioService
            .buscarCardapioDeHoje()
            .then(setCardapio)
            .catch(() => setErro("Não foi possível carregar o cardápio de hoje."))
            .finally(() => setCarregando(false));
    }, []);
    return { cardapio, carregando, erro };
}
