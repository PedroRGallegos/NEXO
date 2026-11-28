# Referencias del proyecto NEXO: interfaz gráfica y diseño

Última actualización: 27 de noviembre de 2026

## 1. Alcance y criterio

Este documento reúne todo lo que se ha usado como referencia para la interfaz gráfica y el diseño de NEXO. Distingue entre tres cosas que no conviene mezclar:

- **Referencia de inspiración o estudio:** se consultó o se tuvo en cuenta, pero no se incorporó código.
- **Dependencia real:** se instala y se usa en el proyecto.
- **Material aportado por las personas autoras:** enunciados e imágenes de referencia.

Estado de las dependencias: el frontend solo depende de `react` y `react-dom` en ejecución (ver `nexo/frontend/package.json`). No se ha instalado ninguna de las bibliotecas de chat de la sección 5, y el código de la interfaz se escribió para este proyecto.

Los enlaces a documentación oficial de las secciones 6 y 7 son direcciones conocidas de cada proyecto. No se han vuelto a verificar en esta revisión, así que conviene abrirlos antes de entregar.

## 2. Material aportado por las personas autoras

| Material | Para qué se usó |
|---|---|
| `Proyecto_POO_por_capas_-_NEXO__tu_primer_agente_de_IA.pdf` (enunciado académico) | Requisitos funcionales (comandos, herramientas, modelos, persistencia) y rúbrica. Cada comando de la consola tiene su equivalente en la interfaz; ver la tabla de la guía de funcionamiento |
| Texto de la actividad del Tema 2 (LLM, validación, reintentos, streaming, `uso.csv`) | Streaming visible en el chat, panel de estadísticas con tokens y coste, y mensajes de error amables |
| Tres imágenes de referencia de una esfera holográfica dorada (partículas, anillos fragmentados, núcleo brillante y marcos de interfaz, al estilo JARVIS) | Dirección visual del núcleo animado de NEXO. **No se ha reproducido ningún fotograma**: la esfera se genera por código con un diseño propio. Procedencia y autoría de las imágenes: [COMPLETAR: fuente] |
| Peticiones de diseño de las personas autoras (cyberpunk, megacorporación, personalidad propia, logo basado en un núcleo) | Identidad visual, logo y tema; ver sección 4 |

## 3. Asistente de IA

El diseño de la interfaz, el logo, la esfera y el código del frontend se desarrollaron con ayuda de **Claude** (Anthropic), a partir de las peticiones y las imágenes anteriores. Detalle en la sección 8 del README.

Una petición se resolvió con un personaje original, porque la IA no dibuja personas reales (la sorpresa del «67», que usaba un robot original, se eliminó):

- Para «Fernando Alonso», la animación usa un piloto genérico celebrando una victoria, con el nombre escrito en texto. No representa a ninguna persona real.
- Además, al escribir «Fernando Alonso» el chat muestra una fotografía real (`nexo/frontend/public/sorpresas/fernando-alonso.jpg`) que aportó el equipo; no la generó ni la buscó la IA. [COMPLETAR: fuente, autoría y licencia de la fotografía; si es de una agencia o un medio, comprobar que se puede publicar o sustituirla por una imagen con licencia libre.]

## 4. Lenguaje de diseño aplicado

Estilo: cyberpunk de megacorporación, con una versión híbrida que prioriza la claridad. Las decisiones y dónde están en el código:

| Elemento | Decisión | Dónde |
|---|---|---|
| Paleta | Cian (NEXO), azul y violeta (marca, estados y operador) sobre casi negro; neón cyberpunk sin ninguna librería externa | `frontend/src/estilos/base.css`, `cyberpunk.css` |
| Formas | Esquinas biseladas con `clip-path` y franjas de peligro en cabecera y compositor | `cyberpunk.css` |
| Tipografía | Pila de fuentes monoespaciadas del sistema, en mayúsculas con espaciado; no se cargan fuentes externas | `base.css`, `cyberpunk.css` |
| Mensajes | Aspecto de registro de terminal («OPERADOR //» y «NEXO //»), herramientas como líneas de ejecución con sus argumentos | `Mensaje.tsx`, `cyberpunk.css` |
| Logo | Emblema de anillos fragmentados con núcleo hexagonal, marcas de calibración y esquinas de enfoque; también es el favicon | `Logo.tsx`, `logo.css`, `index.html` |
| Núcleo de IA | Esfera de partículas y trazos azules y violetas dibujada en un `canvas`, con tres estados (en espera, procesando y respondiendo) | `EsferaJarvis.tsx`, `esfera.css`, `NexoFace.tsx` |
| Panel de datos del núcleo | Solo datos reales: modelo, contexto estimado, estado de la API y último comando | `NexoFace.tsx` |
| Sorpresas | Ilustración de piloto genérico para «Fernando Alonso» y respuesta con la foto aportada por el equipo (la sorpresa del «67» se eliminó) | `huevos.ts`, `Huevo.tsx`, `dominio/sorpresas.py` |
| Texto de las respuestas | Markdown resuelto sin HTML (sin riesgo de XSS) | `formato.ts`, `TextoFormateado.tsx` |
| Adaptación a pantallas | Media queries reunidas; cajón lateral y paneles a pantalla completa en móvil | `responsive.css` |
| Rendimiento | Tope de fotogramas de la esfera, pausa con la pestaña oculta y sin capas decorativas de pantalla completa | `EsferaJarvis.tsx`, `cyberpunk.css` |
| Accesibilidad | `prefers-reduced-motion` desactiva las animaciones, `aria-label` en el núcleo y avisos con `role="status"` | varios |

## 5. Investigación de interfaces de chat en GitHub

Resumen de la investigación realizada el 17 de noviembre de 2026. Los 15 proyectos se estudiaron como **referencia** de estructura, no como código a copiar. Las valoraciones son estimaciones orientativas de esa investigación, no puntuaciones oficiales, y las licencias son las indicadas en cada repositorio en aquella fecha.

### Arquitectura recomendada en esa investigación

1. **Interfaz:** estructura visual, mensajes, campo de entrada, historial y estilos.
2. **Controlador del chat:** gestiona el envío, los estados de carga y los errores.
3. **Adaptador de comunicación:** transforma los mensajes al formato que espera el programa de IA.
4. **Programa de IA:** conserva su lógica y devuelve la respuesta.

En NEXO esto se corresponde con: componentes de `frontend/src/components/`, el hook `useChat.ts`, `frontend/src/api/` (cliente y lector de streaming) y el agente de `servicios/agente.py`.

### Repositorios

| Proyecto | Repositorio | Tecnología indicada | Licencia indicada | Valoración |
|---|---|---|---|---:|
| assistant-ui | https://github.com/assistant-ui/assistant-ui | React, TypeScript, Tailwind, Radix UI | MIT | 10/10 |
| Prompt Kit | https://github.com/ibelick/prompt-kit | React, TypeScript, Tailwind, shadcn/ui | MIT | 9,5/10 |
| Lumi UI | https://github.com/mrigankad/Lumi-UI | React, TypeScript, Radix UI, Tailwind | Apache 2.0 | 9,5/10 |
| RadChat | https://github.com/The01Geek/radchat | React, TypeScript | Apache 2.0 | 9,5/10 |
| chatcn | https://github.com/leonickson1/chatcn | React, TypeScript, Tailwind, shadcn/ui | MIT | 9/10 |
| Chat UI Kit React (Chatscope) | https://github.com/chatscope/chat-ui-kit-react | React, JavaScript, CSS | MIT | 9/10 |
| Chat Component (MIE Web) | https://github.com/mieweb/chat-component | React, Tailwind, Zustand | ISC | 9/10 |
| ChatGPT UI Clone (Chirag-kadajji) | https://github.com/Chirag-kadajji/ChatGPT-UI-Clone | HTML, CSS, JavaScript, Tailwind | MIT | 8,5/10 |
| Chat UI (Serkanbyx) | https://github.com/Serkanbyx/chat-ui | React, TypeScript, Vite, Zustand, Tailwind | MIT | 8,5/10 |
| Chatbot UI Lite | https://github.com/mckaywrigley/chatbot-ui-lite | Next.js, React, TypeScript, Tailwind | MIT | 8,5/10 |
| AI Chatbot (BinaryVortex) | https://github.com/BinaryVortex/AI-Chatbot | HTML, CSS, JavaScript | Sin licencia declarada | 8/10 |
| React Chatbot (Vectara) | https://github.com/vectara/react-chatbot | React, TypeScript, CSS | Apache 2.0 | 8/10 |
| BotUI | https://github.com/botui/botui | JavaScript, React, TypeScript | MIT | 7,5/10 |
| Peekobot | https://github.com/Peekobot/peekobot | HTML, CSS, JavaScript | MIT | 7/10 |
| ChatWidget.js (Harshal19t) | https://github.com/Harshal19t/chat-widget | HTML, CSS, JavaScript | MIT | 10/10 como widget |

### Qué se tomó de cada referencia principal

| Necesidad | Referencia estudiada | Aplicación en NEXO |
|---|---|---|
| Diseño general y temas | Lumi UI | Interfaz oscura propia, con tema definido en variables CSS |
| Burbujas de mensajes | Lumi UI, chatcn | Mensajes diferenciados por rol; resultado propio con estética de registro de terminal |
| Campo de entrada | Prompt Kit | Compositor con contador de caracteres y envío con teclado |
| Indicadores de generación | ChatWidget.js, Lumi UI | Indicador de proceso y cursor durante el streaming |
| Comunicación desacoplada | RadChat, ChatWidget.js | Cliente de API aislado en `frontend/src/api/` |
| Historial | RadChat, assistant-ui | Lista de conversaciones en la barra lateral |
| Adaptación a pantallas | RadChat, chatcn | Diseño con menú lateral en móvil y paneles que se compactan |

La correspondencia sale de la recomendación de la investigación del 17 de noviembre; no se ha comprobado una por una frente al código de cada repositorio. «Estudiada» significa que se tuvo en cuenta la idea o la estructura; no se ha copiado código de estos repositorios. Si en algún momento se incorpora código de alguno, hay que indicarlo aquí y respetar su licencia. BinaryVortex no declara licencia y no debe reutilizarse sin permiso. [COMPLETAR: confirmar que no se ha copiado código de ningún repositorio.]

## 6. Tecnologías empleadas en la interfaz

| Tecnología | Uso | Documentación oficial |
|---|---|---|
| React | Componentes de la interfaz | https://react.dev |
| TypeScript | Tipado del frontend | https://www.typescriptlang.org |
| Vite | Herramienta de desarrollo y compilación (`npm run build`) | https://vite.dev |
| Vitest | Tests del frontend | https://vitest.dev |
| FastAPI | API que sirve la interfaz y el streaming | https://fastapi.tiangolo.com |
| Playwright | Capturas y comprobaciones en navegador durante el desarrollo | https://playwright.dev |
| esbuild | Compilación del `dist/` incluido en esta entrega | https://esbuild.github.io |

Dependencias del backend que afectan a la comunicación con el modelo: `httpx` (https://www.python-httpx.org), `tenacity` (https://tenacity.readthedocs.io) y `python-dotenv` (https://pypi.org/project/python-dotenv/).

## 7. Estándares web utilizados

| Tema | Aplicación | Referencia |
|---|---|---|
| Server-Sent Events | Streaming de la respuesta del agente | https://developer.mozilla.org/es/docs/Web/API/Server-sent_events |
| API Canvas 2D | Dibujo de la esfera | https://developer.mozilla.org/es/docs/Web/API/Canvas_API |
| `prefers-reduced-motion` | Desactivar animaciones si el sistema lo pide | https://developer.mozilla.org/es/docs/Web/CSS/@media/prefers-reduced-motion |
| `clip-path` | Esquinas biseladas | https://developer.mozilla.org/es/docs/Web/CSS/clip-path |
| Consultas de contenedor | Compactar el panel de datos del núcleo cuando el chat es estrecho | https://developer.mozilla.org/es/docs/Web/CSS/CSS_containment/Container_queries |
| Pautas de accesibilidad WCAG 2.2 | Contraste, movimiento reducido y etiquetas | https://www.w3.org/TR/WCAG22/ |

## 8. Notas sobre derechos de uso

- Las imágenes de referencia de la esfera las aportaron las personas autoras. No se reproducen ni se incluyen en el proyecto.
- Logo, esfera y piloto son diseños originales generados por código para este proyecto. La única fotografía del frontend es `fernando-alonso.jpg`, aportada por el equipo (ver sección 3 sobre su fuente y licencia). Las capturas de `nexo/docs/` son de la propia interfaz, pero anteriores al cambio de paleta a azul y violeta.
- El estado de mantenimiento, las licencias y las versiones de los repositorios pueden cambiar. Antes de incorporar código de cualquiera de ellos, hay que consultar su archivo `LICENSE` y su documentación vigente.
