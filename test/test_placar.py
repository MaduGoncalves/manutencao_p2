"""
Suíte Completa e Definitiva de Testes Unitários - placarServer.py
Preserva todos os testes funcionais/HTTP e adiciona testes de precisão atômica
para zerar os mutantes SURVIVED no Cosmic Ray.

Execução (a partir da raiz do projeto):
    python -m unittest discover -s test -p "test_placar.py" -v
"""

import http.client
import importlib.util
import json
import os
import runpy
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

CAMINHO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "placarServer.py")
METODO_ACOES = "POST"


def carregar_modulo(nome="placarServer_teste"):
    """Carrega uma nova instância limpa do módulo."""
    spec = importlib.util.spec_from_file_location("placarServer", CAMINHO)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def texto_novo(texto):
    return "".join(list(texto))


# ==============================================================================
# 1. ESTADO INICIAL
# ==============================================================================
class TestEstadoInicial(unittest.TestCase):
    def test_estado_inicial_exato(self):
        m = carregar_modulo("placar_inicial")
        e = m.estado_partida
        self.assertEqual(e["pontos"], [0, 0])
        self.assertEqual(e["faltas"], [0, 0])
        self.assertEqual(e["tempo_restante_ms"], m.TEMPO_PADRAO_PARTIDA_MS)
        self.assertIs(e["em_andamento"], False)
        self.assertEqual(e["inicio_cronometro_ms"], 0)


# ==============================================================================
# 2. FUNÇÕES DE REGRA DE NEGÓCIO E TEMPO
# ==============================================================================
class TestFuncoesDePartida(unittest.TestCase):
    def setUp(self):
        self.m = carregar_modulo()
        self.m.reiniciar_partida()

    def test_reiniciar_restaura_tudo(self):
        e = self.m.estado_partida
        e["pontos"] = [5, 7]
        e["faltas"] = [2, 3]
        e["tempo_restante_ms"] = 123
        e["em_andamento"] = True
        e["inicio_cronometro_ms"] = 999
        self.m.reiniciar_partida()
        self.assertEqual(e["pontos"], [0, 0])
        self.assertEqual(e["faltas"], [0, 0])
        self.assertEqual(e["tempo_restante_ms"], self.m.TEMPO_PADRAO_PARTIDA_MS)
        self.assertIs(e["em_andamento"], False)
        self.assertEqual(e["inicio_cronometro_ms"], 0)

    def test_iniciar_com_1ms_restante_inicia(self):
        e = self.m.estado_partida
        e["tempo_restante_ms"] = 1
        with mock.patch.object(self.m, "obter_tempo_atual_ms", return_value=1000):
            self.m.iniciar_cronometro()
        self.assertIs(e["em_andamento"], True)
        self.assertEqual(e["inicio_cronometro_ms"], 1000)

    def test_iniciar_com_0ms_nao_inicia(self):
        e = self.m.estado_partida
        e["tempo_restante_ms"] = 0
        with mock.patch.object(self.m, "obter_tempo_atual_ms", return_value=1000):
            self.m.iniciar_cronometro()
        self.assertIs(e["em_andamento"], False)

    def test_iniciar_normal(self):
        with mock.patch.object(self.m, "obter_tempo_atual_ms", return_value=5000):
            self.m.iniciar_cronometro()
        self.assertIs(self.m.estado_partida["em_andamento"], True)
        self.assertEqual(self.m.estado_partida["inicio_cronometro_ms"], 5000)

    def test_tempo_esgotado_retorna_zero(self):
        e = self.m.estado_partida
        e["tempo_restante_ms"] = 1000
        e["em_andamento"] = True
        e["inicio_cronometro_ms"] = 0
        with mock.patch.object(self.m, "obter_tempo_atual_ms", return_value=5000):
            self.assertEqual(self.m.calcular_tempo_restante_cronometro(), 0)
        self.assertEqual(e["tempo_restante_ms"], 0)
        self.assertIs(e["em_andamento"], False)

    def test_tempo_exatamente_zero_encerra(self):
        e = self.m.estado_partida
        e["tempo_restante_ms"] = 1000
        e["em_andamento"] = True
        e["inicio_cronometro_ms"] = 0
        with mock.patch.object(self.m, "obter_tempo_atual_ms", return_value=1000):
            self.assertEqual(self.m.calcular_tempo_restante_cronometro(), 0)
        self.assertIs(e["em_andamento"], False)

    def test_definir_duracao_ignorada_com_cronometro_rodando(self):
        e = self.m.estado_partida
        e["em_andamento"] = True
        self.m.definir_duracao_partida(30)
        self.assertEqual(e["tempo_restante_ms"], self.m.TEMPO_PADRAO_PARTIDA_MS)

    def test_tempo_restante_parcial(self):
        e = self.m.estado_partida
        e["tempo_restante_ms"] = 10000
        e["em_andamento"] = True
        e["inicio_cronometro_ms"] = 0
        with mock.patch.object(self.m, "obter_tempo_atual_ms", return_value=3000):
            self.assertEqual(self.m.calcular_tempo_restante_cronometro(), 7000)

    def test_tempo_parado_retorna_valor_guardado(self):
        self.m.estado_partida["tempo_restante_ms"] = 4321
        self.assertEqual(self.m.calcular_tempo_restante_cronometro(), 4321)

    def test_definir_duracao_zero_e_aceito(self):
        self.m.definir_duracao_partida(0)
        self.assertEqual(self.m.estado_partida["tempo_restante_ms"], 0)

    def test_definir_duracao_negativa_nao_vira_negativa(self):
        self.m.definir_duracao_partida(-1)
        self.assertGreaterEqual(self.m.estado_partida["tempo_restante_ms"], 0)

    def test_definir_duracao_valida(self):
        self.m.definir_duracao_partida(60)
        self.assertEqual(self.m.estado_partida["tempo_restante_ms"], 60000)

    def test_pontos_e_faltas_nao_ficam_negativos(self):
        self.m.registrar_pontuacao(0, -1)
        self.m.registrar_falta(1, -1)
        self.assertEqual(self.m.estado_partida["pontos"], [0, 0])
        self.assertEqual(self.m.estado_partida["faltas"], [0, 0])

    def test_pontuacao_e_falta_acumulam(self):
        self.m.registrar_pontuacao(0, 3)
        self.m.registrar_pontuacao(1, 2)
        self.m.registrar_falta(0, 1)
        self.assertEqual(self.m.estado_partida["pontos"], [3, 2])
        self.assertEqual(self.m.estado_partida["faltas"], [1, 0])


# ==============================================================================
# 3. ELIMINAÇÃO TOTAL DOS MUTANTES SOBREVIVENTES
# ==============================================================================
class TestMatarTodosOsMutantesSobreviventes(unittest.TestCase):
    def setUp(self):
        self.m = carregar_modulo()
        self.m.reiniciar_partida()

    def test_matar_add_bitor_bitxor(self):
        """Mata Add_BitOr (0, 1) e Add_BitXor (0, 1).
        Entrada: 5 e 3. 5 + 3 = 8 (5 | 3 = 7, 5 ^ 3 = 6).
        """
        self.m.registrar_pontuacao(0, 5)
        self.m.registrar_pontuacao(0, 3)
        self.assertEqual(self.m.estado_partida["pontos"][0], 8)

        self.m.registrar_falta(1, 5)
        self.m.registrar_falta(1, 3)
        self.assertEqual(self.m.estado_partida["faltas"][1], 8)

    def test_matar_sub_mod(self):
        """Mata Sub_Mod (0).
        Entrada: 17000 e 5000. 17000 - 5000 = 12000 (17000 % 5000 = 2000).
        """
        self.m.estado_partida["tempo_restante_ms"] = 17000
        self.m.estado_partida["em_andamento"] = True
        self.m.estado_partida["inicio_cronometro_ms"] = 2000

        with mock.patch.object(self.m, "obter_tempo_atual_ms", return_value=7000):
            tempo = self.m.calcular_tempo_restante_cronometro()
            self.assertEqual(tempo, 12000)

    def test_matar_mul_e_div_operadores(self):
        """Mata Mul_Add, Mul_Sub, Mul_Div, Mul_FloorDiv, Mul_Mod, Mul_BitOr, Mul_BitXor."""
        # 7 segundos * 1000 = 7000 ms
        self.m.definir_duracao_partida(7)
        self.assertEqual(self.m.estado_partida["tempo_restante_ms"], 7000)

        if hasattr(self.m, "obter_tempo_restante_segundos"):
            self.m.estado_partida["tempo_restante_ms"] = 7500
            self.assertEqual(self.m.obter_tempo_restante_segundos(), 7.5)

    def test_matar_eq_is_isnot_e_desigualdades(self):
        """Mata Eq_NotEq, Eq_Lt, Eq_LtE, Eq_Gt, Eq_GtE, Eq_Is, Eq_IsNot nos índices de time."""
        # Validação estrita do time 0
        self.m.registrar_pontuacao(int(0), 2)
        self.assertEqual(self.m.estado_partida["pontos"], [2, 0])

        # Validação estrita do time 1
        self.m.registrar_pontuacao(int(1), 3)
        self.assertEqual(self.m.estado_partida["pontos"], [2, 3])

        # Faltas para os índices 0 e 1
        self.m.registrar_falta(int(0), 1)
        self.assertEqual(self.m.estado_partida["faltas"], [1, 0])

        self.m.registrar_falta(int(1), 1)
        self.assertEqual(self.m.estado_partida["faltas"], [1, 1])

    def test_matar_lt_noteq_e_lte_limites(self):
        """Mata Lt_NotEq e Lt_LtE testando limites de transição."""
        # Limite exato em 0
        self.m.definir_duracao_partida(0)
        self.assertEqual(self.m.estado_partida["tempo_restante_ms"], 0)

        # Valor positivo imediatamente acima
        self.m.definir_duracao_partida(1)
        self.assertEqual(self.m.estado_partida["tempo_restante_ms"], 1000)


# ==============================================================================
# 4. ROTAS E SERVIDOR HTTP
# ==============================================================================
class TestRotasHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = carregar_modulo("placar_http")
        cls.servidor = ThreadingHTTPServer(("127.0.0.1", 0), cls.m.manipuladorRequisicaoHTTP)
        cls.porta = cls.servidor.server_address[1]
        cls.thread = threading.Thread(target=cls.servidor.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()

    def setUp(self):
        self.m.reiniciar_partida()

    def req_completa(self, caminho, metodo=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.porta, timeout=5)
        conn.request(metodo or METODO_ACOES, caminho)
        resp = conn.getresponse()
        corpo = resp.read()
        cabecalhos = dict(resp.getheaders())
        conn.close()
        return resp.status, cabecalhos, corpo

    def req(self, caminho, metodo=None):
        return self.req_completa(caminho, metodo)[0]

    def test_post_api_retorna_json_do_estado(self):
        status, cab, corpo = self.req_completa("/api/partida/pontos/0/2", "POST")
        self.assertEqual(status, 200)
        self.assertEqual(cab["Content-Type"], "application/json")
        dados = json.loads(corpo)
        self.assertEqual(dados["pontos"], [2, 0])
        self.assertEqual(dados["faltas"], [0, 0])
        self.assertFalse(dados["em_andamento"])

    def test_get_api_nao_altera_estado(self):
        status, _, corpo = self.req_completa("/api/partida/pontos/0/2", "GET")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(corpo)["pontos"], [0, 0])

    def test_acao_desconhecida_400(self):
        self.assertEqual(self.req("/api/partida/inexistente"), 400)

    def test_pontos_ok_200_e_estado_alterado(self):
        self.assertEqual(self.req("/api/partida/pontos/0/2"), 200)
        self.assertEqual(self.m.estado_partida["pontos"], [2, 0])

    def test_pontos_time_b(self):
        self.assertEqual(self.req("/api/partida/pontos/1/3"), 200)
        self.assertEqual(self.m.estado_partida["pontos"], [0, 3])

    def test_query_string_e_ignorada(self):
        self.assertEqual(self.req("/api/partida/pontos/0/2?x=1"), 200)
        self.assertEqual(self.m.estado_partida["pontos"], [2, 0])

    def test_faltas_time_a(self):
        self.assertEqual(self.req("/api/partida/faltas/0/1"), 200)
        self.assertEqual(self.m.estado_partida["faltas"], [1, 0])

    def test_faltas_time_b(self):
        self.assertEqual(self.req("/api/partida/faltas/1/1"), 200)
        self.assertEqual(self.m.estado_partida["faltas"], [0, 1])

    def test_faltas_variacao_diferente_do_indice(self):
        self.assertEqual(self.req("/api/partida/faltas/0/2"), 200)
        self.assertEqual(self.m.estado_partida["faltas"], [2, 0])
        self.assertEqual(self.req("/api/partida/faltas/1/3"), 200)
        self.assertEqual(self.m.estado_partida["faltas"], [2, 3])

    def test_faltas_parametros_insuficientes_400(self):
        self.assertEqual(self.req("/api/partida/faltas/0"), 400)
        self.assertEqual(self.req("/api/partida/faltas"), 400)
        self.assertEqual(self.m.estado_partida["faltas"], [0, 0])

    def test_definir_tempo_valido(self):
        self.assertEqual(self.req("/api/partida/definir_tempo/90"), 200)
        self.assertEqual(self.m.estado_partida["tempo_restante_ms"], 90000)

    def test_definir_tempo_sem_parametro_400(self):
        self.assertEqual(self.req("/api/partida/definir_tempo"), 400)

    def test_pontos_parametros_insuficientes_400(self):
        self.assertEqual(self.req("/api/partida/pontos/0"), 400)

    def test_parametro_nao_numerico_400(self):
        self.assertEqual(self.req("/api/partida/pontos/a/b"), 400)

    def test_post_fora_da_api_404(self):
        self.assertEqual(self.req("/qualquer", "POST"), 404)

    def test_estatico_inexistente_404(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(self.m, "DIRETORIO_ARQUIVOS_ESTATICOS", Path(tmp).resolve()):
                self.assertEqual(self.req("/nao_existe.html", "GET"), 404)

    def test_estatico_fora_do_diretorio_404(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(self.m, "DIRETORIO_ARQUIVOS_ESTATICOS", Path(tmp).resolve()):
                self.assertEqual(self.req("/../placarServer.py", "GET"), 404)

    def test_estatico_index_200(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "index.html").write_bytes(b"<h1>placar</h1>")
            with mock.patch.object(self.m, "DIRETORIO_ARQUIVOS_ESTATICOS", Path(tmp).resolve()):
                status, cab, corpo = self.req_completa("/", "GET")
        self.assertEqual(status, 200)
        self.assertEqual(cab["Content-Type"], "text/html; charset=utf-8")
        self.assertEqual(corpo, b"<h1>placar</h1>")

    def test_erro_de_leitura_estatico_500(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "index.html").write_bytes(b"x")
            with mock.patch.object(self.m, "DIRETORIO_ARQUIVOS_ESTATICOS", Path(tmp).resolve()), \
                 mock.patch.object(Path, "read_bytes", side_effect=OSError("falha")):
                self.assertEqual(self.req("/", "GET"), 500)


# ==============================================================================
# 5. BLOCO MAIN
# ==============================================================================
class TestMain(unittest.TestCase):
    def test_servidor_sobe_em_0000_porta_8000(self):
        with mock.patch("http.server.ThreadingHTTPServer") as falso, mock.patch("builtins.print") as p:
            runpy.run_path(CAMINHO, run_name="__main__")
        endereco = falso.call_args[0][0]
        self.assertEqual(endereco, ("0.0.0.0", 8000))
        falso.return_value.serve_forever.assert_called_once()
        self.assertIn("8000", str(p.call_args))


# ==============================================================================
# 6. Matar os mutantes sobreviventes restantes (cobertura de código)
# ==============================================================================
class TestMatarMutantesRegrasDeTempo(unittest.TestCase):
    def setUp(self):
        self.m = carregar_modulo()
        self.m.reiniciar_partida()

    # Matar mutantes: NumberReplacer (10 -> 11/9 e 60 -> 61/59) e todos os Mul_* da linha 11
    def test_tempo_padrao_vale_600000_ms(self):
        self.assertEqual(self.m.MINUTOS_PADRAO_PARTIDA, 10)
        self.assertEqual(self.m.SEGUNDOS_POR_MINUTO, 60)
        self.assertEqual(self.m.TEMPO_PADRAO_PARTIDA_MS, 600000)
        self.assertEqual(self.m.estado_partida["tempo_restante_ms"], 600000)

    # Matar mutantes: todos os Mul_* da linha 39 (obter_tempo_atual_ms)
    def test_obter_tempo_atual_converte_segundos_em_ms(self):
        with mock.patch("time.time", return_value=1.5):
            self.assertEqual(self.m.obter_tempo_atual_ms(), 1500)

    # Matar mutante: ReplaceComparisonOperator_LtE_Eq da linha 90
    def test_iniciar_com_tempo_negativo_nao_inicia(self):
        e = self.m.estado_partida
        e["tempo_restante_ms"] = -5
        with mock.patch.object(self.m, "obter_tempo_atual_ms", return_value=1000):
            self.m.iniciar_cronometro()
        self.assertIs(e["em_andamento"], False)
        self.assertEqual(e["inicio_cronometro_ms"], 0)

    # Matar mutante: ReplaceFalseWithTrue #2 da linha 100 (pausar_cronometro)
    def test_pausar_congela_o_tempo_e_para_o_cronometro(self):
        e = self.m.estado_partida
        e["tempo_restante_ms"] = 10000
        e["em_andamento"] = True
        e["inicio_cronometro_ms"] = 0
        with mock.patch.object(self.m, "obter_tempo_atual_ms", return_value=3000):
            self.m.pausar_cronometro()
        self.assertEqual(e["tempo_restante_ms"], 7000)
        self.assertIs(e["em_andamento"], False)


class TestMatarMutantesRoteamento(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = carregar_modulo()
        cls.servidor = ThreadingHTTPServer(("127.0.0.1", 0), cls.m.manipuladorRequisicaoHTTP)
        cls.porta = cls.servidor.server_address[1]
        cls.thread = threading.Thread(target=cls.servidor.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()

    def setUp(self):
        self.m.reiniciar_partida()

    def req_completa(self, caminho, metodo="POST"):
        conn = http.client.HTTPConnection("127.0.0.1", self.porta, timeout=5)
        conn.request(metodo, caminho)
        resp = conn.getresponse()
        corpo = resp.read()
        cabecalhos = dict(resp.getheaders())
        conn.close()
        return resp.status, cabecalhos, corpo

    # Matar mutantes: Eq_Gt, Eq_GtE e Eq_Is das linhas 165 e 168 (acoes iniciar e pausar)
    def test_iniciar_e_pausar_via_http(self):
        with mock.patch.object(self.m, "obter_tempo_atual_ms", return_value=5000):
            status, _, corpo = self.req_completa("/api/partida/iniciar")
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(corpo)["em_andamento"])
        self.assertEqual(self.m.estado_partida["inicio_cronometro_ms"], 5000)

        with mock.patch.object(self.m, "obter_tempo_atual_ms", return_value=8000):
            status, _, corpo = self.req_completa("/api/partida/pausar")
        dados = json.loads(corpo)
        self.assertEqual(status, 200)
        self.assertFalse(dados["em_andamento"])
        self.assertEqual(dados["tempo_restante_ms"], 597000)

    # Matar mutantes: Eq_GtE das linhas 155, 160, 165, 168, 171 e 176, Eq_Gt e Eq_Is da linha 176
    def test_reiniciar_via_http(self):
        e = self.m.estado_partida
        e["pontos"] = [5, 7]
        e["faltas"] = [2, 3]
        e["tempo_restante_ms"] = 123
        status, _, _ = self.req_completa("/api/partida/reiniciar")
        self.assertEqual(status, 200)
        self.assertEqual(e["pontos"], [0, 0])
        self.assertEqual(e["faltas"], [0, 0])
        self.assertEqual(e["tempo_restante_ms"], 600000)
        self.assertIs(e["em_andamento"], False)

    # Matar mutantes: Eq_GtE da linha 176 (acao maior que "reiniciar" nao pode reiniciar)
    def test_acao_alfabeticamente_maior_nao_reinicia(self):
        self.m.estado_partida["pontos"] = [5, 7]
        status, _, _ = self.req_completa("/api/partida/zzz")
        self.assertEqual(status, 400)
        self.assertEqual(self.m.estado_partida["pontos"], [5, 7])

    # Matar mutantes: Eq_LtE e Eq_IsNot da linha 171 (acao menor que "definir_tempo" nao define tempo)
    def test_acao_alfabeticamente_menor_nao_define_tempo(self):
        status, _, _ = self.req_completa("/api/partida/abc/5")
        self.assertEqual(status, 400)
        self.assertEqual(self.m.estado_partida["tempo_restante_ms"], 600000)

    # Matar mutantes: Lt_NotEq das linhas 156, 161 e 172 (parametros alem do minimo)
    def test_parametros_extras_sao_aceitos(self):
        self.assertEqual(self.req_completa("/api/partida/pontos/0/2/extra")[0], 200)
        self.assertEqual(self.m.estado_partida["pontos"], [2, 0])
        self.assertEqual(self.req_completa("/api/partida/faltas/1/3/extra")[0], 200)
        self.assertEqual(self.m.estado_partida["faltas"], [0, 3])
        self.assertEqual(self.req_completa("/api/partida/definir_tempo/5/extra")[0], 200)
        self.assertEqual(self.m.estado_partida["tempo_restante_ms"], 5000)

    # Matar mutante: Eq_GtE da linha 228 (outro arquivo estatico nao pode virar index.html)
    def test_serve_arquivo_estatico_que_nao_e_o_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "index.html").write_bytes(b"idx")
            (Path(tmp) / "style.css").write_bytes(b"css")
            with mock.patch.object(self.m, "DIRETORIO_ARQUIVOS_ESTATICOS", Path(tmp).resolve()):
                status, cab, corpo = self.req_completa("/style.css", "GET")
        self.assertEqual(status, 200)
        self.assertEqual(cab["Content-Type"], "text/css; charset=utf-8")
        self.assertEqual(corpo, b"css")

    # Matar mutante: Eq_LtE da linha 228 (caminho menor que "/" nao pode virar index.html)
    def test_caminho_menor_que_barra_nao_serve_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "index.html").write_bytes(b"idx")
            with mock.patch.object(self.m, "DIRETORIO_ARQUIVOS_ESTATICOS", Path(tmp).resolve()):
                status, _, _ = self.req_completa("-x", "GET")
        self.assertEqual(status, 404)

    # Matar mutante: Eq_Is #6 da linha 228 (== "/" nao pode virar "is '/'")
    def test_raiz_igual_mas_nao_identica_serve_index(self):
        class StrNova(str):
            """Igual a '/', mas nunca o mesmo objeto que o literal '/'."""

        raiz = StrNova("/")
        self.assertEqual(raiz, "/")
        self.assertIsNot(raiz, "/")

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "index.html").write_bytes(b"<h1>idx</h1>")
            with mock.patch.object(self.m, "DIRETORIO_ARQUIVOS_ESTATICOS", Path(tmp).resolve()):
                handler = object.__new__(self.m.manipuladorRequisicaoHTTP)
                with mock.patch.object(handler, "enviar_resposta_http") as enviar:
                    handler.tratar_arquivo_estatico(raiz)

        enviar.assert_called_once_with(
            self.m.manipuladorRequisicaoHTTP.HTTP_STATUS_OK,
            b"<h1>idx</h1>",
            "text/html; charset=utf-8",
        )


class TestMatarMutantesBlocoMain(unittest.TestCase):
    # Matar mutante: Eq_LtE da linha 259 (nome de modulo menor que "__main__" nao sobe servidor)
    def test_nao_sobe_servidor_com_outro_nome_de_modulo(self):
        with mock.patch("http.server.ThreadingHTTPServer") as falso, mock.patch("builtins.print"):
            runpy.run_path(CAMINHO, run_name="Aplicacao")
        falso.assert_not_called()

    # Matar mutante: Eq_Is da linha 259 (comparacao por igualdade e nao por identidade)
    def test_sobe_servidor_com_nome_main_criado_em_tempo_de_execucao(self):
        with mock.patch("http.server.ThreadingHTTPServer") as falso, mock.patch("builtins.print"):
            runpy.run_path(CAMINHO, run_name=texto_novo("__main__"))
        falso.return_value.serve_forever.assert_called_once()


if __name__ == "__main__":
    unittest.main()
    