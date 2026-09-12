interface CardapioItemCardProps {
    nome: string;
    descricao?: string | null;
    preco: number;
    quantidade: number;
    accent: string;
    onIncrementar: () => void;
    onDecrementar: () => void;
}

export default function CardapioItemCard({
    nome,
    descricao,
    preco,
    quantidade,
    accent,
    onIncrementar,
    onDecrementar,
}: CardapioItemCardProps) {
    return (
        <div
            className="flex items-center gap-3 px-4 py-3.5 rounded-xl"
            style={{
                border:
                    quantidade > 0
                        ? `2px solid ${accent}`
                        : "1.5px solid #E8D5C4",
                background: quantidade > 0 ? accent + "0E" : "#fff",
                boxShadow:
                    quantidade > 0
                        ? `0 2px 10px ${accent}18`
                        : "0 1px 4px rgba(0,0,0,0.03)",
            }}
        >
            <div className="flex-1 min-w-0">
                <p className="text-base font-semibold leading-tight text-[#1A0A00]">
                    {nome}
                </p>
                {descricao && (
                    <p className="text-xs text-[#6B5B4E] mt-0.5 line-clamp-2">
                        {descricao}
                    </p>
                )}
                <p className="text-sm font-bold text-[#1A0A00] mt-1">
                    {preco.toLocaleString("pt-BR", {
                        style: "currency",
                        currency: "BRL",
                    })}
                </p>
            </div>

            <div className="flex items-center gap-0 shrink-0">
                {quantidade > 0 ? (
                    <>
                        <button
                            onClick={onDecrementar}
                            className="w-8 h-8 rounded-full flex items-center justify-center font-bold text-lg transition-all active:scale-90"
                            style={{ background: accent + "20", color: accent }}
                            aria-label={`Remover uma unidade de ${nome}`}
                        >
                            −
                        </button>
                        <span className="w-8 text-center font-bold text-[#1A0A00] text-base">
                            {quantidade}
                        </span>
                        <button
                            onClick={onIncrementar}
                            className="w-8 h-8 rounded-full flex items-center justify-center font-bold text-lg transition-all active:scale-90"
                            style={{ background: accent, color: "#fff" }}
                            aria-label={`Adicionar uma unidade de ${nome}`}
                        >
                            +
                        </button>
                    </>
                ) : (
                    <button
                        onClick={onIncrementar}
                        className="w-8 h-8 rounded-full flex items-center justify-center font-bold text-xl transition-all active:scale-90"
                        style={{
                            background: "#F5EDE3",
                            color: "#6B5B4E",
                            border: "1.5px solid #E8D5C4",
                        }}
                        aria-label={`Adicionar ${nome} ao carrinho`}
                    >
                        +
                    </button>
                )}
            </div>
        </div>
    );
}
