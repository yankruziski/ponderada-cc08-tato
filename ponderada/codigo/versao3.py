# Arquivo: versao3.py
# Descrição: mesma ideia da versão 2, mas o produtor pega o mutex antes de
# esperar por uma posição vazia. A troca de ordem provoca o deadlock.

import threading
import time


N = 6
TOTAL_AMOSTRAS = 20_000
TEMPO_DO_WATCHDOG = 1.0


def calcular_resultado(recebidas, travou):
    """Recebe a lista consumida e o estado de trava; retorna as quatro métricas."""
    diferentes = set(recebidas)
    perdidas = TOTAL_AMOSTRAS - len(diferentes)
    duplicadas = len(recebidas) - len(diferentes)
    return len(recebidas), perdidas, duplicadas, travou


def executar():
    """Sem parâmetros; executa a ordem errada e retorna o estado após o watchdog."""
    buffer = [None] * N
    posicao_entrada = 0
    posicao_saida = 0
    recebidas = []

    vazio = threading.Semaphore(N)
    cheio = threading.Semaphore(0)
    mutex = threading.Semaphore(1)

    def produtor():
        """Produz as amostras adquirindo mutex antes de vazio de propósito."""
        nonlocal posicao_entrada

        for amostra in range(TOTAL_AMOSTRAS):
            # Aqui está a única mudança em relação à versão 2.
            # Quando o buffer enche, o produtor continua segurando o mutex
            # enquanto espera uma vaga que somente o consumidor pode liberar.
            mutex.acquire()
            vazio.acquire()

            buffer[posicao_entrada] = amostra
            posicao_entrada = (posicao_entrada + 1) % N

            mutex.release()
            cheio.release()

    def consumidor():
        """Tenta consumir normalmente, mas fica esperando o mutex do produtor."""
        nonlocal posicao_saida

        for _ in range(TOTAL_AMOSTRAS):
            cheio.acquire()
            mutex.acquire()

            amostra = buffer[posicao_saida]
            buffer[posicao_saida] = None
            posicao_saida = (posicao_saida + 1) % N

            mutex.release()
            vazio.release()
            recebidas.append(amostra)

    # As threads são daemon para o programa conseguir encerrar depois que o
    # watchdog comprovar o deadlock. Sem isso, o Python ficaria aberto esperando.
    sensor = threading.Thread(target=produtor, daemon=True)
    motor = threading.Thread(target=consumidor, daemon=True)
    sensor.start()

    # Dá tempo para o sensor encher as seis posições antes do motor começar.
    time.sleep(0.02)
    motor.start()

    time.sleep(TEMPO_DO_WATCHDOG)
    travou = sensor.is_alive() and motor.is_alive()
    return calcular_resultado(recebidas, travou)


def main():
    """Executa o teste e mostra o resultado no terminal."""
    consumidas, perdidas, duplicadas, travou = executar()
    print("Versão 3 - ordem mutex -> vazio")
    print(f"Amostras previstas: {TOTAL_AMOSTRAS} | Buffer: {N}")
    print(
        f"Consumidas: {consumidas} | Perdidas: {perdidas} | "
        f"Duplicadas: {duplicadas} | Travou: {'sim' if travou else 'não'}"
    )


if __name__ == "__main__":
    main()
