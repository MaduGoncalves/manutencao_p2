# Placar / Contador de Jogos (Python)

Dois times: soma/subtrai pontos, faltas, cronômetro regressivo
(iniciar, pausar, definir minutos) e reinício da partida.

- **Back-end:** Python 3.8+ usando só a biblioteca padrão (sem `pip install`).
- **Front-end:** HTML + CSS (Grid) + um pouco de JS, necessário para o cronômetro e os botões (`setInterval` + `fetch`).

## Como rodar

```bash
python app.py
```
(no Windows, se `python` não funcionar, tente `py app.py`)

Abra http://localhost:8000

## Estrutura

```
app.py            servidor + API + regras
static/index.html estrutura da tela
static/style.css  layout (Flexbox e Grid)
static/script.js  chamadas à API e relógio na tela
```

## API (`/api/q`)

| Método | Rota         | O que faz                                   |
|--------|--------------|---------------------------------------------|
| GET    | `/`          | Estado atual                                |
| POST   | `/p/{i}/{d}` | Soma `d` pontos ao time `i` (0 ou 1)        |
| POST   | `/f/{i}/{d}` | Soma `d` faltas ao time `i`                 |
| POST   | `/k`         | Inicia o cronômetro                         |
| POST   | `/l`         | Pausa                                       |
| POST   | `/m/{v}`     | Define o tempo em segundos (relógio parado) |
| POST   | `/n`         | Reinicia tudo                               |

## Mapa de nomes (de propósito pouco legíveis)

| Atual | Sugestão |
|-------|----------|
| `B` (dict) | `estado_partida` |
| `B["p"]`, `B["f"]` | `pontos`, `faltas` |
| `B["t"]` | `tempo_restante_ms` |
| `B["r"]` | `cronometro_rodando` |
| `B["s"]` | `inicio_cronometro_ms` |
| `K` | `TEMPO_PADRAO_MS` |
| `L` | `trava` |
| `w()` | `agora_ms()` |
| `g()` | `calcular_tempo_restante()` |
| `o()` | `estado_atual()` |
| `q(a)` | `executar_comando(partes)` |
| `H` | `ManipuladorHttp` |
| JS `z / y / h / d` | `chamarApi / definirMinutos / formatarTempo / renderizar` |
