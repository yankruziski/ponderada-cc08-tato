# Arquivo: versao2.py
# Descrição: solução do produtor/consumidor usando os semáforos vazio, cheio
# e mutex para proteger um buffer circular de seis posições.

import threading


N = 6
TOTAL_AMOSTRAS = 20_000


def calcular_resultado(recebidas, travou):
    """Recebe a lista consumida e o estado de trava; retorna as quatro métricas."""
    diferentes = set(recebidas)
    perdidas = TOTAL_AMOSTRAS - len(diferentes)
    duplicadas = len(recebidas) - len(diferentes)
    return len(recebidas), perdidas, duplicadas, travou


def executar():
    """Sem parâmetros; roda as threads com semáforos e retorna as quatro métricas."""
    buffer = [None] * N
    posicao_entrada = 0
    posicao_saida = 0
    recebidas = []

    # vazio conta quantas posições ainda podem ser usadas.
    # cheio conta quantas posições já têm uma amostra pronta.
    # mutex permite que apenas uma thread mexa no buffer de cada vez.
    vazio = threading.Semaphore(N)
    cheio = threading.Semaphore(0)
    mutex = threading.Semaphore(1)

    def produtor():
        """Produz 20.000 amostras, esperando uma posição livre para cada uma."""
        nonlocal posicao_entrada

        for amostra in range(TOTAL_AMOSTRAS):
            vazio.acquire()
            mutex.acquire()

            # Começo da região crítica do produtor.
            buffer[posicao_entrada] = amostra
            posicao_entrada = (posicao_entrada + 1) % N
            # Fim da região crítica.

            mutex.release()
            cheio.release()

    def consumidor():
        """Retira do buffer a mesma quantidade de amostras produzida."""
        nonlocal posicao_saida

        for _ in range(TOTAL_AMOSTRAS):
            cheio.acquire()
            mutex.acquire()

            # Começo da região crítica do consumidor.
            amostra = buffer[posicao_saida]
            buffer[posicao_saida] = None
            posicao_saida = (posicao_saida + 1) % N
            # Fim da região crítica.

            mutex.release()
            vazio.release()
            recebidas.append(amostra)

    sensor = threading.Thread(target=produtor)
    motor = threading.Thread(target=consumidor)
    sensor.start()
    motor.start()
    sensor.join(timeout=10)
    motor.join(timeout=10)

    travou = sensor.is_alive() or motor.is_alive()
    return calcular_resultado(recebidas, travou)


def main():
    """Executa o teste e mostra o resultado no terminal."""
    consumidas, perdidas, duplicadas, travou = executar()
    print("Versão 2 - três semáforos")
    print(f"Amostras previstas: {TOTAL_AMOSTRAS} | Buffer: {N}")
    print(
        f"Consumidas: {consumidas} | Perdidas: {perdidas} | "
        f"Duplicadas: {duplicadas} | Travou: {'sim' if travou else 'não'}"
    )


if __name__ == "__main__":
    main()
