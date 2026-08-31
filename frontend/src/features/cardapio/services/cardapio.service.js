import { getCardapioHoje, patchDisponibilidade } from "../api/cardapio.api";
// Camada Service: ponto único que a UI chama; pode combinar API + regras simples de UI
// (ex.: ordenar por categoria) sem misturar com o viewmodel.
export const cardapioService = {
    buscarCardapioDeHoje: getCardapioHoje,
    alterarDisponibilidade: patchDisponibilidade,
};
