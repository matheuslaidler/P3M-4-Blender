# Perfect 3D Model for Blender
##### Updated add-on to import and export Kog's GC models to Blender v5

PT-BR e English documentation for the same addon.

## PT-BR

### Visao geral

P3M-4-Blender e um addon para importar e exportar arquivos .p3m com foco em estabilidade no Blender moderno e com mais funcionalidades.

Objetivos principais:

- Blender 5.1 e 5.0 como alvo principal
- Compatibilidade com Blender 4.5 (não testado)
- Modo moderno como padrao (recomendado)
- Modo legado opcional
- Fluxo unico de importacao e exportacao
- Conseguir importar modelos de Grand Chase dentro do Blender atual

### Recursos atuais

- Importacao P3M com validacao robusta
- Exportacao P3M com serializacao estavel
- Perfil de importacao Moderno e Legado
- Estrategia de vinculacao malha-osso:
  - Com parenting (padrao)
  - Sem parenting (tecnico)
- Correcao de orientacao opcional
- Posicionamento vertical configuravel:
  - Manter origem do arquivo
  - Pe no chao (parte mais baixa do modelo em Z=0)
- Aplicacao automatica de textura externa quando encontrada
- Opcao de forcar vertices sem osso para o osso raiz
- Export sem armature configuravel:
  - Bloquear (padrao)
  - Criar osso raiz dummy
- Modo de pose para exportacao:
  - Rest/T-Pose (padrao seguro)
  - Pose atual como nova Rest Pose

### Requisitos

- Blender 5.1 ou 5.0
- Blender 4.5 (compatibilidade)

### Instalacao

1. Compacte a pasta "addon_p3m_4_blender" em .zip ou baixar o arquivo "P3M_4_Blender.zip" em releases 
2. No Blender: Edit > Preferences > Add-ons
3. Clique em "Install from Disk" (na seta ao lado do botão de tag)
4. Selecione o arquivo zipado (P3M_4_Blender.zip)
5. Ative o addon P3M for Blender (vem ativado geralmente)

Menus:

- File > Import > Perfect 3D Model for Blender (.p3m)
- File > Export > Perfect 3D Model for Blender (.p3m)

### Tutorial de importacao

1. Abra File > Import > Perfect 3D Model for Blender (.p3m).
2. Selecione um arquivo .p3m, varios arquivos ou uma pasta.
3. Defina o Perfil de importacao:
   - Moderno (recomendado)
   - Legado (compatibilidade)
4. Ajuste opcoes relevantes:
   - Importar ossos
   - Modo de vinculacao malha-osso (skeleton-mesh)
   - Aplicar correcao de orientacao
   - Posicionamento vertical
   - Forcar vinculo sem osso ao osso raiz
5. Execute a importacao.

Notas importantes:

- O parser aceita cabecalhos com prefixo Perfect e Perfact.
- Se a malha vier com indices de osso ruins, habilite o vinculo forcado ao osso raiz.

### Tutorial de exportacao

1. Abra File > Export > Perfect 3D Model for Blender (.p3m).
2. Escolha se deseja priorizar objeto ativo.
3. Defina Exportar sem armature:
   - Bloquear exportacao (padrao)
   - Criar osso raiz dummy (para modelos sem osso)
4. Defina Modo de pose para exportacao:
  - Rest/T-Pose (padrao)
  - Pose atual como nova Rest Pose
5. Exporte para o caminho desejado.

Recomendacao de uso:

- Use Bloquear exportacao para rigs completos.
- Use Criar osso raiz dummy apenas quando o modelo nao tiver armature e voce precisar de round-trip tecnico.
- Rest/T-Pose (padrao) prioriza round-trip consistente e evita mismatch entre osso e malha.
- Pose atual como nova Rest Pose serve para gerar base em A-Pose ou qualquer outra pose customizada (Animações da pose original podem ficar incompatíveis).

### Troubleshooting

Problema: malha parece solta dos ossos.

- Teste Modo de vinculacao sem parenting no perfil Moderno.
- Teste Modo de vinculacao com parenting no perfil Legado.
- Confirme que Importar ossos esta ativo.

Problema: modelo fica abaixo do chao.

- Use Posicionamento vertical = Pe no chao (Blender). Nessa opção a parte mais baixa da malha ficará em Z = 0.

Problema: erro de export sem armature.

- Troque Exportar sem armature para Criar osso raiz dummy.

Problema: exportei com pose e ao reimportar a malha/ossos nao vieram na mesma pose.

- No modo Rest/T-Pose, isso e esperado: o export grava pose de repouso.
- Para manter a pose atual como base no arquivo exportado, use "Pose atual como nova Rest Pose".

Problema: sem textura apos importacao.

- Verifique se o arquivo de textura esta na mesma pasta do .p3m e com mesmo nome se necessário.
- Se a textura não foi identificada no modelo ou na pasta, aplique textura manualmente no material.

### Estrutura tecnica

- addon_p3m_v2/__init__.py: registro do addon
- addon_p3m_v2/operador_importacao.py: operador de importacao
- addon_p3m_v2/operador_exportacao.py: operador de exportacao
- addon_p3m_v2/importador_blender.py: pipeline de importacao
- addon_p3m_v2/exportador_blender.py: pipeline de exportacao
- addon_p3m_v2/parser_p3m.py: parser binario
- addon_p3m_v2/modelos_p3m.py: modelos e constantes
- addon_p3m_v2/leitor_binario.py: leitura binaria segura

### Creditos

- Desenvolvimento, atualização e modernizacao por Matheus Laidler
- Add-on criado baseado no trabalho original de John Kenneth L. Andales (Raitou)

---

## EN

### Overview

P3M-4-Blender is an addon for importing and exporting .p3m files with a focus on stability in modern Blender versions.

Main goals:

- Blender 5.1 and 5.0 as primary target
- Compatibility with Blender 4.5
- Modern mode as default
- Optional legacy mode
- Single unified import/export workflow
- Import GC characters to Blender

### Current features

- Robust P3M import validation
- Stable P3M export serialization
- Import profiles: Modern and Legacy
- Mesh-bone binding strategy:
  - With parenting (default)
  - No parenting (technical)
- Optional orientation correction
- Configurable vertical placement:
  - Keep file origin
  - Foot on ground (Blender)
- Automatic external texture attempt
- Optional force-bind for vertices without valid bone
- Configurable export without armature:
  - Block (default)
  - Create dummy root bone
- Export pose mode:
  - Rest/T-Pose (safe default)
  - Current pose as new Rest Pose

### Requirements

- Blender 5.1 or 5.0
- Blender 4.5 (compatibility)

### Installation

1. Zip the folder or download "P3M_4_Blender.zip" from releases.
2. In Blender: Edit > Preferences > Add-ons.
3. Click Install from Disk...
4. Select the zip file.
5. Enable P3M for Blender.

Menu entries:

- File > Import > Perfect 3D Model for Blender (.p3m)
- File > Export > Perfect 3D Model for Blender (.p3m)

### Import tutorial

1. Open File > Import > Perfect 3D Model for Blender (.p3m).
2. Select one file, multiple files, or a folder.
3. Choose Import profile:
   - Modern (recommended)
   - Legacy (compatibility)
4. Configure options:
   - Import bones
   - Mesh-bone binding mode
   - Orientation correction
   - Vertical placement
   - Force root bind for vertices without valid bone
5. Run import.

Important notes:

- Parser accepts both Perfect and Perfact header prefixes.
- For problematic bone indices, enable forced root binding.

### Export tutorial

1. Open File > Export > Perfect 3D Model for Blender (.p3m).
2. Choose whether to prioritize active object.
3. Set Export without armature:
   - Block export (default)
   - Create dummy root bone
4. Set Export pose mode:
  - Rest/T-Pose (default)
  - Current pose as new Rest Pose
5. Export to desired path.

Usage recommendation:

- Use Block export for complete rigs.
- Use Create dummy root bone only when the model has no armature and you need technical round-trip support.
- Rest/T-Pose (default) is the safest mode for consistent round-trip.
- Current pose as new Rest Pose is useful to export A-Pose or any custom bind base.

### Troubleshooting

Issue: mesh looks detached from bones.

- Try no-parenting mode in Modern profile.
- Try parenting mode in Legacy profile.
- Ensure Import bones is enabled.

Issue: model appears below the floor.

- Set Vertical placement to Foot on ground (Blender).

Issue: export error when no armature is present.

- Set Export without armature to Create dummy root bone.

Issue: I exported while posed and reimport does not preserve that exact pose.

- In Rest/T-Pose mode, this is expected by design.
- If you want to preserve the current pose as the new bind base, use Current pose as new Rest Pose.

Issue: texture missing after import.

- Ensure texture file exists in the same folder as the .p3m.
- If needed, assign the texture manually in the material.

### Technical structure

- addon_p3m_v2/__init__.py: addon registration
- addon_p3m_v2/operador_importacao.py: import operator
- addon_p3m_v2/operador_exportacao.py: export operator
- addon_p3m_v2/importador_blender.py: import pipeline
- addon_p3m_v2/exportador_blender.py: export pipeline
- addon_p3m_v2/parser_p3m.py: binary parser
- addon_p3m_v2/modelos_p3m.py: data models and constants
- addon_p3m_v2/leitor_binario.py: safe binary reader

### Credits

- Creation and modernization by Matheus Laidler
- Addon developed based on the original work by John Kenneth L. Andales (Raitou)
