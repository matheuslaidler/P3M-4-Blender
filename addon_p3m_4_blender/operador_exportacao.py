# pyright: reportMissingImports=false, reportInvalidTypeForm=false

from __future__ import annotations

import bpy
from bpy.props import BoolProperty, EnumProperty
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper

from .exportador_blender import ConfiguracaoExportacaoP3M, exportar_p3m_do_blender


class EXPORTAR_OT_p3m_for_blender(Operator, ExportHelper):
    """Exporta arquivo P3M com foco em robustez no Blender moderno."""

    bl_idname = "export_scene.p3m_for_blender"
    bl_label = "Exportar P3M for Blender"
    bl_description = "Exporta malha e armature para formato P3M"
    bl_options = {"UNDO", "PRESET"}

    filename_ext = ".p3m"

    filter_glob: bpy.props.StringProperty(
        default="*.p3m",
        options={"HIDDEN"},
        maxlen=255,
    )

    usar_objeto_ativo: BoolProperty(
        name="Priorizar objeto ativo",
        description=(
            "Tenta montar o par malha+armature a partir do objeto ativo antes de usar "
            "os selecionados"
        ),
        default=True,
    )

    comportamento_sem_armature: EnumProperty(
        name="Exportar sem armature",
        description="Define como tratar exportacao de malha sem armature",
        items=[
            (
                "BLOQUEAR",
                "Bloquear exportacao",
                "Cancela exportacao e orienta criar armature",
            ),
            (
                "CRIAR_DUMMY",
                "Criar osso raiz dummy",
                "Gera um osso raiz para manter arquivo P3M valido",
            ),
        ],
        default="BLOQUEAR",
    )

    modo_pose_exportacao: EnumProperty(
        name="Modo de pose para exportacao",
        description="Escolhe se exporta em rest pose ou transforma a pose atual em nova rest",
        items=[
            (
                "REST_POSE",
                "Rest/T-Pose (padrao)",
                "Mantem o comportamento seguro e consistente para round-trip",
            ),
            (
                "POSE_ATUAL_COMO_REST",
                "Pose atual como nova Rest Pose",
                "Bakeia a pose atual da malha+ossos como bind base no arquivo exportado",
            ),
        ],
        default="REST_POSE",
    )

    def execute(self, context: bpy.types.Context):
        configuracao = ConfiguracaoExportacaoP3M(
            usar_objeto_ativo=self.usar_objeto_ativo,
            comportamento_sem_armature=self.comportamento_sem_armature,
            modo_pose_exportacao=self.modo_pose_exportacao,
        )

        try:
            resultado = exportar_p3m_do_blender(
                contexto=context,
                caminho_arquivo=self.filepath,
                configuracao=configuracao,
            )
        except Exception as erro:  # noqa: BLE001
            self.report({"ERROR"}, f"Falha ao exportar P3M: {erro}")
            return {"CANCELLED"}

        if resultado.avisos:
            self.report(
                {"WARNING"},
                (
                    f"Exportacao concluida com avisos ({len(resultado.avisos)}). "
                    "Confira o console para detalhes."
                ),
            )
            for aviso in resultado.avisos:
                print(f"[P3M for Blender][AVISO] {aviso}")
        else:
            self.report(
                {"INFO"},
                (
                    f"Exportacao concluida: ossos={resultado.total_ossos}, "
                    f"vertices={resultado.total_vertices}, triangulos={resultado.total_triangulos}."
                ),
            )

        return {"FINISHED"}


def _menu_exportacao(self, _contexto):
    self.layout.operator(
        EXPORTAR_OT_p3m_for_blender.bl_idname,
        text="Perfect 3D Model for Blender (.p3m)",
    )


CLASSES_EXPORTACAO = (EXPORTAR_OT_p3m_for_blender,)


def registrar_menu_exportacao() -> None:
    bpy.types.TOPBAR_MT_file_export.append(_menu_exportacao)


def remover_menu_exportacao() -> None:
    bpy.types.TOPBAR_MT_file_export.remove(_menu_exportacao)
