import { useEffect, useState } from "react";
import { cardapioService } from "../services/cardapio.service";
import type { CardapioDoDia } from "../types/cardapio.types";

// Camada Viewmodel: estado e efeitos da tela, consumido pelo componente/página.
export function useCardapioHoje() {
  const [cardapio, setCardapio] = useState<CardapioDoDia | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    cardapioService
      .buscarCardapioDeHoje()
      .then(setCardapio)
      .catch(() => setErro("Não foi possível carregar o cardápio de hoje."))
      .finally(() => setCarregando(false));
  }, []);

  return { cardapio, carregando, erro };
}
