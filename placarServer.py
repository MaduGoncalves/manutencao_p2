import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Constantes (UPPER_SNAKE_CASE)
TEMPO_PADRAO_PARTIDA_MS = 600000  # 10 minutos em milissegundos
TRAVA_SINCRONIZACAO = threading.Lock()
DIRETORIO_ARQUIVOS_ESTATICOS = Path(__file__).parent / "static"
TIPOS_MIME_SUPORTADOS = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
}

# Estado global da partida (snake_case)
estado_partida = {
    "pontos": [0, 0],
    "faltas": [0, 0],
    "tempo_restante_ms": TEMPO_PADRAO_PARTIDA_MS,
    "em_andamento": False,
    "inicio_cronometro_ms": 0,
}


def obter_tempo_atual_ms():
    """Retorna o timestamp atual em milissegundos."""
    return int(time.time() * 1000)


def calcular_tempo_restante_ms():
    """Calcula o tempo restante do cronômetro da partida."""
    if estado_partida["em_andamento"]:
        tempo_decorrido = obter_tempo_atual_ms() - estado_partida["inicio_cronometro_ms"]
        tempo_restante = estado_partida["tempo_restante_ms"] - tempo_decorrido
        if tempo_restante <= 0:
            estado_partida["tempo_restante_ms"] = 0
            estado_partida["em_andamento"] = False
            return 0
        return tempo_restante
    return estado_partida["tempo_restante_ms"]


def gerar_json_estado_partida():
    """Monta manualmente a string no formato JSON sem usar a biblioteca json."""
    pontos_time_a = estado_partida["pontos"][0]
    pontos_time_b = estado_partida["pontos"][1]
    faltas_time_a = estado_partida["faltas"][0]
    faltas_time_b = estado_partida["faltas"][1]
    tempo_restante = calcular_tempo_restante_ms()
    em_andamento_texto = "true" if estado_partida["em_andamento"] else "false"

    return (
        f'{{"pontos": [{pontos_time_a}, {pontos_time_b}], '
        f'"faltas": [{faltas_time_a}, {faltas_time_b}], '
        f'"tempo_restante_ms": {tempo_restante}, '
        f'"em_andamento": {em_andamento_texto}}}'
    )


def executar_comando_partida(parametros):
    """Processa comandos descritivos recebidos na URL."""
    tipo_comando = parametros[0] if parametros else ""
    try:
        if tipo_comando in ("pontos", "faltas"):
            indice_time = int(parametros[1])
            variacao = int(parametros[2])

            if indice_time in (0, 1):
                valor_atual = estado_partida[tipo_comando][indice_time]
                estado_partida[tipo_comando][indice_time] = max(0, valor_atual + variacao)

        elif tipo_comando == "iniciar":
            if not estado_partida["em_andamento"] and calcular_tempo_restante_ms() > 0:
                estado_partida["inicio_cronometro_ms"] = obter_tempo_atual_ms()
                estado_partida["em_andamento"] = True

        elif tipo_comando == "pausar":
            estado_partida["tempo_restante_ms"] = calcular_tempo_restante_ms()
            estado_partida["em_andamento"] = False

        elif tipo_comando == "definir_tempo":
            tempo_em_segundos = int(parametros[1])
            if not estado_partida["em_andamento"] and tempo_em_segundos >= 0:
                estado_partida["tempo_restante_ms"] = tempo_em_segundos * 1000

        elif tipo_comando == "reiniciar":
            estado_partida["pontos"] = [0, 0]
            estado_partida["faltas"] = [0, 0]
            estado_partida["tempo_restante_ms"] = TEMPO_PADRAO_PARTIDA_MS
            estado_partida["em_andamento"] = False
            estado_partida["inicio_cronometro_ms"] = 0

    except (IndexError, ValueError):
        pass


class manipuladorRequisicaoHTTP(BaseHTTPRequestHandler):
    """Servidor HTTP e API para o placar eletrônico (nome da classe em camelCase)."""

    def enviar_resposta_http(self, codigo_status, corpo_resposta, tipo_conteudo):
        self.send_response(codigo_status)
        self.send_header("Content-Type", tipo_conteudo)
        self.send_header("Content-Length", str(len(corpo_resposta)))
        self.end_headers()
        self.wfile.write(corpo_resposta)

    def processar_requisicao(self, eh_metodo_post):
        caminho_url = self.path.split("?")[0]

        # Rota da API
        if caminho_url.startswith("/api/partida"):
            with TRAVA_SINCRONIZACAO:
                if eh_metodo_post:
                    # Rota tratada: /api/partida/<comando>/<param1>/<param2>
                    partes_comando = [
                        segmento for segmento in caminho_url[12:].split("/") if segmento
                    ]
                    executar_comando_partida(partes_comando)
                corpo_json = gerar_json_estado_partida()
            return self.enviar_resposta_http(
                200, corpo_json.encode("utf-8"), "application/json"
            )

        if eh_metodo_post:
            return self.enviar_resposta_http(404, b"", "text/plain")

        # Rota de Arquivos Estáticos
        nome_arquivo = "index.html" if caminho_url == "/" else caminho_url.lstrip("/")
        caminho_arquivo = (DIRETORIO_ARQUIVOS_ESTATICOS / nome_arquivo).resolve()

        if (
            DIRETORIO_ARQUIVOS_ESTATICOS.resolve() in caminho_arquivo.parents
            and caminho_arquivo.is_file()
        ):
            tipo_mime = TIPOS_MIME_SUPORTADOS.get(caminho_arquivo.suffix, "text/plain")
            return self.enviar_resposta_http(200, caminho_arquivo.read_bytes(), tipo_mime)

        return self.enviar_resposta_http(404, b"nao encontrado", "text/plain")

    def do_GET(self):
        self.processar_requisicao(eh_metodo_post=False)

    def do_POST(self):
        self.processar_requisicao(eh_metodo_post=True)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print("Rodando em http://localhost:8000")
    ThreadingHTTPServer(("0.0.0.0", 8000), manipuladorRequisicaoHTTP).serve_forever()