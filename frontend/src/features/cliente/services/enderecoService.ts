import { clientApi } from "@/shared/api/clientApi";

export interface Endereco {
    id: string;
    client_id: string;
    created_at: string;
    street: string;
    number: string;
    neighborhood: string;
    complement?: string | null;
    reference_point?: string | null;
    primary_address: boolean;
    latitude?: number | null;
    longitude?: number | null;
}

export interface EnderecoInput {
    street: string;
    number: string;
    neighborhood: string;
    complement?: string;
    reference_point?: string;
    latitude?: number | null;
    longitude?: number | null;
}

const BASE_PATH = "/clientes/me/enderecos/";

export async function listarEnderecos(): Promise<Endereco[]> {
    const { data } = await clientApi.get<Endereco[]>(BASE_PATH);
    return data;
}

export async function criarEndereco(payload: EnderecoInput): Promise<Endereco> {
    const { data } = await clientApi.post<Endereco>(BASE_PATH, payload);
    return data;
}

export async function atualizarEndereco(
    id: string,
    payload: Partial<EnderecoInput>,
): Promise<Endereco> {
    const { data } = await clientApi.put<Endereco>(
        `${BASE_PATH}${id}`,
        payload,
    );
    return data;
}

export async function removerEndereco(id: string): Promise<void> {
    await clientApi.delete(`${BASE_PATH}${id}`);
}

export async function definirEnderecoPadrao(id: string): Promise<Endereco> {
    const { data } = await clientApi.patch<Endereco>(
        `${BASE_PATH}${id}/padrao`,
    );
    return data;
}
