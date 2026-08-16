import type { CardapioDoDia } from "../types/cardapio.types";

export const MOCK_CARDAPIO_HOJE: CardapioDoDia = {
  data: "2026-08-15",
  itens: [
    { id: 1, alimentoId: 1, nome: "Frango grelhado", categoria: "Carnes", disponivel: true, preco: 18.9 },
    { id: 2, alimentoId: 2, nome: "Arroz branco", categoria: "Arroz", disponivel: true, preco: 0 },
  ],
};
