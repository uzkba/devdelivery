import os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("DATABASE_URL")
print("repr:", repr(url))

if url:
    print("bytes:", url.encode("utf-8"))
    print("tamanho:", len(url))
    for i, ch in enumerate(url):
        if ord(ch) > 127:
            print(f"caractere não-ASCII na posição {i}: {ch!r} (código {ord(ch)})")
else:
    print("DATABASE_URL não foi encontrada — .env não está sendo lido")