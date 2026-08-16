import { httpClient } from "@/shared/api/httpClient";
import type { CardapioDoDia } from "../types/cardapio.types";

// Camada API: só faz a chamada HTTP crua, sem regra nenhuma.
export async function getCardapioHoje() {
  const { data } = await httpClient.get<CardapioDoDia>("/cardapio/hoje");
  return data;
}

export async function patchDisponibilidade(cardapioItemId: number, disponivel: boolean) {
  const { data } = await httpClient.patch(`/cardapio/itens/${cardapioItemId}/disponibilidade`, { disponivel });
  return data;
}
