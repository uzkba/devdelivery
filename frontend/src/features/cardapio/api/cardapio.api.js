import { httpClient } from "@/shared/api/httpClient";
// Camada API: só faz a chamada HTTP crua, sem regra nenhuma.
export async function getCardapioHoje() {
    const { data } = await httpClient.get("/cardapio/hoje");
    return data;
}
export async function patchDisponibilidade(cardapioItemId, disponivel) {
    const { data } = await httpClient.patch(`/cardapio/itens/${cardapioItemId}/disponibilidade`, { disponivel });
    return data;
}
