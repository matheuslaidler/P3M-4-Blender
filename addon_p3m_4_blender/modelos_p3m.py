from __future__ import annotations

from dataclasses import dataclass, field

INDICE_NULO = 255
TAMANHO_CABECALHO_P3M = 26
CABECALHO_ESPERADO_PREFIXO = "Perfect 3D Model"
CABECALHOS_ACEITOS_PREFIXO = (
    "Perfect 3D Model",
    "Perfact 3D Model",
)


@dataclass(slots=True)
class OssoPosicaoP3M:
    x: float
    y: float
    z: float
    indices_filhos_angulo: list[int] = field(default_factory=list)

    @property
    def vetor(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)


@dataclass(slots=True)
class OssoAnguloP3M:
    x: float
    y: float
    z: float
    escala: float
    indices_filhos_posicao: list[int] = field(default_factory=list)


@dataclass(slots=True)
class TrianguloP3M:
    a: int
    b: int
    c: int


@dataclass(slots=True)
class VerticeP3M:
    x: float
    y: float
    z: float
    peso: float
    indice_osso: int | None
    nx: float
    ny: float
    nz: float
    u: float
    v: float

    @property
    def posicao(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)

    @property
    def normal(self) -> tuple[float, float, float]:
        return (self.nx, self.ny, self.nz)

    @property
    def uv(self) -> tuple[float, float]:
        return (self.u, self.v)


@dataclass(slots=True)
class ArquivoP3M:
    caminho_arquivo: str
    versao: str
    ossos_posicao: list[OssoPosicaoP3M]
    ossos_angulo: list[OssoAnguloP3M]
    triangulos: list[TrianguloP3M]
    vertices: list[VerticeP3M]
    bloco_textura_bruto: bytes
    texturas_referenciadas: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    @property
    def total_ossos_posicao(self) -> int:
        return len(self.ossos_posicao)

    @property
    def total_ossos_angulo(self) -> int:
        return len(self.ossos_angulo)

    @property
    def total_triangulos(self) -> int:
        return len(self.triangulos)

    @property
    def total_vertices(self) -> int:
        return len(self.vertices)
