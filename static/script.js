// Constante da URL Base da API (UPPER_SNAKE_CASE)
const ROTA_BASE_API = '/api/partida';

// Formata o tempo restante de milissegundos para MM:SS
function formatarTempoMilissegundos(milissegundos) {
    const totalSegundos = Math.ceil(milissegundos / 1000);
    const minutos = String(Math.floor(totalSegundos / 60)).padStart(2, '0');
    const segundos = String(totalSegundos % 60).padStart(2, '0');
    return `${minutos}:${segundos}`;
}

// Atualiza a interface com os dados recebidos da API
function atualizarInterface(dadosPartida) {
    document.getElementById('pontos-time-a').textContent = dadosPartida.pontos[0];
    document.getElementById('pontos-time-b').textContent = dadosPartida.pontos[1];
    document.getElementById('faltas-time-a').textContent = dadosPartida.faltas[0];
    document.getElementById('faltas-time-b').textContent = dadosPartida.faltas[1];

    const elementoCronometro = document.getElementById('display-cronometro');
    elementoCronometro.textContent = formatarTempoMilissegundos(dadosPartida.tempo_restante_ms);
    elementoCronometro.classList.toggle('tempo-esgotado', dadosPartida.tempo_restante_ms === 0);
}

// Envia comandos HTTP para o backend (GET por padrão, POST quando há rota de ação)
async function enviarComando(caminhoComando = '') {
    try {
        const metodoHttp = caminhoComando ? 'POST' : 'GET';
        const resposta = await fetch(ROTA_BASE_API + caminhoComando, { method: metodoHttp });

        if (resposta.ok) {
            const dadosPartida = await resposta.json();
            atualizarInterface(dadosPartida);
        }
    } catch (erro) {
        console.error('Erro de comunicação com o servidor:', erro);
    }
}

// Converte o valor digitado de minutos para segundos e envia ao backend
function definirTempoPartida() {
    const campoMinutos = document.getElementById('campo-minutos');
    const minutosDigitados = parseFloat(campoMinutos.value);

    if (!isNaN(minutosDigitados) && minutosDigitados >= 0) {
        const segundosTotais = Math.round(minutosDigitados * 60);
        enviarComando('/definir_tempo/' + segundosTotais);
    }
}

// Inicialização e sincronização periódica (polling a cada 500ms)
enviarComando();
setInterval(() => enviarComando(), 500);