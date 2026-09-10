export interface ViaCepResult {
    logradouro: string;
    bairro: string;
    localidade: string;
    uf: string;
    erro?: boolean;
}

export async function buscarEnderecoPorCep(
    cep: string,
): Promise<ViaCepResult | null> {
    const digits = cep.replace(/\D/g, "");
    if (digits.length !== 8) return null;

    try {
        const res = await fetch(`https://viacep.com.br/ws/${digits}/json/`);
        if (!res.ok) return null;
        const data = await res.json();
        if (data.erro) return null;
        return data as ViaCepResult;
    } catch {
        return null;
    }
}

export function formatarCep(value: string): string {
    const digits = value.replace(/\D/g, "").slice(0, 8);
    return digits.length > 5
        ? `${digits.slice(0, 5)}-${digits.slice(5)}`
        : digits;
}