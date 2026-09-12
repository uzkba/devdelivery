import { buscarCardapioDoDia } from "../api/cardapioApi";
import { mapCardapioDoDia } from "../mappers/cardapioMapper";
import type { CardapioDoDia } from "../types/cardapio";

export async function obterCardapioDoDia(
    restauranteId: string,
): Promise<CardapioDoDia> {
    const bruto = await buscarCardapioDoDia(restauranteId);
    return mapCardapioDoDia(bruto);
}
