import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Constantes Globais de Tempo e Equipes
MILISSEGUNDOS_POR_SEGUNDO = 1000
MINUTOS_PADRAO_PARTIDA = 10
SEGUNDOS_POR_MINUTO = 60
TEMPO_PADRAO_PARTIDA_MS = (
    MINUTOS_PADRAO_PARTIDA * SEGUNDOS_POR_MINUTO * MILISSEGUNDOS_POR_SEGUNDO
)

INDICE_TIME_A = 0
INDICE_TIME_B = 1

TRAVA_SINCRONIZACAO = threading.Lock()
DIRETORIO_ARQUIVOS_ESTATICOS = Path(__file__).parent / "static"
TIPOS_MIME_SUPORTADOS = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
}

# Estado Global da Partida
estado_partida = {
    "pontos": [0, 0],
    "faltas": [0, 0],
    "tempo_restante_ms": TEMPO_PADRAO_PARTIDA_MS,
    "em_andamento": False,
    "inicio_cronometro_ms": 0,
}


# --- REGRAS E AÇÕES DO DOMÍNIO  ---

def obter_tempo_atual_ms():
    """Retorna o timestamp atual em milissegundos."""
    return int(time.time() * MILISSEGUNDOS_POR_SEGUNDO)


def calcular_tempo_restante_cronometro():
    """Calcula o tempo restante no cronômetro da partida."""
    TEMPO_ESGOTADO_MS = 0

    if not estado_partida["em_andamento"]:
        return estado_partida["tempo_restante_ms"]

    tempo_decorrido = obter_tempo_atual_ms() - estado_partida["inicio_cronometro_ms"]
    tempo_restante = estado_partida["tempo_restante_ms"] - tempo_decorrido

    if tempo_restante <= TEMPO_ESGOTADO_MS:
        estado_partida["tempo_restante_ms"] = TEMPO_ESGOTADO_MS
        estado_partida["em_andamento"] = False
        return TEMPO_ESGOTADO_MS

    return tempo_restante


def registrar_pontuacao(indice_equipe, variacao_pontos):
    """Registra a variação de pontos mantendo o comportamento dentro do fluxo normal."""
    VALOR_MINIMO_PONTOS = 0

    if indice_equipe not in (INDICE_TIME_A, INDICE_TIME_B):
        return

    pontos_atuais = estado_partida["pontos"][indice_equipe]
    estado_partida["pontos"][indice_equipe] = max(
        VALOR_MINIMO_PONTOS, pontos_atuais + variacao_pontos
    )


def registrar_falta(indice_equipe, variacao_faltas):
    """Registra a variação de faltas mantendo o comportamento dentro do fluxo normal."""
    VALOR_MINIMO_FALTAS = 0

    if indice_equipe not in (INDICE_TIME_A, INDICE_TIME_B):
        return

    faltas_atuais = estado_partida["faltas"][indice_equipe]
    estado_partida["faltas"][indice_equipe] = max(
        VALOR_MINIMO_FALTAS, faltas_atuais + variacao_faltas
    )


def iniciar_cronometro():
    """Inicia o cronômetro da partida."""
    if estado_partida["em_andamento"]:
        return
    if calcular_tempo_restante_cronometro() <= 0:
        return

    estado_partida["inicio_cronometro_ms"] = obter_tempo_atual_ms()
    estado_partida["em_andamento"] = True


def pausar_cronometro():
    """Pausa a contagem do tempo conservando a marcação atual."""
    estado_partida["tempo_restante_ms"] = calcular_tempo_restante_cronometro()
    estado_partida["em_andamento"] = False


def definir_duracao_partida(tempo_em_segundos):
    """Define a duração da partida."""
    TEMPO_MINIMO_SEGUNDOS = 0

    if estado_partida["em_andamento"]:
        return
    if tempo_em_segundos < TEMPO_MINIMO_SEGUNDOS:
        return

    estado_partida["tempo_restante_ms"] = tempo_em_segundos * MILISSEGUNDOS_POR_SEGUNDO


def reiniciar_partida():
    """Restaura o estado inicial da partida."""
    estado_partida["pontos"] = [0, 0]
    estado_partida["faltas"] = [0, 0]
    estado_partida["tempo_restante_ms"] = TEMPO_PADRAO_PARTIDA_MS
    estado_partida["em_andamento"] = False
    estado_partida["inicio_cronometro_ms"] = 0


def gerar_json_estado_partida():
    """Serializa o estado atual da partida em formato JSON."""
    pontos_time_a = estado_partida["pontos"][INDICE_TIME_A]
    pontos_time_b = estado_partida["pontos"][INDICE_TIME_B]
    faltas_time_a = estado_partida["faltas"][INDICE_TIME_A]
    faltas_time_b = estado_partida["faltas"][INDICE_TIME_B]
    tempo_restante = calcular_tempo_restante_cronometro()
    em_andamento_texto = "true" if estado_partida["em_andamento"] else "false"

    return (
        f'{{"pontos": [{pontos_time_a}, {pontos_time_b}], '
        f'"faltas": [{faltas_time_a}, {faltas_time_b}], '
        f'"tempo_restante_ms": {tempo_restante}, '
        f'"em_andamento": {em_andamento_texto}}}'
    )


# --- INFRAESTRUTURA E ROTEAMENTO HTTP  ---

def extrair_segmentos_rota(caminho_url, prefixo):
    """Extrai os segmentos da URL em uma lista limpa."""
    return [seg for seg in caminho_url[len(prefixo):].split("/") if seg]


def processar_comando_partida(parametros_rota):
    """Valida entradas e mapeia ações. Lança ValueError para entradas excepcionais/inválidas."""
    if not parametros_rota:
        return

    acao = parametros_rota[0]

    if acao == "pontos":
        if len(parametros_rota) < 3:
            raise ValueError("Parâmetros insuficientes para registrar pontuação.")
        return registrar_pontuacao(int(parametros_rota[1]), int(parametros_rota[2]))

    if acao == "faltas":
        if len(parametros_rota) < 3:
            raise ValueError("Parâmetros insuficientes para registrar falta.")
        return registrar_falta(int(parametros_rota[1]), int(parametros_rota[2]))

    if acao == "iniciar":
        return iniciar_cronometro()

    if acao == "pausar":
        return pausar_cronometro()

    if acao == "definir_tempo":
        if len(parametros_rota) < 2:
            raise ValueError("Parâmetro de tempo ausente.")
        return definir_duracao_partida(int(parametros_rota[1]))

    if acao == "reiniciar":
        return reiniciar_partida()

    raise ValueError(f"Ação desconhecida solicitada: '{acao}'")


class manipuladorRequisicaoHTTP(BaseHTTPRequestHandler):
    """Servidor web com separação explícita do fluxo feliz (try) e exceções (except)."""

    HTTP_STATUS_OK = 200
    HTTP_STATUS_BAD_REQUEST = 400
    HTTP_STATUS_NOT_FOUND = 404
    HTTP_STATUS_INTERNAL_ERROR = 500
    PREFIXO_ROTA_API = "/api/partida"

    def enviar_resposta_http(self, codigo_status, corpo_resposta, tipo_conteudo):
        self.send_response(codigo_status)
        self.send_header("Content-Type", tipo_conteudo)
        self.send_header("Content-Length", str(len(corpo_resposta)))
        self.end_headers()
        self.wfile.write(corpo_resposta)

    def processar_requisicao(self, eh_metodo_post):
        caminho_url = self.path.split("?")[0]

        if caminho_url.startswith(self.PREFIXO_ROTA_API):
            return self.tratar_requisicao_api(caminho_url, eh_metodo_post)

        if eh_metodo_post:
            return self.enviar_resposta_http(self.HTTP_STATUS_NOT_FOUND, b"", "text/plain")

        return self.tratar_arquivo_estatico(caminho_url)

    def tratar_requisicao_api(self, caminho_url, eh_metodo_post):
        try:
            with TRAVA_SINCRONIZACAO:
                if eh_metodo_post:
                    partes = extrair_segmentos_rota(caminho_url, self.PREFIXO_ROTA_API)
                    processar_comando_partida(partes)
                corpo_json = gerar_json_estado_partida()

            return self.enviar_resposta_http(
                self.HTTP_STATUS_OK, corpo_json.encode("utf-8"), "application/json"
            )

        except ValueError as erro_parametro:
            print(f"[LOG ALERTA] Requisição API inválida: {erro_parametro}")
            return self.enviar_resposta_http(
                self.HTTP_STATUS_BAD_REQUEST, b"Requisicao invalida", "text/plain"
            )

    def tratar_arquivo_estatico(self, caminho_url):
        nome_arquivo = "index.html" if caminho_url == "/" else caminho_url.lstrip("/")
        caminho_arquivo = (DIRETORIO_ARQUIVOS_ESTATICOS / nome_arquivo).resolve()

        if not self.eh_caminho_estatico_valido(caminho_arquivo):
            return self.enviar_resposta_http(self.HTTP_STATUS_NOT_FOUND, b"nao encontrado", "text/plain")

        try:
            conteudo_arquivo = caminho_arquivo.read_bytes()
            tipo_mime = TIPOS_MIME_SUPORTADOS.get(caminho_arquivo.suffix, "text/plain")
            return self.enviar_resposta_http(self.HTTP_STATUS_OK, conteudo_arquivo, tipo_mime)

        except OSError as erro_io:
            print(f"[LOG ERRO] Falha ao ler arquivo estático no disco: {erro_io}")
            return self.enviar_resposta_http(
                self.HTTP_STATUS_INTERNAL_ERROR, b"Erro interno do servidor", "text/plain"
            )

    def eh_caminho_estatico_valido(self, caminho_arquivo):
        diretorio_base = DIRETORIO_ARQUIVOS_ESTATICOS.resolve()
        return diretorio_base in caminho_arquivo.parents and caminho_arquivo.is_file()

    def do_GET(self):
        self.processar_requisicao(eh_metodo_post=False)

    def do_POST(self):
        self.processar_requisicao(eh_metodo_post=True)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    HOST_SERVIDOR = "0.0.0.0"
    PORTA_SERVIDOR = 8000

    print(f"Rodando em http://localhost:{PORTA_SERVIDOR}")
    ThreadingHTTPServer((HOST_SERVIDOR, PORTA_SERVIDOR), manipuladorRequisicaoHTTP).serve_forever()