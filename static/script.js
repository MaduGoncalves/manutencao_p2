// Constantes Globais de Roteamento e Equipes 
const ROTA_BASE_API = '/api/partida';
const INDICE_EQUIPE_A = 0;
const INDICE_EQUIPE_B = 1;
const INTERVALO_SINCRONIZACAO_MS = 500;

// Formata o tempo restante do cronômetro para a exibição no formato MM:SS
function formatar_tempo_cronometro(tempo_restante_ms) {
    const MILISSEGUNDOS_POR_SEGUNDO = 1000;
    const SEGUNDOS_POR_MINUTO = 60;
    const TAMANHO_FORMATO_DIGITOS = 2;
    const CARACTERE_PREENCHIMENTO = '0';

    const total_segundos = Math.ceil(tempo_restante_ms / MILISSEGUNDOS_POR_SEGUNDO);
    const minutos = String(Math.floor(total_segundos / SEGUNDOS_POR_MINUTO)).padStart(
        TAMANHO_FORMATO_DIGITOS, 
        CARACTERE_PREENCHIMENTO
    );
    const segundos = String(total_segundos % SEGUNDOS_POR_MINUTO).padStart(
        TAMANHO_FORMATO_DIGITOS, 
        CARACTERE_PREENCHIMENTO
    );
    return `${minutos}:${segundos}`;
}

// Atualiza as pontuações e faltas dos times
function atualizar_marcadores_equipes(estado_partida) {
    document.getElementById('pontos-time-a').textContent = estado_partida.pontos[INDICE_EQUIPE_A];
    document.getElementById('pontos-time-b').textContent = estado_partida.pontos[INDICE_EQUIPE_B];
    document.getElementById('faltas-time-a').textContent = estado_partida.faltas[INDICE_EQUIPE_A];
    document.getElementById('faltas-time-b').textContent = estado_partida.faltas[INDICE_EQUIPE_B];
}

// Atualiza especificamente a exibição do cronômetro da partida
function atualizar_display_cronometro(tempo_restante_ms) {
    const TEMPO_ESGOTADO_MS = 0;
    const display_cronometro = document.getElementById('display-cronometro');

    display_cronometro.textContent = formatar_tempo_cronometro(tempo_restante_ms);
    display_cronometro.classList.toggle('tempo-esgotado', tempo_restante_ms === TEMPO_ESGOTADO_MS);
}

// Atualiza placar
function atualizar_placar_partida(estado_partida) {
    atualizar_marcadores_equipes(estado_partida);
    atualizar_display_cronometro(estado_partida.tempo_restante_ms);
}

// Função responsável pela comunicação entre front-end e o servidor Python, através de requisições HTTP assíncronas
async function enviar_requisicao_partida(rota_acao = '') {
    try {
        const metodo_http = rota_acao ? 'POST' : 'GET';
        const resposta = await fetch(ROTA_BASE_API + rota_acao, { method: metodo_http });

        if (!resposta.ok) {
            throw new Error(`Erro na resposta da API (${resposta.status}): ${resposta.statusText}`);
        }

        const estado_partida = await resposta.json();
        atualizar_placar_partida(estado_partida);
    } catch (erro) {
        console.error('[FALHA DE SINCRONIZAÇÃO]', erro.message);
    }
}

// Ajustar o tempo total da partida com base no valor que o operador digitar na tela.
function definir_duracao_partida() {
    const MINUTOS_MINIMOS = 0;
    const SEGUNDOS_POR_MINUTO = 60;

    const campo_minutos = document.getElementById('campo-minutos');
    const duracao_minutos = parseFloat(campo_minutos?.value);

    if (isNaN(duracao_minutos) || duracao_minutos < MINUTOS_MINIMOS) {
        return;
    }

    const duracao_segundos = Math.round(duracao_minutos * SEGUNDOS_POR_MINUTO);
    enviar_requisicao_partida('/definir_tempo/' + duracao_segundos);
}

// Solicita confirmação antes de reiniciar o cronoêmtro 
function solicitar_reiniciar_partida() {
    if (!confirm('Reiniciar partida?')) {
        return;
    }
    enviar_requisicao_partida('/reiniciar');
}

// Vincula eventos aos botões de ação dinâmica (pontos e faltas)
function configurar_botoes_acao() {
    document.querySelectorAll('.btn-acao').forEach(botao_acao => {
        botao_acao.addEventListener('click', () => {
            const { tipo: acao, time: equipe, valor } = botao_acao.dataset;
            if (!acao || !equipe || !valor) return;
            
            enviar_requisicao_partida(`/${acao}/${equipe}/${valor}`);
        });
    });
}

// Vincula eventos de controle do painel principal
function configurar_painel_controle() {
    document.getElementById('btn-iniciar')?.addEventListener('click', () => enviar_requisicao_partida('/iniciar'));
    document.getElementById('btn-pausar')?.addEventListener('click', () => enviar_requisicao_partida('/pausar'));
    document.getElementById('btn-definir-tempo')?.addEventListener('click', definir_duracao_partida);
    document.getElementById('btn-reiniciar')?.addEventListener('click', solicitar_reiniciar_partida);
}

// Inicia o ciclo de polling para sincronização contínua
function iniciar_sincronizacao_periodica() {
    enviar_requisicao_partida();
    setInterval(() => enviar_requisicao_partida(), INTERVALO_SINCRONIZACAO_MS);
}

// Inicialização dos componentes na carga do DOM
document.addEventListener('DOMContentLoaded', () => {
    configurar_botoes_acao();
    configurar_painel_controle();
    iniciar_sincronizacao_periodica();
});