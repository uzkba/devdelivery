import argparse
import getpass
import secrets
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import SessionLocal
from app.services.provisionamento_service import (
    ProvisionamentoError,
    provisionar_restaurante,
)


def _criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cria um restaurante novo com o primeiro admin, entrega padrão e categorias iniciais."
    )
    parser.add_argument("--nome", required=True, help="Nome fantasia do restaurante.")
    parser.add_argument("--admin-nome", required=True, help="Nome do primeiro admin.")
    parser.add_argument("--admin-login", required=True, help="Login do primeiro admin.")
    parser.add_argument("--slug", help="Link do cardápio. Se omitido, é gerado a partir do nome.")
    parser.add_argument("--telefone", help="Telefone do restaurante.")
    parser.add_argument("--cnpj", help="CNPJ do restaurante.")
    parser.add_argument(
        "--gerar-senha",
        action="store_true",
        help="Gera uma senha aleatória e a exibe uma única vez, em vez de pedir no terminal.",
    )
    parser.add_argument(
        "--sem-pausa-inicial",
        action="store_true",
        help="Cria o restaurante já aceitando pedidos (por padrão ele nasce pausado).",
    )
    return parser


def _obter_senha(gerar: bool) -> str | None:
    if gerar:
        return secrets.token_urlsafe(12)
    senha = getpass.getpass("Senha do admin: ")
    if senha != getpass.getpass("Repita a senha: "):
        print("Erro: as senhas não conferem.", file=sys.stderr)
        return None
    return senha


def main(argv: list[str] | None = None) -> int:
    args = _criar_parser().parse_args(argv)

    senha = _obter_senha(args.gerar_senha)
    if senha is None:
        return 1

    with SessionLocal() as db:
        try:
            resultado = provisionar_restaurante(
                db,
                nome=args.nome,
                admin_nome=args.admin_nome,
                admin_login=args.admin_login,
                admin_senha=senha,
                slug=args.slug,
                telefone=args.telefone,
                cnpj=args.cnpj,
                iniciar_pausado=not args.sem_pausa_inicial,
            )
        except ProvisionamentoError as erro:
            print(f"Erro: {erro}", file=sys.stderr)
            return 1

        restaurante = resultado.restaurante
        print("Restaurante provisionado com sucesso.")
        print(f"  Nome:       {restaurante.trade_name}")
        print(f"  Link:       /restaurantes/{restaurante.slug}")
        print(f"  Admin:      {resultado.admin.login}")
        if args.gerar_senha:
            print(f"  Senha:      {senha}   (anote agora: não será exibida de novo)")
        print(f"  Categorias: {', '.join(c.name for c in resultado.categorias)}")
        if restaurante.is_paused:
            print()
            print("O restaurante foi criado PAUSADO. Próximos passos:")
            print("  1. entrar no painel como admin e cadastrar os horários")
            print("     (PUT /admin/restaurante/horarios);")
            print("  2. retomar os pedidos (PATCH /admin/restaurante/pausa com")
            print('     {"pausado": false}).')

    return 0


if __name__ == "__main__":
    raise SystemExit(main())