from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.routers import autenticacao_route, teste

app = FastAPI(
    title="Delivery de Marmitas",
    description="API do sistema de delivery de marmitas",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(autenticacao_route.router)
app.include_router(teste.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}


# from backend.app.routers import pedido, cliente, cardapio
# app.include_router(pedido.router)
# app.include_router(cliente.router)