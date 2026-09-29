# Placar / Contador de Jogos (Python + JavaScript)

Placar eletrônico para gerenciamento de partidas em tempo real com controle de pontuação, faltas e cronômetro regressivo.

## Funcionalidades

- **Controle de Pontuação e Faltas:** Adição e ajuste dinâmico para duas equipes (Time A e Time B).
- **Cronômetro Regressivo:** Controles de iniciar, pausar, definir tempo em minutos e reiniciar partida.
- **Sincronização Contínua:** Atualização automática entre o front-end e o servidor backend via polling HTTP.
- **Zero Dependências Externas:** Construído exclusivamente com bibliotecas nativas do Python e JavaScript Vanilla.

## Tecnologias

- **Back-end:** Python 3.8+ (usando apenas módulos nativos: `http.server`, `threading`, `time`, `pathlib`).
- **Front-end:** HTML5, CSS3 (Flexbox/Grid) e JavaScript ES6+ (`fetch` API e manipuladores de eventos).

## Estrutura do Projeto

```text
meu_placar/
├── server.py              # Servidor HTTP, roteamento e regras de negócio
└── static/                # Camada de apresentação e arquivos estáticos
    ├── index.html         # Estrutura e marcação da interface
    ├── style.css          # Estilização e layout (Flexbox e Grid)
    └── app.js             # Comunicação com a API e atualização da UI