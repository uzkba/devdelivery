import type { ItemCardapio } from "../types/cardapio.types";

type Props = {
  item: ItemCardapio;
  onAdicionar: (item: ItemCardapio) => void;
};

export function ItemCardapioCard({ item, onAdicionar }: Props) {
  return (
    <button
      onClick={() => onAdicionar(item)}
      className="flex w-full items-center justify-between rounded-lg border border-neutral-200 p-4 text-left hover:bg-neutral-50"
    >
      <span className="text-base font-medium">{item.nome}</span>
      <span className="text-sm text-neutral-500">
        R$ {item.preco.toFixed(2)}
      </span>
    </button>
  );
}
