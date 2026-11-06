# Arquivo: versao1.py
# Descrição: buffer circular sem sincronização. Esta versão foi feita para
# mostrar a condição de corrida entre a thread do sensor e a do motor.

import threading
import time


N = 6
TOTAL_AMOSTRAS = 20_000
LIMITE_ESPERA = 1.0


def calcular_resultado(recebidas, travou):
    """Recebe a lista consumida e o estado de trava; retorna as quatro métricas."""
    diferentes = set(recebidas)
    perdidas = TOTAL_AMOSTRAS - len(diferentes)
    duplicadas = len(recebidas) - len(diferentes)
    return len(recebidas), perdidas, duplicadas, travou


def executar():
    """Sem parâmetros; roda as threads sem proteção e retorna as quatro métricas."""
    buffer = [None] * N
    posicao_entrada = 0
    posicao_saida = 0
    ocupadas = 0
    recebidas = []
    parar = threading.Event()
    travou = False

    def produtor():
        """Produz as amostras de 0 até 19.999 e tenta colocá-las no buffer."""
        nonlocal posicao_entrada, ocupadas

        for amostra in range(TOTAL_AMOSTRAS):
            # Espera ocupada: o produtor consulta o contador até surgir uma
            # posição. Não há semáforo nem lock nesta versão.
            while ocupadas >= N and not parar.is_set():
                time.sleep(0)

            if parar.is_set():
                return

            buffer[posicao_entrada] = amostra
            posicao_entrada = (posicao_entrada + 1) % N

            # Esta é uma parte da região crítica. Se o consumidor rodar depois
            # da leitura e antes da escrita, uma das atualizações será perdida.
            valor_atual = ocupadas
            time.sleep(0)
            ocupadas = valor_atual + 1

    def consumidor():
        """Consome amostras e para se ficar um segundo sem receber nada."""
        nonlocal posicao_saida, ocupadas, travou
        ultimo_recebimento = time.monotonic()

        while len(recebidas) < TOTAL_AMOSTRAS and not parar.is_set():
            if ocupadas <= 0:
                if time.monotonic() - ultimo_recebimento >= LIMITE_ESPERA:
                    travou = True
                    parar.set()
                    return
                time.sleep(0)
                continue

            amostra = buffer[posicao_saida]
            buffer[posicao_saida] = None
            posicao_saida = (posicao_saida + 1) % N

            # O sleep(0) força a troca de thread no pior ponto possível.
            valor_atual = ocupadas
            time.sleep(0)
            ocupadas = valor_atual - 1

            if amostra is not None:
                recebidas.append(amostra)
                ultimo_recebimento = time.monotonic()

    sensor = threading.Thread(target=produtor)
    motor = threading.Thread(target=consumidor)
    sensor.start()
    motor.start()
    sensor.join(timeout=10)
    motor.join(timeout=10)

    # É uma segunda segurança para o programa não ficar aberto para sempre.
    if sensor.is_alive() or motor.is_alive():
        travou = True
        parar.set()
        sensor.join(timeout=1)
        motor.join(timeout=1)

    return calcular_resultado(recebidas, travou)


def main():
    """Executa o teste e mostra o resultado no terminal."""
    consumidas, perdidas, duplicadas, travou = executar()
    print("Versão 1 - sem sincronização")
    print(f"Amostras previstas: {TOTAL_AMOSTRAS} | Buffer: {N}")
    print(
        f"Consumidas: {consumidas} | Perdidas: {perdidas} | "
        f"Duplicadas: {duplicadas} | Travou: {'sim' if travou else 'não'}"
    )


if __name__ == "__main__":
    main()
