from __future__ import annotations

from .leitor_binario import ErroFormatoP3M, LeitorBinario
from .modelos_p3m import (
    ArquivoP3M,
    CABECALHOS_ACEITOS_PREFIXO,
    CABECALHO_ESPERADO_PREFIXO,
    INDICE_NULO,
    OssoAnguloP3M,
    OssoPosicaoP3M,
    TAMANHO_CABECALHO_P3M,
    TrianguloP3M,
    VerticeP3M,
)

EXTENSOES_TEXTURA_CONHECIDAS = (
    ".dds",
    ".png",
    ".jpg",
    ".jpeg",
    ".tga",
    ".bmp",
    ".tif",
    ".tiff",
)


def _ler_indices_filhos(leitor: LeitorBinario, campo: str) -> list[int]:
    indices_brutos = leitor.ler_struct("<10B", campo)
    return [int(indice) for indice in indices_brutos if indice != INDICE_NULO]


def _cabecalho_p3m_valido(versao: str) -> bool:
    versao_normalizada = " ".join(versao.strip().split()).lower()
    return any(
        versao_normalizada.startswith(prefixo.lower())
        for prefixo in CABECALHOS_ACEITOS_PREFIXO
    )


def _extrair_texturas_referenciadas_do_bloco(bloco_textura_bruto: bytes) -> list[str]:
    texturas_referenciadas: list[str] = []

    for trecho in bloco_textura_bruto.split(b"\x00"):
        if not trecho:
            continue

        texto = trecho.decode("ascii", errors="ignore").strip(" \t\r\n")
        if not texto:
            continue

        texto = "".join(caractere for caractere in texto if 32 <= ord(caractere) <= 126)
        texto = texto.replace("\\", "/")
        if len(texto) < 4:
            continue

        if any(texto.lower().endswith(extensao) for extensao in EXTENSOES_TEXTURA_CONHECIDAS):
            texturas_referenciadas.append(texto)

    # Remove duplicatas preservando a ordem original.
    return list(dict.fromkeys(texturas_referenciadas))


def analisar_arquivo_p3m(
    caminho_arquivo: str,
    validar_cabecalho: bool = True,
    inverter_v_uv: bool = True,
) -> ArquivoP3M:
    with open(caminho_arquivo, "rb") as arquivo:
        conteudo = arquivo.read()

    leitor = LeitorBinario(conteudo, caminho_arquivo)
    avisos: list[str] = []

    cabecalho_bruto = leitor.ler_bytes(TAMANHO_CABECALHO_P3M, "cabecalho")
    versao = cabecalho_bruto.decode("ascii", errors="ignore").strip("\x00 ")
    leitor.pular(1, "padding apos cabecalho")

    if validar_cabecalho and not _cabecalho_p3m_valido(versao):
        raise ErroFormatoP3M(
            (
                "Cabecalho P3M inesperado. "
                f"Valor lido='{versao}', arquivo='{caminho_arquivo}'. "
                f"Prefixos aceitos={CABECALHOS_ACEITOS_PREFIXO}."
            )
        )

    total_ossos_posicao, total_ossos_angulo = leitor.ler_struct(
        "<2B", "contagem de ossos"
    )

    ossos_posicao: list[OssoPosicaoP3M] = []
    for indice_posicao in range(total_ossos_posicao):
        x, y, z = leitor.ler_struct("<3f", f"osso_posicao_{indice_posicao}_vetor")
        indices_filhos_angulo = _ler_indices_filhos(
            leitor, f"osso_posicao_{indice_posicao}_filhos"
        )
        leitor.pular(2, f"padding osso_posicao_{indice_posicao}")
        ossos_posicao.append(
            OssoPosicaoP3M(
                x=float(x),
                y=float(y),
                z=float(z),
                indices_filhos_angulo=indices_filhos_angulo,
            )
        )

    ossos_angulo: list[OssoAnguloP3M] = []
    for indice_angulo in range(total_ossos_angulo):
        x, y, z, escala = leitor.ler_struct(
            "<4f", f"osso_angulo_{indice_angulo}_vetor"
        )
        indices_filhos_posicao = _ler_indices_filhos(
            leitor, f"osso_angulo_{indice_angulo}_filhos"
        )
        leitor.pular(2, f"padding osso_angulo_{indice_angulo}")
        ossos_angulo.append(
            OssoAnguloP3M(
                x=float(x),
                y=float(y),
                z=float(z),
                escala=float(escala),
                indices_filhos_posicao=indices_filhos_posicao,
            )
        )

    total_vertices, total_triangulos = leitor.ler_struct(
        "<2H", "contagem de vertices e triangulos"
    )
    bloco_textura_bruto = leitor.ler_bytes(260, "bloco de textura de 260 bytes")
    texturas_referenciadas = _extrair_texturas_referenciadas_do_bloco(bloco_textura_bruto)

    if not texturas_referenciadas and any(byte != 0 for byte in bloco_textura_bruto):
        avisos.append(
            (
                "Bloco de textura contem dados nao nulos, mas nenhum caminho de imagem "
                "foi decodificado automaticamente."
            )
        )

    triangulos: list[TrianguloP3M] = []
    for indice_triangulo in range(total_triangulos):
        a, b, c = leitor.ler_struct("<3H", f"triangulo_{indice_triangulo}")
        triangulos.append(TrianguloP3M(a=int(a), b=int(b), c=int(c)))

    vertices: list[VerticeP3M] = []
    total_indices_legado = 0
    total_indices_diretos = 0
    total_indices_invalidos = 0
    for indice_vertice in range(total_vertices):
        x, y, z, peso = leitor.ler_struct("<4f", f"vertice_{indice_vertice}_base")
        indice_osso_bruto = leitor.ler_struct(
            "<B", f"vertice_{indice_vertice}_indice_osso"
        )[0]
        leitor.pular(3, f"padding vertice_{indice_vertice}_indice_osso")
        nx, ny, nz, u, v = leitor.ler_struct("<5f", f"vertice_{indice_vertice}_normal_uv")

        if inverter_v_uv:
            v = 1.0 - v

        indice_osso: int | None = None
        if indice_osso_bruto != INDICE_NULO:
            indice_convertido_legado = int(indice_osso_bruto) - int(total_ossos_posicao)
            indice_convertido_direto = int(indice_osso_bruto)

            if 0 <= indice_convertido_legado < int(total_ossos_angulo):
                indice_osso = indice_convertido_legado
                total_indices_legado += 1
            elif 0 <= indice_convertido_direto < int(total_ossos_angulo):
                indice_osso = indice_convertido_direto
                total_indices_diretos += 1
            else:
                total_indices_invalidos += 1
                avisos.append(
                    (
                        f"Vertice {indice_vertice}: indice de osso invalido "
                        (
                            f"(valor_bruto={indice_osso_bruto}, "
                            f"convertido_legado={indice_convertido_legado}, "
                            f"convertido_direto={indice_convertido_direto})."
                        )
                    )
                )

        vertices.append(
            VerticeP3M(
                x=float(x),
                y=float(y),
                z=float(z),
                peso=float(peso),
                indice_osso=indice_osso,
                nx=float(nx),
                ny=float(ny),
                nz=float(nz),
                u=float(u),
                v=float(v),
            )
        )

    if leitor.bytes_restantes > 0:
        avisos.append(
            (
                "Arquivo possui bytes extras ao final. "
                f"Restante={leitor.bytes_restantes} bytes."
            )
        )

    if total_indices_diretos > 0:
        avisos.append(
            (
                "Foram detectados vertices com indice de osso em modo direto "
                f"(total={total_indices_diretos})."
            )
        )

    if total_indices_invalidos > 0:
        avisos.append(
            (
                "Vertices com indice de osso invalido: "
                f"{total_indices_invalidos}."
            )
        )

    return ArquivoP3M(
        caminho_arquivo=caminho_arquivo,
        versao=versao,
        ossos_posicao=ossos_posicao,
        ossos_angulo=ossos_angulo,
        triangulos=triangulos,
        vertices=vertices,
        bloco_textura_bruto=bloco_textura_bruto,
        texturas_referenciadas=texturas_referenciadas,
        avisos=avisos,
    )
