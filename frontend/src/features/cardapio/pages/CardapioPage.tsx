import { useCardapioHoje } from "../viewmodels/useCardapioHoje";
import { ItemCardapioCard } from "../components/ItemCardapioCard";

// Camada Page: monta a tela usando o viewmodel + componentes — sem chamar API direto.
export function CardapioPage() {
  const { cardapio, carregando, erro } = useCardapioHoje();

  if (carregando) return <p className="p-4">Carregando cardápio...</p>;
  if (erro) return <p className="p-4 text-red-600">{erro}</p>;
  if (!cardapio || cardapio.itens.length === 0) {
    return <p className="p-4">Nenhum item disponível no momento.</p>;
  }

  return (
    <main className="mx-auto max-w-xl space-y-3 p-4">
      <h1 className="text-xl font-semibold">Cardápio de hoje</h1>
      {cardapio.itens.map((item) => (
        <ItemCardapioCard key={item.id} item={item} onAdicionar={() => {}} />
      ))}
    </main>
  );
}
