import { clientApi } from "@/shared/api/clientApi";
import type { CardapioDoDiaApi } from "../mappers/cardapioMapper"

export async function buscarCardapioDoDia(
    restauranteId: string,
): Promise<CardapioDoDiaApi> {
    const { data } = await clientApi.get<CardapioDoDiaApi>(
        `/restaurantes/${restauranteId}/cardapio-do-dia`,
    );
    return data;
}
