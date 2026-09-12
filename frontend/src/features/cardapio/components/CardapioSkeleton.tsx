export default function CardapioSkeleton() {
    return (
        <div className="min-h-[70vh] px-4 py-4 flex flex-col gap-8 animate-pulse">
            {[0, 1, 2].map((grupo) => (
                <div key={grupo} className="flex flex-col gap-3">
                    <div className="h-5 w-32 rounded bg-[#E8D5C4]" />
                    <div className="flex flex-col gap-2">
                        {[0, 1, 2].map((linha) => (
                            <div
                                key={linha}
                                className="h-16 rounded-xl bg-[#F5EDE3]"
                            />
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
}
