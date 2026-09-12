import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCardapioDoDia } from "@/features/cardapio/hooks/useCardapioDoDia";
import { useCardapioCarrinho } from "@/features/cardapio/viewmodels/useCardapioCarrinho";
import { corDaCategoria } from "@/features/cardapio/utils/corPorCategoria";
import CardapioItemCard from "@/features/cardapio/components/CardapioItemCard";
import CardapioSkeleton from "@/features/cardapio/components/CardapioSkeleton";
import CardapioVazio from "@/features/cardapio/components/CardapioVazio";

export default function CardapioClientePage() {
    const navigate = useNavigate();
    const { cardapio, carregando, erro, recarregar } = useCardapioDoDia();
    const { quantidades, definirQuantidade, itensCarrinho, totalItens, total } =
        useCardapioCarrinho(cardapio);

    const sectionRefs = useRef<Record<string, HTMLElement | null>>({});
    const [categoriaAtiva, setCategoriaAtiva] = useState("");

    useEffect(() => {
        if (cardapio && cardapio.categorias.length > 0) {
            setCategoriaAtiva(cardapio.categorias[0].categoriaId);
        }
    }, [cardapio]);

    useEffect(() => {
        if (!cardapio) return;
        const obs = new IntersectionObserver(
            (entries) => {
                entries.forEach((e) => {
                    if (e.isIntersecting) setCategoriaAtiva(e.target.id);
                });
            },
            { rootMargin: "-30% 0px -60% 0px" },
        );
        Object.values(sectionRefs.current).forEach(
            (el) => el && obs.observe(el),
        );
        return () => obs.disconnect();
    }, [cardapio]);

    function handleContinuar() {
        navigate("/pedido/endereco", { state: { cartItems: itensCarrinho } });
    }

    if (carregando) return <CardapioSkeleton />;

    if (erro) {
        return (
            <div className="min-h-[70vh] flex flex-col items-center justify-center text-center px-6 py-20">
                <p className="text-sm text-[#6B5B4E] mb-4">{erro}</p>
                <button
                    onClick={recarregar}
                    className="px-4 py-2 rounded-xl font-bold text-sm"
                    style={{ background: "#F97316", color: "#fff" }}
                >
                    Tentar novamente
                </button>
            </div>
        );
    }

    if (!cardapio || cardapio.categorias.length === 0) {
        return <CardapioVazio />;
    }

    return (
        <div className="pb-40">
            <div
                className="sticky top-0 z-20 px-4 py-3 flex gap-2 overflow-x-auto"
                style={{
                    background: "rgba(255,248,239,0.97)",
                    borderBottom: "1px solid #E8D5C4",
                    scrollbarWidth: "none",
                }}
            >
                {cardapio.categorias.map((categoria) => (
                    <button
                        key={categoria.categoriaId}
                        onClick={() =>
                            sectionRefs.current[
                                categoria.categoriaId
                            ]?.scrollIntoView({
                                behavior: "smooth",
                                block: "start",
                            })
                        }
                        className="px-3.5 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap shrink-0 transition-all"
                        style={{
                            border: "1.5px solid #E8D5C4",
                            background:
                                categoriaAtiva === categoria.categoriaId
                                    ? "#1A0A00"
                                    : "#fff",
                            color:
                                categoriaAtiva === categoria.categoriaId
                                    ? "#fff"
                                    : "#6B5B4E",
                        }}
                    >
                        {categoria.categoriaNome}
                    </button>
                ))}
            </div>

            <div className="mx-4 mt-4 mb-1 flex items-center gap-2 text-sm text-[#6B5B4E]">
                <span className="w-2 h-2 rounded-full bg-green-500" />
                <span>
                    Cardápio de hoje ·{" "}
                    {new Date(`${cardapio.data}T00:00:00`).toLocaleDateString(
                        "pt-BR",
                    )}
                </span>
            </div>

            <div className="px-4 py-4 flex flex-col gap-8">
                {cardapio.categorias.map((categoria) => {
                    const accent = corDaCategoria(categoria.categoriaNome);
                    return (
                        <section
                            key={categoria.categoriaId}
                            id={categoria.categoriaId}
                            ref={(el) => {
                                sectionRefs.current[categoria.categoriaId] = el;
                            }}
                        >
                            <div className="flex items-center gap-2 mb-3">
                                <div
                                    className="w-1 h-5 rounded-full shrink-0"
                                    style={{ background: accent }}
                                />
                                <h2
                                    className="text-lg font-bold text-[#1A0A00]"
                                    style={{ fontFamily: "Fraunces, serif" }}
                                >
                                    {categoria.categoriaNome}
                                </h2>
                            </div>

                            <div className="flex flex-col gap-2">
                                {categoria.itens.map((item) => (
                                    <CardapioItemCard
                                        key={item.itemId}
                                        nome={item.nome}
                                        descricao={item.descricao}
                                        preco={item.preco}
                                        quantidade={
                                            quantidades[item.itemId] ?? 0
                                        }
                                        accent={accent}
                                        onIncrementar={() =>
                                            definirQuantidade(
                                                item.itemId,
                                                (quantidades[item.itemId] ??
                                                    0) + 1,
                                            )
                                        }
                                        onDecrementar={() =>
                                            definirQuantidade(
                                                item.itemId,
                                                (quantidades[item.itemId] ??
                                                    0) - 1,
                                            )
                                        }
                                    />
                                ))}
                            </div>
                        </section>
                    );
                })}
            </div>

            <div
                className="fixed bottom-0 left-0 right-0 z-30 px-4 py-4"
                style={{
                    background: "rgba(255,248,239,0.97)",
                    backdropFilter: "blur(12px)",
                    borderTop: "1.5px solid #E8D5C4",
                }}
            >
                <div className="max-w-lg mx-auto">
                    {totalItens > 0 ? (
                        <>
                            <div className="mb-3">
                                <p className="text-xs font-bold text-[#B0967E] uppercase tracking-wide mb-2">
                                    Seu pedido
                                </p>
                                <div className="flex flex-col gap-1">
                                    {itensCarrinho.map((item) => (
                                        <div
                                            key={item.id}
                                            className="flex justify-between items-center text-sm"
                                        >
                                            <span className="text-[#1A0A00] font-medium">
                                                {item.nome}
                                            </span>
                                            <span className="text-[#6B5B4E] font-bold">
                                                × {item.quantidade}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                                <div
                                    className="mt-2 pt-2 border-t flex justify-between items-center"
                                    style={{ borderColor: "#E8D5C4" }}
                                >
                                    <span className="text-sm font-semibold text-[#6B5B4E]">
                                        Total estimado
                                    </span>
                                    <span
                                        className="font-bold text-[#1A0A00]"
                                        style={{
                                            fontFamily: "Fraunces, serif",
                                        }}
                                    >
                                        {total.toLocaleString("pt-BR", {
                                            style: "currency",
                                            currency: "BRL",
                                        })}
                                    </span>
                                </div>
                            </div>
                            <button
                                onClick={handleContinuar}
                                className="w-full py-4 rounded-2xl font-bold text-base transition-all active:scale-[0.98]"
                                style={{
                                    fontFamily: "Fraunces, serif",
                                    background:
                                        "linear-gradient(135deg,#F97316,#EA580C)",
                                    color: "#fff",
                                    boxShadow:
                                        "0 4px 16px rgba(249,115,22,0.3)",
                                }}
                            >
                                Continuar
                            </button>
                        </>
                    ) : (
                        <p className="text-center text-sm text-[#B0967E] py-1">
                            Toque em um alimento para adicioná-lo ao pedido.
                        </p>
                    )}
                </div>
            </div>
        </div>
    );
}
