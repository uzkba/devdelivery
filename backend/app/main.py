from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="DevDelivery API",
    description="API do sistema de delivery de marmitas",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # frontend Vite em dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TODO: incluir os routers conforme forem criados, ex.:
# from app.routers import auth, clientes, cardapio, pedidos, relatorios
# app.include_router(auth.router)
# app.include_router(clientes.router)
# app.include_router(cardapio.router)
# app.include_router(pedidos.router)
# app.include_router(relatorios.router)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}