# Perfect 3D Model for Blender
##### Updated add-on to import and export Kog's GC models to Blender v5

<img width="672" height="504" alt="image" src="https://github.com/user-attachments/assets/0f55ba37-f4fb-4d6e-a305-2e334eec8c9b" />

> PT-BR and English documentation for the same add-on.

---

## PT-BR

### Visão geral

P3M-4-Blender é um add-on para importar e exportar arquivos .p3m com foco em estabilidade no Blender moderno e com mais funcionalidades.

Objetivos principais:

- Blender 5.1 e 5.0 como alvo principal
- Compatibilidade com Blender 4.5 (não testado)
- Modo moderno como padrão (recomendado)
- Modo legado opcional
- Fluxo único de importação e exportação
- Conseguir importar modelos de Grand Chase dentro do Blender atual

### Recursos atuais

- Importação P3M com validação robusta
- Exportação P3M com serialização estável
- Perfil de importação Moderno e Legado
- Estratégia de vinculação malha-osso:
  - Com parenting (padrão)
  - Sem parenting (técnico)
- Correção de orientação opcional
- Posicionamento vertical configurável:
  - Manter origem do arquivo
  - Pé no chão (parte mais baixa do modelo em Z=0)
- Aplicação automática de textura externa quando encontrada
- Opção de forçar vértices sem osso para o osso raiz
- Exportação sem armature configurável:
  - Bloquear (padrão)
  - Criar osso raiz dummy
- Modo de pose para exportação:
  - Rest/T-Pose (padrão seguro)
  - Pose atual como nova Rest Pose

### Requisitos

- Blender 5.1 ou 5.0
- Blender 4.5 (compatibilidade)

### Instalação

<img width="354" height="438" alt="image" src="https://github.com/user-attachments/assets/f51daf01-7324-4c6b-a2f5-6fd18871e1f5" />

1. Compacte a pasta "addon_p3m_4_blender" em .zip ou baixe o arquivo "P3M_4_Blender.zip" ([releases](https://github.com/matheuslaidler/P3M-4-Blender/releases/)) 
2. No Blender: Edit > Preferences > Add-ons
3. Clique em "Install from Disk" (na seta ao lado do botão de tag)
4. Selecione o arquivo zipado (P3M_4_Blender.zip)
5. Ative o add-on P3M for Blender (geralmente já vem ativado)

<img width="916" height="350" alt="image" src="https://github.com/user-attachments/assets/e04ca929-5655-41ed-aa0c-bd70d6fff2d3" />

Menus:

- File > Import > Perfect 3D Model for Blender (.p3m)
- File > Export > Perfect 3D Model for Blender (.p3m)

<img width="451" height="251" alt="image" src="https://github.com/user-attachments/assets/0a40946a-e023-4b2b-bec1-df9ad3b7e8e3" />

### Tutorial de importação

1. Abra File > Import > Perfect 3D Model for Blender (.p3m).
2. Selecione um arquivo .p3m, vários arquivos ou uma pasta.
3. Defina o Perfil de importação:
   - Moderno (recomendado)
   - Legado (compatibilidade)
4. Ajuste opções relevantes:
   - Importar ossos
   - Modo de vinculação malha-osso (skeleton-mesh)
   - Aplicar correção de orientação
   - Posicionamento vertical
   - Forçar vínculo sem osso ao osso raiz
5. Execute a importação.

<img width="957" height="271" alt="image" src="https://github.com/user-attachments/assets/dd11e15f-f2e5-49e9-8bfc-789a88c31b75" />

Notas importantes:

- O parser aceita cabeçalhos com prefixo Perfect e Perfact.
- Se a malha vier com índices de osso ruins, habilite o vínculo forçado ao osso raiz.

### Tutorial de exportação

1. Abra File > Export > Perfect 3D Model for Blender (.p3m).
2. Escolha se deseja priorizar o objeto ativo.
3. Defina Exportar sem armature:
   - Bloquear exportação (padrão)
   - Criar osso raiz dummy (para modelos sem osso)
4. Defina Modo de pose para exportação:
  - Rest/T-Pose (padrão)
  - Pose atual como nova Rest Pose
5. Exporte para o caminho desejado.

Recomendação de uso:

- Use Bloquear exportação para rigs completos.
- Use Criar osso raiz dummy apenas quando o modelo não tiver armature e você precisar de round-trip técnico.
- Rest/T-Pose (padrão) prioriza round-trip consistente e evita mismatch entre osso e malha.
- Pose atual como nova Rest Pose serve para gerar base em A-Pose ou qualquer outra pose customizada (animações da pose original podem ficar incompatíveis).

### Solução de problemas

Problema: malha parece solta dos ossos.

- Teste Modo de vinculação sem parenting no perfil Moderno.
- Teste Modo de vinculação com parenting no perfil Legado.
- Confirme se Importar ossos está ativo.

Problema: modelo fica abaixo do chão.

- Use Posicionamento vertical = Pé no chão (Blender). Nessa opção, a parte mais baixa da malha ficará em Z = 0.

Problema: erro de exportação sem armature.

- Troque Exportar sem armature para Criar osso raiz dummy.

Problema: exportei com pose e ao reimportar a malha/ossos não vieram na mesma pose.

- No modo Rest/T-Pose, isso é esperado: o exportador grava a pose de repouso.
- Para manter a pose atual como base no arquivo exportado, use "Pose atual como nova Rest Pose".

Problema: sem textura após importação.

- Verifique se o arquivo de textura está na mesma pasta do .p3m e com o mesmo nome, se necessário.
- Se a textura não foi identificada no modelo ou na pasta, aplique a textura manualmente no material.

### Estrutura técnica

- addon_p3m_v2/__init__.py: registro do add-on
- addon_p3m_v2/operador_importacao.py: operador de importação
- addon_p3m_v2/operador_exportacao.py: operador de exportação
- addon_p3m_v2/importador_blender.py: pipeline de importação
- addon_p3m_v2/exportador_blender.py: pipeline de exportação
- addon_p3m_v2/parser_p3m.py: parser binário
- addon_p3m_v2/modelos_p3m.py: modelos e constantes
- addon_p3m_v2/leitor_binario.py: leitura binária segura

### Créditos

- Desenvolvimento, atualização e modernização por Matheus Laidler
- Add-on criado baseado no trabalho original de John Kenneth L. Andales (Raitou)

---

## EN

### Overview

P3M-4-Blender is an add-on for importing and exporting .p3m files with a focus on stability in modern Blender versions.

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

1. Zip the folder or download "P3M_4_Blender.zip" from ([releases](https://github.com/matheuslaidler/P3M-4-Blender/releases/)).
2. In Blender: Edit > Preferences > Add-ons.
3. Click Install from Disk...
4. Select the zip file.
5. Enable P3M for Blender.

Menu entries:

- File > Import > Perfect 3D Model for Blender (.p3m)
- File > Export > Perfect 3D Model for Blender (.p3m)

### Import tutorial

*Note: The add-on interface is currently in Portuguese. The translations below will guide you on what to select.*

1. Open File > Import > Perfect 3D Model for Blender (.p3m).
2. Select one file, multiple files, or a folder.
3. Choose the Import profile (Perfil de importação):
   - **Moderno** (Modern - recommended)
   - **Legado** (Legacy - compatibility)
4. Configure options:
   - **Importar ossos** (Import bones)
   - **Modo de vinculação malha-osso** (Mesh-bone binding mode)
   - **Aplicar correção de orientação** (Apply orientation correction)
   - **Posicionamento vertical** (Vertical placement)
   - **Forçar vínculo sem osso ao osso raiz** (Force root bind for vertices without valid bone)
5. Run import.

Important notes:

- Parser accepts both Perfect and Perfact header prefixes.
- For problematic bone indices, enable forced root binding (**Forçar vínculo sem osso ao osso raiz**).

### Export tutorial

1. Open File > Export > Perfect 3D Model for Blender (.p3m).
2. Choose whether to prioritize active object.
3. Set Export without armature (Exportar sem armature):
   - **Bloquear exportação** (Block export - default)
   - **Criar osso raiz dummy** (Create dummy root bone)
4. Set Export pose mode (Modo de pose para exportação):
  - **Rest/T-Pose** (Rest/T-Pose - default)
  - **Pose atual como nova Rest Pose** (Current pose as new Rest Pose)
5. Export to desired path.

Usage recommendation:

- Use **Bloquear exportação** (Block export) for complete rigs.
- Use **Criar osso raiz dummy** (Create dummy root bone) only when the model has no armature and you need technical round-trip support.
- **Rest/T-Pose** (default) is the safest mode for consistent round-trip.
- **Pose atual como nova Rest Pose** is useful to export A-Pose or any custom bind base.

### Troubleshooting

Issue: mesh looks detached from bones.

- Try no-parenting mode in Modern profile (**Moderno**).
- Try parenting mode in Legacy profile (**Legado**).
- Ensure Import bones (**Importar ossos**) is enabled.

Issue: model appears below the floor.

- Set Vertical placement (Posicionamento vertical) to **Pé no chão (Blender)**.

Issue: export error when no armature is present.

- Set Export without armature to **Criar osso raiz dummy**.

Issue: I exported while posed and reimport does not preserve that exact pose.

- In Rest/T-Pose mode, this is expected by design.
- If you want to preserve the current pose as the new bind base, use **Pose atual como nova Rest Pose**.

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
- Add-on developed based on the original work by John Kenneth L. Andales (Raitou)
