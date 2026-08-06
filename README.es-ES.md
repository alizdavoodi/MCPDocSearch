

# Rastreador de Documentación y Servidor MCP

Este proyecto proporciona un conjunto de herramientas para rastrear sitios web, generar documentación en Markdown y hacer que esa documentación sea buscable a través de un servidor de Protocolo de Contexto de Modelo (MCP), diseñado para integrarse con herramientas como Cursor.

## Características

- **Rastreador Web (`crawler_cli`)**:
  - Rastrea sitios web comenzando desde una URL dada usando `crawl4ai`.
  - Profundidad de rastreo, patrones de URL (incluir/excluir), tipos de contenido, etc., configurables.
  - Limpieza opcional de HTML antes de la conversión a Markdown (elimina enlaces de navegación, encabezados y pies de página).
  - Genera un único archivo Markdown consolidado a partir del contenido rastreado.
  - Guarda la salida en `./storage/` de forma predeterminada.
- **Servidor MCP (`mcp_server`)**:
  - Carga archivos Markdown desde el directorio `./storage/`.
  - Analiza el Markdown en fragmentos semánticos basados en encabezados.
  - Genera incrustaciones vectoriales para cada fragmento usando `sentence-transformers` (`multi-qa-mpnet-base-dot-v1`).
  - **Caché:** Utiliza un archivo de caché (`storage/document_chunks_cache.pkl`) para almacenar fragmentos e incrustaciones procesados.
    - **Primera Ejecución:** El inicio inicial del servidor después de rastrear nuevos documentos puede tardar un poco, ya que debe analizar, fragmentar y generar incrustaciones para todo el contenido.
    - **Ejecuciones Subsecuentes:** Si el archivo de caché existe y los tiempos de modificación de los archivos `.md` fuente en `./storage/` no han cambiado, el servidor carga directamente desde la caché, lo que resulta en tiempos de inicio mucho más rápidos.
    - **Invalidación de Caché:** La caché se invalida y regenera automáticamente si cualquier archivo `.md` en `./storage/` se modifica, agrega o elimina desde la última creación de la caché.
  - Expone herramientas MCP a través de `fastmcp` para clientes como Cursor:
    - `list_documents`: Lista los documentos rastreados disponibles.
    - `get_document_headings`: Obtiene la estructura de encabezados de un documento.
    - `search_documentation`: Realiza una búsqueda semántica sobre fragmentos de documentos usando similitud vectorial.
- **Integración con Cursor**: Diseñado para ejecutar el servidor MCP a través del transporte `stdio` para su uso dentro de Cursor.

## Flujo de Trabajo

1. **Rastreo:** Usa la herramienta `crawler_cli` para rastrear un sitio web y generar un archivo `.md` en `./storage/`.
2. **Ejecutar Servidor:** Configura y ejecuta `mcp_server` (típicamente gestionado por un cliente MCP como Cursor).
3. **Cargar e Incrustar:** El servidor carga, fragmenta e incrusta automáticamente el contenido de los archivos `.md` en `./storage/`.
4. **Consulta:** Usa el cliente MCP (p. ej., Cursor Agent) para interactuar con las herramientas del servidor (`list_documents`, `search_documentation`, etc.) para consultar el contenido rastreado.

## Configuración

Este proyecto utiliza [`uv`](https://github.com/astral-sh/uv) para la gestión de dependencias y ejecución.

1. **Instalar `uv`**: Sigue las instrucciones en el [sitio web de uv](https://github.com/astral-sh/uv).
2. **Clonar el repositorio:**

   ```bash
   git clone https://github.com/alizdavoodi/MCPDocSearch.git
   cd MCPDocSearch
   ```

3. **Instalar dependencias:**

   ```bash
   uv sync
   ```

   Este comando crea un entorno virtual (usualmente `.venv`) e instala todas las dependencias listadas en `pyproject.toml`.

## Uso

### 1. Rastreo de Documentación

Ejecuta el rastreador usando el script `crawl.py` o directamente a través de `uv run`.

**Ejemplo Básico:**

```bash
uv run python crawl.py https://docs.example.com
```

Esto rastreará `https://docs.example.com` con la configuración predeterminada y guardará la salida en `./storage/docs.example.com.md`.

**Ejemplo con Opciones:**

```bash
uv run python crawl.py https://docs.another.site --output ./storage/custom_name.md --max-depth 2 --keyword "API" --keyword "Reference" --exclude-pattern "*blog*"
```

**Ver todas las opciones:**

```bash
uv run python crawl.py --help
```

Las opciones clave incluyen:

- `--output`/`-o`: Especifica la ruta del archivo de salida.
- `--max-depth`/`-d`: Establece la profundidad de rastreo (debe estar entre 1 y 5).
- `--include-pattern`/`--exclude-pattern`: Filtra las URLs a rastrear.
- `--keyword`/`-k`: Palabras clave para la puntuación de relevancia durante el rastreo.
- `--remove-links`/`--keep-links`: Controla la limpieza de HTML.
- `--cache-mode`: Controla la caché de `crawl4ai` (`DEFAULT`, `BYPASS`, `FORCE_REFRESH`).
- `--wait-for`: Espera un tiempo específico (segundos) o un selector CSS antes de capturar el contenido (p. ej., `5` o `'css:.content'`). Útil para páginas con carga diferida.
- `--js-code`: Ejecuta JavaScript personalizado en la página antes de capturar el contenido.
- `--page-load-timeout`: Establece el tiempo máximo (segundos) para esperar a que se cargue una página.
- `--wait-for-js-render`/`--no-wait-for-js-render`: Habilita un script específico para manejar mejor las Aplicaciones de Página Única (SPA) con mucho JavaScript, haciendo desplazamiento y haciendo clic en botones potenciales de "cargar más". Establece automáticamente un tiempo de espera predeterminado si no se especifica `--wait-for`.

#### Refinamiento de Rastreo con Patrones y Profundidad

A veces, es posible que desees rastrear solo una subsección específica de un sitio de documentación. Esto a menudo requiere prueba y error con `--include-pattern` y `--max-depth`.

- **`--include-pattern`**: Restringe el rastreador para que solo siga enlaces cuyas URLs coincidan con los patrones dados. Usa comodines (`*`) para flexibilidad.
- **`--max-depth`**: Controla cuántos "clics" alejados de la URL de inicio se permitirá que vaya el rastreador. Una profundidad de 1 significa que solo rastrea páginas enlazadas directamente desde la URL de inicio. Una profundidad de 2 significa que rastrea esas páginas _y_ las páginas enlazadas desde ellas (si también coinciden con los patrones de inclusión), y así sucesivamente.

**Ejemplo: Rastrear solo la sección de API de Administración de Pulsar**

Supongamos que solo quieres el contenido bajo `https://pulsar.apache.org/docs/4.0.x/admin-api-*`.

1. **URL de Inicio:** Podrías comenzar en la página de descripción general: `https://pulsar.apache.org/docs/4.0.x/admin-api-overview/`.
2. **Patrón de Inclusión:** Solo quieres enlaces que contengan `admin-api`: `--include-pattern "*admin-api*"`.
3. **Profundidad Máxima:** Necesitas averiguar cuántos niveles de profundidad tienen los enlaces de la API de administración desde la página inicial. Comienza con `2` y aumenta si es necesario.
4. **Modo Verbo:** Usa `-v` para ver qué URLs se están visitando o saltando, lo cual ayuda a depurar los patrones y la profundidad.

```bash
uv run python crawl.py https://pulsar.apache.org/docs/4.0.x/admin-api-overview/ -v --include-pattern "*admin-api*" --max-depth 2
```

Revisa el archivo de salida (`./storage/pulsar.apache.org.md` de forma predeterminada en este caso). Si faltan páginas, intenta aumentar `--max-depth` a `3`. Si se incluyen demasiadas páginas no relacionadas, haz que `--include-pattern` sea más específico o agrega reglas `--exclude-pattern`.

### 2. Ejecución del Servidor MCP

El servidor MCP está diseñado para ser ejecutado por un cliente MCP como Cursor a través del transporte `stdio`. El comando para ejecutar el servidor es:

```bash
python -m mcp_server.main
```

Sin embargo, debe ejecutarse desde el directorio raíz del proyecto (`MCPDocSearch`) para que Python pueda encontrar el módulo `mcp_server`.

## ⚠️ Precaución: Tiempo de Generación de Incrustaciones

El servidor MCP genera incrustaciones localmente la primera vez que se ejecuta o cada vez que los archivos Markdown fuente en `./storage/` cambian. Este proceso implica cargar un modelo de aprendizaje automático y procesar todos los fragmentos de texto.

- **El Tiempo Varía:** El tiempo requerido para la generación de incrustaciones puede variar significativamente según:
  - **Hardware:** Los sistemas con una GPU compatible (CUDA o Apple Silicon/MPS) serán mucho más rápidos que los sistemas solo con CPU.
  - **Tamaño de Datos:** El número total de archivos Markdown y la longitud de su contenido impactan directamente el tiempo de procesamiento.
- **Ten Paciencia:** Para conjuntos de documentación grandes o en hardware más lento, el inicio inicial (o el inicio después de cambios) puede tardar varios minutos. Los inicios subsecuentes que usan la caché serán mucho más rápidos. ⏳


### 3. Configuración de Cursor/Claude for Desktop

Para usar este servidor con Cursor, crea un archivo `.cursor/mcp.json` en la raíz de este proyecto (`MCPDocSearch/.cursor/mcp.json`) con el siguiente contenido:

```json
{
  "mcpServers": {
    "doc-query-server": {
      "command": "uv",
      "args": [
        "--directory",
        // IMPORTANT: Replace with the ABSOLUTE path to this project directory on your machine
        "/path/to/your/MCPDocSearch",
        "run",
        "python",
        "-m",
        "mcp_server.main"
      ],
      "env": {}
    }
  }
}
```

**Explicación:**

- `"doc-query-server"`: Un nombre para el servidor dentro de Cursor.
- `"command": "uv"`: Especifica `uv` como el ejecutor de comandos.
- `"args"`:
  - `"--directory", "/path/to/your/MCPDocSearch"`: **Crucialmente**, le indica a `uv` que cambie su directorio de trabajo a la raíz de tu proyecto antes de ejecutar el comando. **Reemplaza `/path/to/your/MCPDocSearch` con la ruta absoluta real en tu sistema.**
  - `"run", "python", "-m", "mcp_server.main"`: El comando que `uv` ejecutará dentro del directorio y entorno virtual correctos.

Después de guardar este archivo y reiniciar Cursor, "doc-query-server" debería estar disponible en la configuración MCP de Cursor y ser utilizable por el Agente (p. ej., `@doc-query-server search documentation for "how to install"`).

Para Claude for Desktop, puedes usar esta [documentación oficial](https://modelcontextprotocol.io/quickstart/server#mac-os-linux) para configurar el servidor MCP


## Dependencias

Bibliotecas clave utilizadas:

- `crawl4ai`: Funcionalidad principal de rastreo web.
- `fastmcp`: Implementación del servidor MCP.
- `sentence-transformers`: Generación de incrustaciones de texto.
- `torch`: Requerido por `sentence-transformers`.
- `typer`: Construcción de la CLI del rastreador.
- `uv`: Gestión de proyectos y entornos.
- `beautifulsoup4` (vía `crawl4ai`): Análisis de HTML.
- `rich`: Salida de terminal mejorada.

## Arquitectura

El proyecto sigue este flujo básico:

1. **`crawler_cli`**: Ejecutas esta herramienta, proporcionando una URL de inicio y opciones.
2. **Rastreo (`crawl4ai`)**: La herramienta usa `crawl4ai` para obtener páginas web, siguiendo enlaces según las reglas configuradas (profundidad, patrones).
3. **Limpieza (`crawler_cli/markdown.py`)**: Opcionalmente, el contenido HTML se limpia (eliminando navegación, enlaces) usando BeautifulSoup.
4. **Generación de Markdown (`crawl4ai`)**: El HTML limpio se convierte a Markdown.
5. **Almacenamiento (`./storage/`)**: El contenido Markdown generado se guarda en un archivo en el directorio `./storage/`.
6. **Inicio de `mcp_server`**: Cuando el servidor MCP inicia (usualmente a través de la configuración de Cursor), ejecuta `mcp_server/data_loader.py`.
7. **Carga y Caché**: El cargador de datos busca un archivo de caché (`.pkl`). Si es válido, carga fragmentos e incrustaciones desde la caché. De lo contrario, lee archivos `.md` desde `./storage/`.
8. **Fragmentación e Incrustación**: Los archivos Markdown se analizan en fragmentos basados en encabezados. Se generan incrustaciones para cada fragmento usando `sentence-transformers` y se almacenan en memoria (y se guardan en la caché).
9. **Herramientas MCP (`mcp_server/mcp_tools.py`)**: El servidor expone herramientas (`list_documents`, `search_documentation`, etc.) a través de `fastmcp`.
10. **Consulta (Cursor)**: Un cliente MCP como Cursor puede llamar a estas herramientas. `search_documentation` usa las incrustaciones precalculadas para encontrar fragmentos relevantes basándose en la similitud semántica con la consulta.

## Licencia

Este proyecto está licenciado bajo la Licencia MIT - consulta el archivo [LICENSE](LICENSE) para más detalles.

## Contribuciones

¡Las contribuciones son bienvenidas! Siéntete libre de abrir un problema o enviar una solicitud de extracción (pull request).

## Notas de Seguridad

- **Caché Pickle:** Este proyecto utiliza el módulo `pickle` de Python para almacenar en caché datos procesados (`storage/document_chunks_cache.pkl`). Deserializar datos de fuentes no confiables puede ser inseguro. Asegúrate de que el directorio `./storage/` solo sea escribible por usuarios/procesos de confianza.
