export default function CardapioVazio() {
    return (
        <div className="min-h-[70vh] flex flex-col items-center justify-center text-center px-6 py-20">
            <p
                className="text-lg font-bold text-[#1A0A00] mb-2"
                style={{ fontFamily: "Fraunces, serif" }}
            >
                Nenhum cardápio disponível hoje
            </p>
            <p className="text-sm text-[#6B5B4E]">
                Volte mais tarde — o restaurante ainda não publicou o cardápio
                de hoje.
            </p>
        </div>
    );
}
