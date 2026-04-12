# pyright: reportMissingImports=false

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import bpy
import mathutils

from .modelos_p3m import ArquivoP3M
from .parser_p3m import analisar_arquivo_p3m

LOGGER = logging.getLogger(__name__)

MATRIZ_CORRECAO_ORIENTACAO = mathutils.Matrix(
    (
        (-1.0, 0.0, 0.0, 0.0),
        (0.0, 0.0, 1.0, 0.0),
        (0.0, 1.0, 0.0, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )
)

EXTENSOES_TEXTURA_BUSCA = (
    ".dds",
    ".png",
    ".jpg",
    ".jpeg",
    ".tga",
    ".bmp",
)


@dataclass(slots=True)
class ConfiguracaoImportacaoP3M:
    perfil_importacao: str = "MODERNO"
    importar_ossos: bool = True
    modo_vinculacao: str = "COM_PARENTING"
    ocultar_ossos_sem_uso: bool = False
    aplicar_correcao_orientacao: bool = True
    posicionamento_vertical: str = "AUTO_PERFIL"
    aplicar_textura_externa: bool = True
    forcar_vinculo_osso_raiz: bool = True
    validar_cabecalho: bool = True


@dataclass(slots=True)
class ResultadoImportacaoP3M:
    objeto_malha: bpy.types.Object
    objeto_armature: bpy.types.Object | None
    dados_arquivo: ArquivoP3M
    avisos: list[str]


def _obter_colecao_destino(contexto: bpy.types.Context) -> bpy.types.Collection:
    if contexto.collection is not None:
        return contexto.collection
    return contexto.scene.collection


def _desselecionar_todos(contexto: bpy.types.Context) -> None:
    for objeto in list(contexto.selected_objects):
        objeto.select_set(False)


def _ativar_objeto(contexto: bpy.types.Context, objeto: bpy.types.Object) -> None:
    _desselecionar_todos(contexto)
    objeto.select_set(True)
    contexto.view_layer.objects.active = objeto


def _trocar_modo(contexto: bpy.types.Context, objeto: bpy.types.Object, modo: str) -> None:
    _ativar_objeto(contexto, objeto)
    if objeto.mode != modo:
        bpy.ops.object.mode_set(mode=modo)


def _construir_filhos_por_osso(dados_arquivo: ArquivoP3M) -> tuple[dict[int, list[int]], list[str]]:
    avisos: list[str] = []
    filhos_por_osso: dict[int, list[int]] = {
        indice: [] for indice in range(dados_arquivo.total_ossos_angulo)
    }

    for indice_osso, osso_angulo in enumerate(dados_arquivo.ossos_angulo):
        filhos_unicos: set[int] = set()

        for indice_posicao in osso_angulo.indices_filhos_posicao:
            if not (0 <= indice_posicao < dados_arquivo.total_ossos_posicao):
                avisos.append(
                    (
                        f"Osso {indice_osso}: indice de osso de posicao invalido "
                        f"({indice_posicao})."
                    )
                )
                continue

            osso_posicao = dados_arquivo.ossos_posicao[indice_posicao]
            for indice_filho in osso_posicao.indices_filhos_angulo:
                if not (0 <= indice_filho < dados_arquivo.total_ossos_angulo):
                    avisos.append(
                        (
                            f"Osso {indice_osso}: filho de angulo invalido "
                            f"({indice_filho})."
                        )
                    )
                    continue
                if indice_filho == indice_osso:
                    continue
                filhos_unicos.add(indice_filho)

        filhos_por_osso[indice_osso] = sorted(filhos_unicos)

    return filhos_por_osso, avisos


def _construir_pais_por_filho(
    filhos_por_osso: dict[int, list[int]],
) -> tuple[dict[int, int], list[str]]:
    avisos: list[str] = []
    pai_por_filho: dict[int, int] = {}

    for indice_pai, lista_filhos in filhos_por_osso.items():
        for indice_filho in lista_filhos:
            if indice_filho in pai_por_filho and pai_por_filho[indice_filho] != indice_pai:
                avisos.append(
                    (
                        f"Filho {indice_filho} possui mais de um pai possivel "
                        f"({pai_por_filho[indice_filho]} e {indice_pai}). "
                        "Mantendo o primeiro para estabilidade."
                    )
                )
                continue
            pai_por_filho[indice_filho] = indice_pai

    return pai_por_filho, avisos


def _construir_cabecas_locais(dados_arquivo: ArquivoP3M) -> list[mathutils.Vector]:
    cabecas_locais: list[mathutils.Vector] = [
        mathutils.Vector((0.0, 0.0, 0.0)) for _ in range(dados_arquivo.total_ossos_angulo)
    ]

    for osso_posicao in dados_arquivo.ossos_posicao:
        vetor_posicao = mathutils.Vector(osso_posicao.vetor)
        for indice_filho in osso_posicao.indices_filhos_angulo:
            if 0 <= indice_filho < dados_arquivo.total_ossos_angulo:
                # Ultimo valor observado vence para manter compatibilidade com o script antigo.
                cabecas_locais[indice_filho] = vetor_posicao.copy()

    return cabecas_locais


def _calcular_cabecas_globais_legado(
    cabecas_locais: list[mathutils.Vector],
    pai_por_filho: dict[int, int],
) -> dict[int, mathutils.Vector]:
    cabecas = [vetor.copy() for vetor in cabecas_locais]

    for indice in range(len(cabecas)):
        indice_pai = pai_por_filho.get(indice)
        if indice_pai is None:
            continue
        if 0 <= indice_pai < len(cabecas):
            cabecas[indice] = cabecas[indice_pai] + cabecas[indice]

    return {indice: cabecas[indice] for indice in range(len(cabecas))}


def _calcular_cabecas_globais_moderno(
    cabecas_locais: list[mathutils.Vector],
    pai_por_filho: dict[int, int],
) -> tuple[dict[int, mathutils.Vector], list[str]]:
    avisos: list[str] = []
    memo: dict[int, mathutils.Vector] = {}
    pilha: set[int] = set()

    def resolver(indice: int) -> mathutils.Vector:
        if indice in memo:
            return memo[indice].copy()

        if indice in pilha:
            avisos.append(
                f"Ciclo detectado na hierarquia de ossos em torno do indice {indice}."
            )
            return cabecas_locais[indice].copy()

        pilha.add(indice)
        cabeca_global = cabecas_locais[indice].copy()
        indice_pai = pai_por_filho.get(indice)

        if indice_pai is not None and 0 <= indice_pai < len(cabecas_locais):
            cabeca_global = resolver(indice_pai) + cabeca_global

        pilha.remove(indice)
        memo[indice] = cabeca_global.copy()
        return cabeca_global

    resultado = {indice: resolver(indice) for indice in range(len(cabecas_locais))}
    return resultado, avisos


def _calcular_hierarquia_ossos(
    dados_arquivo: ArquivoP3M,
    perfil_importacao: str,
) -> tuple[dict[int, mathutils.Vector], dict[int, list[int]], list[str]]:
    avisos: list[str] = []
    filhos_por_osso, avisos_filhos = _construir_filhos_por_osso(dados_arquivo)
    pai_por_filho, avisos_pais = _construir_pais_por_filho(filhos_por_osso)
    cabecas_locais = _construir_cabecas_locais(dados_arquivo)

    avisos.extend(avisos_filhos)
    avisos.extend(avisos_pais)

    if perfil_importacao == "LEGADO":
        cabecas_globais = _calcular_cabecas_globais_legado(cabecas_locais, pai_por_filho)
    else:
        cabecas_globais, avisos_cabecas = _calcular_cabecas_globais_moderno(
            cabecas_locais, pai_por_filho
        )
        avisos.extend(avisos_cabecas)

    return cabecas_globais, filhos_por_osso, avisos


def _garantir_tail_minimo(osso_edit: bpy.types.EditBone) -> None:
    if (osso_edit.tail - osso_edit.head).length < 0.00001:
        osso_edit.tail = osso_edit.head + mathutils.Vector((0.0, 0.05, 0.0))


def _criar_armature_blender(
    contexto: bpy.types.Context,
    nome_base: str,
    dados_arquivo: ArquivoP3M,
    cabecas_globais: dict[int, mathutils.Vector],
    filhos_por_osso: dict[int, list[int]],
) -> bpy.types.Object:
    armature_data = bpy.data.armatures.new(f"{nome_base}_armature_data")
    objeto_armature = bpy.data.objects.new(f"{nome_base}_armature", armature_data)
    _obter_colecao_destino(contexto).objects.link(objeto_armature)

    _trocar_modo(contexto, objeto_armature, "EDIT")

    ossos_edit: list[bpy.types.EditBone] = []
    for indice_osso in range(dados_arquivo.total_ossos_angulo):
        osso_edit = armature_data.edit_bones.new(f"bone_{indice_osso}")
        osso_edit.use_deform = True
        cabeca = cabecas_globais.get(indice_osso, mathutils.Vector((0.0, 0.0, 0.0)))
        osso_edit.head = cabeca
        osso_edit.tail = cabeca + mathutils.Vector((0.0, 0.05, 0.0))
        ossos_edit.append(osso_edit)

    for indice_pai, lista_filhos in filhos_por_osso.items():
        if not (0 <= indice_pai < len(ossos_edit)):
            continue
        osso_pai = ossos_edit[indice_pai]
        for indice_filho in lista_filhos:
            if not (0 <= indice_filho < len(ossos_edit)):
                continue
            osso_filho = ossos_edit[indice_filho]
            if osso_filho.parent is None:
                osso_filho.parent = osso_pai

    for indice_osso, osso_edit in enumerate(ossos_edit):
        filhos_validos = [
            indice
            for indice in filhos_por_osso.get(indice_osso, [])
            if 0 <= indice < len(ossos_edit)
        ]

        if len(filhos_validos) == 1:
            osso_edit.tail = ossos_edit[filhos_validos[0]].head.copy()
        elif len(filhos_validos) == 0 and osso_edit.parent is not None:
            direcao = osso_edit.head - osso_edit.parent.head
            if direcao.length > 0.00001:
                osso_edit.tail = osso_edit.head + direcao.normalized() * 0.05

        _garantir_tail_minimo(osso_edit)

    _trocar_modo(contexto, objeto_armature, "OBJECT")
    return objeto_armature


def _criar_malha_blender(
    contexto: bpy.types.Context,
    nome_base: str,
    dados_arquivo: ArquivoP3M,
    cabecas_globais: dict[int, mathutils.Vector],
    forcar_vinculo_osso_raiz: bool,
) -> tuple[bpy.types.Object, list[str]]:
    avisos: list[str] = []

    posicoes_vertices: list[tuple[float, float, float]] = []
    for indice_vertice, vertice in enumerate(dados_arquivo.vertices):
        posicao = mathutils.Vector(vertice.posicao)

        indice_osso_efetivo, _foi_forcado = _resolver_indice_osso_efetivo(
            vertice=vertice,
            total_ossos=dados_arquivo.total_ossos_angulo,
            forcar_vinculo_osso_raiz=forcar_vinculo_osso_raiz,
        )

        if indice_osso_efetivo is not None:
            cabeca_osso = cabecas_globais.get(indice_osso_efetivo)
            if cabeca_osso is not None:
                posicao += cabeca_osso
            else:
                avisos.append(
                    (
                        f"Vertice {indice_vertice}: osso efetivo {indice_osso_efetivo} nao foi "
                        "encontrado para ajustar posicao."
                    )
                )

        posicoes_vertices.append((posicao.x, posicao.y, posicao.z))

    triangulos_validos: list[tuple[int, int, int]] = []
    limite_vertices = len(posicoes_vertices)

    for indice_triangulo, triangulo in enumerate(dados_arquivo.triangulos):
        a, b, c = triangulo.a, triangulo.b, triangulo.c
        if a >= limite_vertices or b >= limite_vertices or c >= limite_vertices:
            avisos.append(
                (
                    f"Triangulo {indice_triangulo}: indice fora do limite "
                    f"(a={a}, b={b}, c={c}, total_vertices={limite_vertices})."
                )
            )
            continue

        if len({a, b, c}) < 3:
            avisos.append(
                (
                    f"Triangulo {indice_triangulo}: indices repetidos "
                    f"(a={a}, b={b}, c={c})."
                )
            )
            continue

        triangulos_validos.append((a, b, c))

    malha = bpy.data.meshes.new(f"{nome_base}_mesh_data")
    malha.from_pydata(posicoes_vertices, [], triangulos_validos)

    if len(malha.polygons) > 0:
        malha.polygons.foreach_set("use_smooth", [True] * len(malha.polygons))

    if len(malha.loops) > 0:
        camada_uv = malha.uv_layers.new(name="UVMap")
        for loop in malha.loops:
            camada_uv.data[loop.index].uv = dados_arquivo.vertices[loop.vertex_index].uv

    normais = [vertice.normal for vertice in dados_arquivo.vertices]
    try:
        malha.normals_split_custom_set_from_vertices(normais)
    except Exception as erro:  # noqa: BLE001
        avisos.append(f"Nao foi possivel aplicar normais customizadas: {erro}")

    malha.validate(clean_customdata=False)
    malha.update()

    objeto_malha = bpy.data.objects.new(f"{nome_base}_mesh", malha)
    _obter_colecao_destino(contexto).objects.link(objeto_malha)
    return objeto_malha, avisos


def _criar_vertex_groups(
    objeto_malha: bpy.types.Object,
    dados_arquivo: ArquivoP3M,
    forcar_vinculo_osso_raiz: bool,
) -> tuple[int, int, int, int]:
    total_vinculados = 0
    total_sem_osso = 0
    total_indice_invalido = 0
    total_vinculados_forcados = 0

    for indice_osso in range(dados_arquivo.total_ossos_angulo):
        objeto_malha.vertex_groups.new(name=f"bone_{indice_osso}")

    for indice_vertice, vertice in enumerate(dados_arquivo.vertices):
        indice_osso_efetivo, foi_forcado = _resolver_indice_osso_efetivo(
            vertice=vertice,
            total_ossos=dados_arquivo.total_ossos_angulo,
            forcar_vinculo_osso_raiz=forcar_vinculo_osso_raiz,
        )

        if vertice.indice_osso is None:
            total_sem_osso += 1
        elif not (0 <= vertice.indice_osso < dados_arquivo.total_ossos_angulo):
            total_indice_invalido += 1

        if indice_osso_efetivo is None:
            continue

        if foi_forcado:
            peso = 1.0
            total_vinculados_forcados += 1
        else:
            peso = min(max(float(vertice.peso), 0.0), 1.0)
            total_vinculados += 1

        objeto_malha.vertex_groups[indice_osso_efetivo].add(
            [indice_vertice],
            peso,
            "REPLACE",
        )

    return (
        total_vinculados,
        total_sem_osso,
        total_indice_invalido,
        total_vinculados_forcados,
    )


def _resolver_indice_osso_efetivo(
    vertice,
    total_ossos: int,
    forcar_vinculo_osso_raiz: bool,
) -> tuple[int | None, bool]:
    indice_osso = vertice.indice_osso
    if indice_osso is not None and 0 <= indice_osso < total_ossos:
        return indice_osso, False

    if forcar_vinculo_osso_raiz and total_ossos > 0:
        return 0, True

    return None, False


def _configurar_modificador_armature(
    objeto_malha: bpy.types.Object,
    objeto_armature: bpy.types.Object,
    usar_parenting: bool,
) -> None:
    if usar_parenting:
        matriz_mundo_original = objeto_malha.matrix_world.copy()
        objeto_malha.parent = objeto_armature
        objeto_malha.matrix_parent_inverse = objeto_armature.matrix_world.inverted()
        objeto_malha.matrix_world = matriz_mundo_original

    modificador = None
    for item_modificador in objeto_malha.modifiers:
        if item_modificador.type == "ARMATURE":
            modificador = item_modificador
            break

    if modificador is None:
        modificador = objeto_malha.modifiers.new(name="Armature", type="ARMATURE")

    modificador.object = objeto_armature
    modificador.use_vertex_groups = True
    modificador.use_bone_envelopes = False


def _ocultar_ossos_sem_uso(
    objeto_armature: bpy.types.Object,
    dados_arquivo: ArquivoP3M,
) -> None:
    ossos_usados = {
        f"bone_{vertice.indice_osso}"
        for vertice in dados_arquivo.vertices
        if vertice.indice_osso is not None
    }

    for osso in objeto_armature.data.bones:
        if osso.name in ossos_usados:
            continue
        if len(osso.children) > 0:
            continue
        osso.hide = True


def _normalizar_texto_caminho_textura(texto: str) -> str:
    return texto.replace("\\", os.sep).replace("/", os.sep).strip(" \t\r\n\"")


def _resolver_texturas_externas(
    caminho_arquivo_p3m: str,
    dados_arquivo: ArquivoP3M,
) -> list[str]:
    pasta_modelo = os.path.dirname(caminho_arquivo_p3m)
    nome_base_modelo = os.path.splitext(os.path.basename(caminho_arquivo_p3m))[0]
    candidatos: list[str] = []

    for referencia in dados_arquivo.texturas_referenciadas:
        referencia_norm = _normalizar_texto_caminho_textura(referencia)
        if not referencia_norm:
            continue

        if os.path.isabs(referencia_norm):
            candidatos.append(referencia_norm)
        else:
            candidatos.append(os.path.join(pasta_modelo, referencia_norm))
            candidatos.append(os.path.join(pasta_modelo, os.path.basename(referencia_norm)))

    for extensao in EXTENSOES_TEXTURA_BUSCA:
        candidatos.append(os.path.join(pasta_modelo, f"{nome_base_modelo}{extensao}"))
        candidatos.append(os.path.join(pasta_modelo, f"{nome_base_modelo}{extensao.upper()}"))

    # Remove duplicatas preservando ordem e retorna apenas arquivos existentes.
    encontrados: list[str] = []
    vistos: set[str] = set()
    for candidato in candidatos:
        caminho_normalizado = os.path.normpath(candidato)
        if caminho_normalizado in vistos:
            continue
        vistos.add(caminho_normalizado)
        if os.path.exists(caminho_normalizado) and os.path.isfile(caminho_normalizado):
            encontrados.append(caminho_normalizado)

    return encontrados


def _aplicar_material_com_textura(
    objeto_malha: bpy.types.Object,
    caminho_textura: str,
) -> None:
    imagem = bpy.data.images.load(caminho_textura, check_existing=True)

    material = bpy.data.materials.new(name=f"{objeto_malha.name}_material")
    material.use_nodes = True

    arvore = material.node_tree
    if arvore is None:
        raise RuntimeError("Nao foi possivel criar arvore de nos do material.")

    nos = arvore.nodes
    links = arvore.links
    nos.clear()

    no_textura = nos.new(type="ShaderNodeTexImage")
    no_textura.image = imagem
    no_bsdf = nos.new(type="ShaderNodeBsdfPrincipled")
    no_saida = nos.new(type="ShaderNodeOutputMaterial")

    no_textura.location = (-450, 120)
    no_bsdf.location = (-140, 120)
    no_saida.location = (170, 120)

    links.new(no_textura.outputs["Color"], no_bsdf.inputs["Base Color"])
    if "Alpha" in no_textura.outputs and "Alpha" in no_bsdf.inputs:
        links.new(no_textura.outputs["Alpha"], no_bsdf.inputs["Alpha"])
    links.new(no_bsdf.outputs["BSDF"], no_saida.inputs["Surface"])

    if len(objeto_malha.data.materials) == 0:
        objeto_malha.data.materials.append(material)
    else:
        objeto_malha.data.materials[0] = material


def _tentar_aplicar_textura_externa(
    caminho_arquivo_p3m: str,
    objeto_malha: bpy.types.Object,
    dados_arquivo: ArquivoP3M,
) -> list[str]:
    avisos: list[str] = []
    texturas_encontradas = _resolver_texturas_externas(caminho_arquivo_p3m, dados_arquivo)

    if not texturas_encontradas:
        avisos.append(
            (
                "Nenhuma textura externa foi encontrada automaticamente para este P3M. "
                "Se houver DDS em outro diretorio, importe manualmente no material."
            )
        )
        return avisos

    caminho_textura = texturas_encontradas[0]
    try:
        _aplicar_material_com_textura(objeto_malha, caminho_textura)
    except Exception as erro:  # noqa: BLE001
        avisos.append(
            (
                "Falha ao aplicar textura externa automaticamente "
                f"('{caminho_textura}'): {erro}"
            )
        )

    return avisos


def _aplicar_correcao_orientacao(
    contexto: bpy.types.Context,
    objeto_malha: bpy.types.Object,
    objeto_armature: bpy.types.Object | None,
) -> None:
    objeto_malha.matrix_world = MATRIZ_CORRECAO_ORIENTACAO @ objeto_malha.matrix_world
    if objeto_armature is not None:
        objeto_armature.matrix_world = (
            MATRIZ_CORRECAO_ORIENTACAO @ objeto_armature.matrix_world
        )

    contexto.view_layer.update()


def _aplicar_posicionamento_vertical(
    contexto: bpy.types.Context,
    objeto_malha: bpy.types.Object,
    objeto_armature: bpy.types.Object | None,
    posicionamento_vertical: str,
) -> None:
    if posicionamento_vertical != "ALINHAR_CHAO_Z0":
        return

    if len(objeto_malha.data.vertices) == 0:
        return

    menor_z = min(
        (objeto_malha.matrix_world @ vertice.co).z for vertice in objeto_malha.data.vertices
    )
    deslocamento_z = -menor_z
    if abs(deslocamento_z) < 0.000001:
        return

    matriz_deslocamento = mathutils.Matrix.Translation((0.0, 0.0, deslocamento_z))
    objeto_malha.matrix_world = matriz_deslocamento @ objeto_malha.matrix_world

    if objeto_armature is not None:
        objeto_armature.matrix_world = matriz_deslocamento @ objeto_armature.matrix_world

    contexto.view_layer.update()


def _resolver_posicionamento_vertical(
    perfil_importacao: str,
    posicionamento_vertical: str,
) -> str:
    if posicionamento_vertical in {"MANTER_ORIGEM", "ALINHAR_CHAO_Z0"}:
        return posicionamento_vertical

    if perfil_importacao == "MODERNO":
        return "ALINHAR_CHAO_Z0"

    return "MANTER_ORIGEM"


def importar_p3m_no_blender(
    contexto: bpy.types.Context,
    caminho_arquivo: str,
    configuracao: ConfiguracaoImportacaoP3M,
) -> ResultadoImportacaoP3M:
    dados_arquivo = analisar_arquivo_p3m(
        caminho_arquivo=caminho_arquivo,
        validar_cabecalho=configuracao.validar_cabecalho,
        inverter_v_uv=True,
    )

    nome_base = os.path.splitext(os.path.basename(caminho_arquivo))[0]
    avisos = list(dados_arquivo.avisos)

    cabecas_globais, filhos_por_osso, avisos_hierarquia = _calcular_hierarquia_ossos(
        dados_arquivo,
        perfil_importacao=configuracao.perfil_importacao,
    )
    avisos.extend(avisos_hierarquia)

    objeto_armature: bpy.types.Object | None = None
    if configuracao.importar_ossos and dados_arquivo.total_ossos_angulo > 0:
        objeto_armature = _criar_armature_blender(
            contexto=contexto,
            nome_base=nome_base,
            dados_arquivo=dados_arquivo,
            cabecas_globais=cabecas_globais,
            filhos_por_osso=filhos_por_osso,
        )

    objeto_malha, avisos_malha = _criar_malha_blender(
        contexto=contexto,
        nome_base=nome_base,
        dados_arquivo=dados_arquivo,
        cabecas_globais=cabecas_globais,
        forcar_vinculo_osso_raiz=configuracao.forcar_vinculo_osso_raiz,
    )
    avisos.extend(avisos_malha)

    if configuracao.aplicar_correcao_orientacao:
        _aplicar_correcao_orientacao(contexto, objeto_malha, objeto_armature)

    posicionamento_vertical_resolvido = _resolver_posicionamento_vertical(
        perfil_importacao=configuracao.perfil_importacao,
        posicionamento_vertical=configuracao.posicionamento_vertical,
    )

    _aplicar_posicionamento_vertical(
        contexto=contexto,
        objeto_malha=objeto_malha,
        objeto_armature=objeto_armature,
        posicionamento_vertical=posicionamento_vertical_resolvido,
    )

    if objeto_armature is not None:
        (
            total_vinculados,
            total_sem_osso,
            total_indice_invalido,
            total_vinculados_forcados,
        ) = _criar_vertex_groups(
            objeto_malha,
            dados_arquivo,
            forcar_vinculo_osso_raiz=configuracao.forcar_vinculo_osso_raiz,
        )

        if total_vinculados == 0 and dados_arquivo.total_vertices > 0:
            avisos.append(
                (
                    "Nenhum vertice foi vinculado a osso com indices validos. "
                    "Teste perfil Legado ou habilite o vinculo forcado ao osso raiz."
                )
            )

        if total_sem_osso > 0:
            avisos.append(
                (
                    f"Vertices sem osso associado: {total_sem_osso}."
                )
            )

        if total_indice_invalido > 0:
            avisos.append(
                (
                    f"Vertices com indice de osso invalido: {total_indice_invalido}."
                )
            )

        if total_vinculados_forcados > 0:
            avisos.append(
                (
                    "Vinculo forcado ao osso raiz aplicado em "
                    f"{total_vinculados_forcados} vertices."
                )
            )

        usar_parenting = configuracao.modo_vinculacao == "COM_PARENTING"
        _configurar_modificador_armature(
            objeto_malha,
            objeto_armature,
            usar_parenting=usar_parenting,
        )

        if usar_parenting:
            avisos.append("Vinculacao aplicada no modo com parenting.")
        else:
            avisos.append("Vinculacao aplicada no modo sem parenting (moderno).")

        if configuracao.ocultar_ossos_sem_uso:
            _ocultar_ossos_sem_uso(objeto_armature, dados_arquivo)

    if configuracao.aplicar_textura_externa:
        avisos.extend(
            _tentar_aplicar_textura_externa(
                caminho_arquivo_p3m=caminho_arquivo,
                objeto_malha=objeto_malha,
                dados_arquivo=dados_arquivo,
            )
        )

    _ativar_objeto(contexto, objeto_malha)

    LOGGER.info(
        "Importacao P3M concluida | arquivo=%s | vertices=%s | triangulos=%s | ossos=%s",
        caminho_arquivo,
        dados_arquivo.total_vertices,
        dados_arquivo.total_triangulos,
        dados_arquivo.total_ossos_angulo,
    )

    return ResultadoImportacaoP3M(
        objeto_malha=objeto_malha,
        objeto_armature=objeto_armature,
        dados_arquivo=dados_arquivo,
        avisos=avisos,
    )
