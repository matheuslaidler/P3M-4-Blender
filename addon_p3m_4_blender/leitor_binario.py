from __future__ import annotations

import struct


class ErroFormatoP3M(RuntimeError):
    """Erro usado quando o conteudo do arquivo P3M nao respeita o layout esperado."""


class LeitorBinario:
    def __init__(self, conteudo: bytes, caminho_arquivo: str) -> None:
        self._conteudo = conteudo
        self._cursor = 0
        self.caminho_arquivo = caminho_arquivo

    @property
    def cursor(self) -> int:
        return self._cursor

    @property
    def tamanho_total(self) -> int:
        return len(self._conteudo)

    @property
    def bytes_restantes(self) -> int:
        return self.tamanho_total - self._cursor

    def _garantir_tamanho(self, tamanho: int, campo: str) -> None:
        if self._cursor + tamanho > self.tamanho_total:
            raise ErroFormatoP3M(
                (
                    f"Arquivo truncado ao ler '{campo}'. "
                    f"Cursor={self._cursor}, precisando={tamanho}, "
                    f"restante={self.bytes_restantes}, arquivo='{self.caminho_arquivo}'."
                )
            )

    def ler_bytes(self, tamanho: int, campo: str) -> bytes:
        self._garantir_tamanho(tamanho, campo)
        inicio = self._cursor
        fim = inicio + tamanho
        self._cursor = fim
        return self._conteudo[inicio:fim]

    def ler_struct(self, formato: str, campo: str) -> tuple:
        estrutura = struct.Struct(formato)
        bloco = self.ler_bytes(estrutura.size, campo)
        return estrutura.unpack(bloco)

    def pular(self, tamanho: int, campo: str) -> None:
        self._garantir_tamanho(tamanho, campo)
        self._cursor += tamanho
