import { useCallback, useEffect, useState } from "react";
import * as enderecoService from "../services/enderecoService";
import type { Endereco, EnderecoInput } from "../services/enderecoService";

export function useEnderecos() {
    const [enderecos, setEnderecos] = useState<Endereco[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const carregar = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await enderecoService.listarEnderecos();
            setEnderecos(data);
        } catch {
            setError("Não foi possível carregar seus endereços.");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        carregar();
    }, [carregar]);

    const adicionar = useCallback(async (payload: EnderecoInput) => {
        const novo = await enderecoService.criarEndereco(payload);
        setEnderecos((prev) => [...prev, novo]);
        return novo;
    }, []);

    const atualizar = useCallback(
        async (id: string, payload: Partial<EnderecoInput>) => {
            const atualizado = await enderecoService.atualizarEndereco(id, payload);
            setEnderecos((prev) => prev.map((e) => (e.id === id ? atualizado : e)));
            return atualizado;
        },
        [],
    );

    const remover = useCallback(async (id: string) => {
        await enderecoService.removerEndereco(id);
        setEnderecos((prev) => prev.filter((e) => e.id !== id));
    }, []);

    const definirPadrao = useCallback(async (id: string) => {
        const atualizado = await enderecoService.definirEnderecoPadrao(id);
        setEnderecos((prev) => prev.map((e) => ({ ...e, primary_address: e.id === id })));
        return atualizado;
    }, []);

    return {
        enderecos,
        loading,
        error,
        recarregar: carregar,
        adicionar,
        atualizar,
        remover,
        definirPadrao,
    };
}