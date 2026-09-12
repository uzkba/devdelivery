const CORES_POR_CATEGORIA: Record<string, string> = {
    arroz: "#D97706",
    feijao: "#EA580C",
    carnes: "#DC2626",
    acompanhamentos: "#CA8A04",
    saladas: "#16A34A",
    bebidas: "#0EA5E9",
};

function normalizar(nome: string): string {
    return nome
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase()
        .trim();
}

export function corDaCategoria(nomeCategoria: string): string {
    return CORES_POR_CATEGORIA[normalizar(nomeCategoria)] ?? "#F97316";
}
