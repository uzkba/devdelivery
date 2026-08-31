import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
export function ItemCardapioCard({ item, onAdicionar }) {
    return (_jsxs("button", { onClick: () => onAdicionar(item), className: "flex w-full items-center justify-between rounded-lg border border-neutral-200 p-4 text-left hover:bg-neutral-50", children: [_jsx("span", { className: "text-base font-medium", children: item.nome }), _jsxs("span", { className: "text-sm text-neutral-500", children: ["R$ ", item.preco.toFixed(2)] })] }));
}
