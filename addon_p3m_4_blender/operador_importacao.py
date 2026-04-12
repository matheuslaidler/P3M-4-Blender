# pyright: reportMissingImports=false, reportInvalidTypeForm=false

from __future__ import annotations

import os

import bpy
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, StringProperty
from bpy.types import Operator, OperatorFileListElement
from bpy_extras.io_utils import ImportHelper

from .importador_blender import ConfiguracaoImportacaoP3M, importar_p3m_no_blender
from .leitor_binario import ErroFormatoP3M


class IMPORTAR_OT_p3m_for_blender(Operator, ImportHelper):
    """Importa arquivos P3M com foco em Blender moderno."""

    bl_idname = "import_scene.p3m_for_blender"
    bl_label = "Importar P3M for Blender"
    bl_description = "Importa modelo P3M no Blender com modo moderno e modo legado"
    bl_options = {"UNDO", "PRESET"}

    filename_ext = ".p3m"

    filter_glob: StringProperty(
        default="*.p3m",
        options={"HIDDEN"},
        maxlen=255,
    )

    files: CollectionProperty(
        name="Arquivos P3M",
        type=OperatorFileListElement,
    )

    directory: StringProperty(subtype="DIR_PATH")

    perfil_importacao: EnumProperty(
        name="Perfil de importacao",
        description=(
            "Modo moderno prioriza robustez no Blender atual; "
            "modo legado tenta reproduzir o comportamento antigo"
        ),
        items=[
            ("MODERNO", "Moderno (padrao)", "Importacao robusta para Blender 5.x"),
            ("LEGADO", "Legado (opcional)", "Compatibilidade com comportamento antigo"),
        ],
        default="MODERNO",
    )

    importar_ossos: BoolProperty(
        name="Importar ossos",
        description="Cria armature e vincula a malha aos ossos lidos do P3M",
        default=True,
    )

    modo_vinculacao: EnumProperty(
        name="Modo de vinculacao malha-osso",
        description="Define como a malha sera vinculada ao armature no Blender",
        items=[
            (
                "SEM_PARENTING",
                "Sem parenting (tecnico)",
                "Usa somente Armature modifier e vertex groups",
            ),
            (
                "COM_PARENTING",
                "Com parenting (trio completo)",
                "Usa parenting + Armature modifier + vertex groups",
            ),
        ],
        default="COM_PARENTING",
    )

    ocultar_ossos_sem_uso: BoolProperty(
        name="Ocultar ossos sem uso",
        description="Oculta ossos folha que nao influenciam vertices",
        default=False,
    )

    aplicar_correcao_orientacao: BoolProperty(
        name="Aplicar correcao de orientacao",
        description="Aplica transformacao de eixos usada pelo pipeline P3M",
        default=True,
    )

    posicionamento_vertical: EnumProperty(
        name="Posicionamento vertical",
        description="Escolhe como posicionar o modelo no chao apos a importacao",
        items=[
            (
                "AUTO_PERFIL",
                "Automatico por perfil",
                "Moderno: pe no chao | Legado: manter origem",
            ),
            (
                "MANTER_ORIGEM",
                "Manter origem original",
                "Preserva a origem espacial original do P3M",
            ),
            (
                "ALINHAR_CHAO_Z0",
                "Pe no chao (Blender)",
                "Alinha o menor ponto da malha em Z=0 para manter os pes no chao",
            ),
        ],
        default="AUTO_PERFIL",
    )

    aplicar_textura_externa: BoolProperty(
        name="Tentar aplicar textura externa",
        description=(
            "Procura automaticamente arquivo de textura (ex.: DDS) na pasta do P3M "
            "e cria material basico"
        ),
        default=True,
    )

    forcar_vinculo_osso_raiz: BoolProperty(
        name="Forcar vinculo sem osso ao osso raiz",
        description=(
            "Quando um vertice nao possui osso valido, vincula ao bone_0 para evitar "
            "malha solta em alguns arquivos"
        ),
        default=True,
    )

    validar_cabecalho: BoolProperty(
        name="Validar cabecalho P3M",
        description="Cancela a importacao se o cabecalho nao for identificado como P3M",
        default=True,
    )

    def _coletar_caminhos_arquivos(self) -> list[str]:
        if len(self.files) > 0:
            caminhos = [os.path.join(self.directory, arquivo.name) for arquivo in self.files]
            return [
                caminho
                for caminho in caminhos
                if os.path.isfile(caminho) and caminho.lower().endswith(".p3m")
            ]

        if self.filepath:
            if os.path.isdir(self.filepath):
                caminhos = [
                    os.path.join(self.filepath, nome)
                    for nome in sorted(os.listdir(self.filepath))
                    if nome.lower().endswith(".p3m")
                ]
                return [caminho for caminho in caminhos if os.path.isfile(caminho)]

            if os.path.isfile(self.filepath) and self.filepath.lower().endswith(".p3m"):
                return [self.filepath]

        if self.directory and os.path.isdir(self.directory):
            caminhos = [
                os.path.join(self.directory, nome)
                for nome in sorted(os.listdir(self.directory))
                if nome.lower().endswith(".p3m")
            ]
            return [caminho for caminho in caminhos if os.path.isfile(caminho)]

        return []

    def execute(self, context: bpy.types.Context):
        caminhos_arquivos = self._coletar_caminhos_arquivos()
        if not caminhos_arquivos:
            self.report({"ERROR"}, "Nenhum arquivo P3M foi selecionado.")
            return {"CANCELLED"}

        configuracao = ConfiguracaoImportacaoP3M(
            perfil_importacao=self.perfil_importacao,
            importar_ossos=self.importar_ossos,
            modo_vinculacao=self.modo_vinculacao,
            ocultar_ossos_sem_uso=self.ocultar_ossos_sem_uso,
            aplicar_correcao_orientacao=self.aplicar_correcao_orientacao,
            posicionamento_vertical=self.posicionamento_vertical,
            aplicar_textura_externa=self.aplicar_textura_externa,
            forcar_vinculo_osso_raiz=self.forcar_vinculo_osso_raiz,
            validar_cabecalho=self.validar_cabecalho,
        )

        total_sucesso = 0
        total_falha = 0
        total_avisos = 0

        for caminho_arquivo in caminhos_arquivos:
            try:
                resultado = importar_p3m_no_blender(
                    contexto=context,
                    caminho_arquivo=caminho_arquivo,
                    configuracao=configuracao,
                )
                total_sucesso += 1
                total_avisos += len(resultado.avisos)

            except ErroFormatoP3M as erro_formato:
                total_falha += 1
                self.report(
                    {"WARNING"},
                    f"Falha em '{os.path.basename(caminho_arquivo)}': {erro_formato}",
                )
            except Exception as erro_inesperado:  # noqa: BLE001
                total_falha += 1
                self.report(
                    {"WARNING"},
                    (
                        f"Erro inesperado ao importar '{os.path.basename(caminho_arquivo)}': "
                        f"{erro_inesperado}"
                    ),
                )

        if total_sucesso == 0:
            self.report({"ERROR"}, "Nenhum arquivo foi importado com sucesso.")
            return {"CANCELLED"}

        mensagem_final = (
            f"Importacao concluida: sucesso={total_sucesso}, "
            f"falha={total_falha}, avisos={total_avisos}."
        )
        self.report({"INFO"}, mensagem_final)
        return {"FINISHED"}


def _menu_importacao(self, _contexto):
    self.layout.operator(
        IMPORTAR_OT_p3m_for_blender.bl_idname,
        text="Perfect 3D Model for Blender (.p3m)",
    )


CLASSES = (IMPORTAR_OT_p3m_for_blender,)


def registrar_menu_importacao() -> None:
    bpy.types.TOPBAR_MT_file_import.append(_menu_importacao)


def remover_menu_importacao() -> None:
    bpy.types.TOPBAR_MT_file_import.remove(_menu_importacao)
