bl_info = {
    "name": "P3M for Blender (Perfect 3D Model)",
    "author": "Matheus Laidler",
    "description": (
        "Importar e exportar modelo da KOG de diversos modos;"
        "Plugin desenvolvido, renovado e atualizado para Blender 5."
    ),
    "blender": (4, 5, 0),
    "version": (2, 1, 0),
    "location": "File > Import/Export > Perfect 3D Model for Blender (.p3m)",
    "warning": "",
    "doc_url": "",
    "category": "Import-Export",
}

import bpy

from .operador_exportacao import (
    CLASSES_EXPORTACAO,
    registrar_menu_exportacao,
    remover_menu_exportacao,
)
from .operador_importacao import CLASSES, registrar_menu_importacao, remover_menu_importacao

CLASSES_REGISTRO = CLASSES + CLASSES_EXPORTACAO


def register() -> None:
    for classe in CLASSES_REGISTRO:
        bpy.utils.register_class(classe)
    registrar_menu_importacao()
    registrar_menu_exportacao()


def unregister() -> None:
    remover_menu_exportacao()
    remover_menu_importacao()
    for classe in reversed(CLASSES_REGISTRO):
        bpy.utils.unregister_class(classe)


if __name__ == "__main__":
    register()
