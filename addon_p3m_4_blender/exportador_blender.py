# pyright: reportMissingImports=false

from __future__ import annotations

import os
import struct
from dataclasses import dataclass

import bpy

INDICE_NULO = 255
MAX_FILHOS = 10
CABECALHO_EXPORTACAO_PADRAO = "Perfact 3D Model (Ver 0.5)"


@dataclass(slots=True)
class ConfiguracaoExportacaoP3M:
    usar_objeto_ativo: bool = True
    comportamento_sem_armature: str = "BLOQUEAR"
    modo_pose_exportacao: str = "REST_POSE"


@dataclass(slots=True)
class ResultadoExportacaoP3M:
    caminho_arquivo: str
    total_ossos: int
    total_vertices: int
    total_triangulos: int
    avisos: list[str]


def _ordenar_ossos_topologico(armature_objeto: bpy.types.Object) -> list[bpy.types.Bone]:
    ossos = armature_objeto.data.bones
    visitado: set[str] = set()
    ordem: list[bpy.types.Bone] = []

    def visitar(osso: bpy.types.Bone) -> None:
        if osso.name in visitado:
            return
        visitado.add(osso.name)
        ordem.append(osso)
        for filho in sorted(osso.children, key=lambda item: item.name):
            visitar(filho)

    raizes = sorted([osso for osso in ossos if osso.parent is None], key=lambda item: item.name)
    for raiz in raizes:
        visitar(raiz)

    for osso in sorted(ossos, key=lambda item: item.name):
        visitar(osso)

    return ordem


def _resolver_objetos_exportacao(
    contexto: bpy.types.Context,
    usar_objeto_ativo: bool,
    comportamento_sem_armature: str,
) -> tuple[bpy.types.Object | None, bpy.types.Object]:
    objeto_ativo = contexto.view_layer.objects.active
    selecionados = list(contexto.selected_objects)

    armature_objeto: bpy.types.Object | None = None
    malha_objeto: bpy.types.Object | None = None

    if usar_objeto_ativo and objeto_ativo is not None:
        if objeto_ativo.type == "MESH":
            malha_objeto = objeto_ativo
            for modificador in objeto_ativo.modifiers:
                if modificador.type == "ARMATURE" and modificador.object is not None:
                    armature_objeto = modificador.object
                    break
        elif objeto_ativo.type == "ARMATURE":
            armature_objeto = objeto_ativo
            for filho in objeto_ativo.children:
                if filho.type == "MESH":
                    malha_objeto = filho
                    break

    if armature_objeto is None:
        for objeto in selecionados:
            if objeto.type == "ARMATURE":
                armature_objeto = objeto
                break

    if malha_objeto is None:
        for objeto in selecionados:
            if objeto.type == "MESH":
                malha_objeto = objeto
                break

    if malha_objeto is None and armature_objeto is not None:
        for filho in armature_objeto.children:
            if filho.type == "MESH":
                malha_objeto = filho
                break

    if malha_objeto is None:
        raise RuntimeError("Nao foi possivel encontrar malha para exportacao.")

    if armature_objeto is None and comportamento_sem_armature != "CRIAR_DUMMY":
        raise RuntimeError(
            (
                "Nao foi possivel encontrar armature para exportacao. "
                "Ative 'Criar osso raiz dummy' para exportar malha sem armature."
            )
        )

    return armature_objeto, malha_objeto


def _mapear_uv_por_vertice(malha: bpy.types.Mesh) -> dict[int, tuple[float, float]]:
    mapa_uv: dict[int, tuple[float, float]] = {}

    if len(malha.uv_layers) == 0:
        return mapa_uv

    camada_uv = malha.uv_layers.active
    if camada_uv is None:
        return mapa_uv

    for poligono in malha.polygons:
        for indice_vertice, indice_loop in zip(poligono.vertices, poligono.loop_indices):
            if indice_vertice in mapa_uv:
                continue
            uv = camada_uv.data[indice_loop].uv
            mapa_uv[indice_vertice] = (float(uv.x), float(uv.y))

    return mapa_uv


def _mapear_grupo_para_osso(
    malha_objeto: bpy.types.Object,
    indice_osso_por_nome: dict[str, int],
) -> dict[int, int]:
    mapa: dict[int, int] = {}
    for grupo in malha_objeto.vertex_groups:
        indice_osso = indice_osso_por_nome.get(grupo.name)
        if indice_osso is not None:
            mapa[grupo.index] = indice_osso
    return mapa


def _escolher_osso_primario(
    vertice: bpy.types.MeshVertex,
    grupo_para_osso: dict[int, int],
) -> tuple[int | None, float]:
    melhor_indice: int | None = None
    melhor_peso = -1.0

    for grupo in vertice.groups:
        indice_osso = grupo_para_osso.get(grupo.group)
        if indice_osso is None:
            continue
        if grupo.weight > melhor_peso:
            melhor_indice = indice_osso
            melhor_peso = float(grupo.weight)

    if melhor_indice is None:
        return None, 0.0

    return melhor_indice, max(0.0, min(melhor_peso, 1.0))


def _obter_cabecas_exportacao(
    armature_objeto: bpy.types.Object,
    ossos_ordenados: list[bpy.types.Bone],
    modo_pose_exportacao: str,
) -> tuple[dict[str, tuple[float, float, float]], list[str]]:
    avisos: list[str] = []
    cabecas_por_nome: dict[str, tuple[float, float, float]] = {}

    for osso in ossos_ordenados:
        cabeca = osso.head_local.copy()

        if modo_pose_exportacao == "POSE_ATUAL_COMO_REST":
            pose_osso = armature_objeto.pose.bones.get(osso.name)
            if pose_osso is not None:
                cabeca = pose_osso.head.copy()
            else:
                avisos.append(
                    (
                        f"Osso '{osso.name}' sem pose bone ativo; "
                        "usando head de rest pose."
                    )
                )

        cabecas_por_nome[osso.name] = (float(cabeca.x), float(cabeca.y), float(cabeca.z))

    return cabecas_por_nome, avisos


def exportar_p3m_do_blender(
    contexto: bpy.types.Context,
    caminho_arquivo: str,
    configuracao: ConfiguracaoExportacaoP3M,
) -> ResultadoExportacaoP3M:
    avisos: list[str] = []

    armature_objeto, malha_objeto = _resolver_objetos_exportacao(
        contexto,
        usar_objeto_ativo=configuracao.usar_objeto_ativo,
        comportamento_sem_armature=configuracao.comportamento_sem_armature,
    )

    ossos_ordenados: list[bpy.types.Bone] = []
    indice_osso_por_nome: dict[str, int] = {}
    posicoes_locais: list[tuple[float, float, float]] = []
    filhos_por_osso: list[list[int]] = []

    if armature_objeto is not None:
        ossos_ordenados = _ordenar_ossos_topologico(armature_objeto)

    total_ossos = len(ossos_ordenados)
    if total_ossos == 0:
        if configuracao.comportamento_sem_armature != "CRIAR_DUMMY":
            raise RuntimeError("Armature sem ossos nao pode ser exportada em P3M.")

        total_ossos = 1
        posicoes_locais = [(0.0, 0.0, 0.0)]
        filhos_por_osso = [[]]
        avisos.append(
            "Exportacao sem armature: usando osso raiz dummy para manter formato P3M valido."
        )

    if total_ossos > 255:
        raise RuntimeError("Formato P3M suporta no maximo 255 ossos.")

    cabecas_exportacao_por_nome: dict[str, tuple[float, float, float]] = {}

    if ossos_ordenados:
        cabecas_exportacao_por_nome, avisos_cabecas = _obter_cabecas_exportacao(
            armature_objeto=armature_objeto,
            ossos_ordenados=ossos_ordenados,
            modo_pose_exportacao=configuracao.modo_pose_exportacao,
        )
        avisos.extend(avisos_cabecas)

        indice_osso_por_nome = {osso.name: indice for indice, osso in enumerate(ossos_ordenados)}

        for osso in ossos_ordenados:
            cabeca_global = cabecas_exportacao_por_nome[osso.name]
            cabeca_local = list(cabeca_global)

            if osso.parent is not None:
                cabeca_pai_global = cabecas_exportacao_por_nome[osso.parent.name]
                cabeca_local[0] -= cabeca_pai_global[0]
                cabeca_local[1] -= cabeca_pai_global[1]
                cabeca_local[2] -= cabeca_pai_global[2]

            posicoes_locais.append(
                (float(cabeca_local[0]), float(cabeca_local[1]), float(cabeca_local[2]))
            )

            filhos = []
            for filho in sorted(osso.children, key=lambda item: item.name):
                indice_filho = indice_osso_por_nome.get(filho.name)
                if indice_filho is not None:
                    filhos.append(indice_filho)

            if len(filhos) > MAX_FILHOS:
                avisos.append(
                    (
                        f"Osso '{osso.name}' possui {len(filhos)} filhos; "
                        f"apenas {MAX_FILHOS} serao exportados."
                    )
                )

            filhos_por_osso.append(filhos[:MAX_FILHOS])

    modificadores_armature_desativados: list[bpy.types.Modifier] = []
    usar_pose_atual = configuracao.modo_pose_exportacao == "POSE_ATUAL_COMO_REST"

    if armature_objeto is not None and not usar_pose_atual:
        for modificador in malha_objeto.modifiers:
            if modificador.type != "ARMATURE":
                continue
            if not modificador.show_viewport:
                continue
            modificador.show_viewport = False
            modificadores_armature_desativados.append(modificador)

        if modificadores_armature_desativados:
            contexto.view_layer.update()
            avisos.append(
                (
                    "Malha exportada em pose de repouso para manter consistencia com os ossos. "
                    "A pose atual nao e gravada no P3M."
                )
            )

    if armature_objeto is not None and usar_pose_atual:
        possui_armature_modifier_ativo = any(
            modificador.type == "ARMATURE"
            and modificador.object == armature_objeto
            and modificador.show_viewport
            for modificador in malha_objeto.modifiers
        )
        if not possui_armature_modifier_ativo:
            avisos.append(
                (
                    "Modo 'Pose atual como nova rest pose' ativo, mas nao ha Armature modifier "
                    "visivel ligado a esta armature. Resultado pode sair sem a pose atual."
                )
            )

    if armature_objeto is None and usar_pose_atual:
        avisos.append(
            (
                "Modo 'Pose atual como nova rest pose' ignorado por ausencia de armature. "
                "Exportando em rest pose padrao."
            )
        )

    objeto_avaliado = None
    malha_avaliada = None

    try:
        depsgraph = contexto.evaluated_depsgraph_get()
        objeto_avaliado = malha_objeto.evaluated_get(depsgraph)
        malha_avaliada = objeto_avaliado.to_mesh(
            preserve_all_data_layers=True,
            depsgraph=depsgraph,
        )

        malha_avaliada.calc_loop_triangles()

        total_vertices = len(malha_avaliada.vertices)
        total_triangulos = len(malha_avaliada.loop_triangles)

        if total_vertices > 65535:
            raise RuntimeError("Formato P3M suporta no maximo 65535 vertices.")

        if total_triangulos > 65535:
            raise RuntimeError("Formato P3M suporta no maximo 65535 triangulos.")

        grupo_para_osso = _mapear_grupo_para_osso(malha_objeto, indice_osso_por_nome)
        mapa_uv = _mapear_uv_por_vertice(malha_avaliada)

        triangulos = [
            (int(tri.vertices[0]), int(tri.vertices[1]), int(tri.vertices[2]))
            for tri in malha_avaliada.loop_triangles
        ]

        vertices_exportacao: list[tuple[tuple[float, float, float], float, int, tuple[float, float, float], tuple[float, float]]] = []

        sem_vinculo = 0
        for vertice in malha_avaliada.vertices:
            posicao = vertice.co.copy()

            if ossos_ordenados:
                indice_osso, peso = _escolher_osso_primario(vertice, grupo_para_osso)
                indice_osso_bruto = INDICE_NULO

                if indice_osso is not None and 0 <= indice_osso < total_ossos:
                    osso = ossos_ordenados[indice_osso]
                    cabeca_osso = cabecas_exportacao_por_nome[osso.name]
                    posicao.x -= cabeca_osso[0]
                    posicao.y -= cabeca_osso[1]
                    posicao.z -= cabeca_osso[2]
                    indice_osso_bruto = indice_osso + total_ossos
                else:
                    sem_vinculo += 1
            else:
                peso = 1.0
                indice_osso_bruto = total_ossos

            normal = vertice.normal.copy()
            uv = mapa_uv.get(vertice.index, (0.0, 0.0))

            vertices_exportacao.append(
                (
                    (float(posicao.x), float(posicao.y), float(posicao.z)),
                    float(peso),
                    int(indice_osso_bruto),
                    (float(normal.x), float(normal.y), float(normal.z)),
                    (float(uv[0]), float(1.0 - uv[1])),
                )
            )

        if sem_vinculo > 0:
            avisos.append(f"Vertices sem osso vinculado: {sem_vinculo}.")

        with open(caminho_arquivo, "wb") as arquivo:
            cabecalho = CABECALHO_EXPORTACAO_PADRAO.encode("ascii", errors="ignore")
            arquivo.write(cabecalho.ljust(26, b"\x00")[:26])
            arquivo.write(b"\x00")

            arquivo.write(struct.pack("<B", total_ossos))
            arquivo.write(struct.pack("<B", total_ossos))

            for indice_osso, posicao_local in enumerate(posicoes_locais):
                arquivo.write(struct.pack("<3f", *posicao_local))

                filhos_angulo = [indice_osso]
                for indice_filho in filhos_angulo[:MAX_FILHOS]:
                    arquivo.write(struct.pack("<B", indice_filho))

                for _ in range(MAX_FILHOS - len(filhos_angulo[:MAX_FILHOS])):
                    arquivo.write(struct.pack("<B", INDICE_NULO))

                arquivo.write(struct.pack("<2x"))

            for indice_osso in range(total_ossos):
                arquivo.write(struct.pack("<4f", 0.0, 0.0, 0.0, 1.0))
                filhos_posicao = filhos_por_osso[indice_osso]

                for indice_filho in filhos_posicao:
                    arquivo.write(struct.pack("<B", indice_filho))

                for _ in range(MAX_FILHOS - len(filhos_posicao)):
                    arquivo.write(struct.pack("<B", INDICE_NULO))

                arquivo.write(struct.pack("<2x"))

            arquivo.write(struct.pack("<H", total_vertices))
            arquivo.write(struct.pack("<H", total_triangulos))
            arquivo.write(struct.pack("<260x"))

            for a, b, c in triangulos:
                arquivo.write(struct.pack("<3H", a, b, c))

            for posicao, peso, indice_osso_bruto, normal, uv in vertices_exportacao:
                arquivo.write(struct.pack("<3f", *posicao))
                arquivo.write(struct.pack("<f", peso))
                arquivo.write(struct.pack("<B", indice_osso_bruto))
                arquivo.write(struct.pack("<3x"))
                arquivo.write(struct.pack("<3f", *normal))
                arquivo.write(struct.pack("<2f", *uv))

        return ResultadoExportacaoP3M(
            caminho_arquivo=caminho_arquivo,
            total_ossos=total_ossos,
            total_vertices=total_vertices,
            total_triangulos=total_triangulos,
            avisos=avisos,
        )
    finally:
        if objeto_avaliado is not None:
            objeto_avaliado.to_mesh_clear()

        if modificadores_armature_desativados:
            for modificador in modificadores_armature_desativados:
                modificador.show_viewport = True
            contexto.view_layer.update()
