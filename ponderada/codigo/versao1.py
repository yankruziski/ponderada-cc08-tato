"""Versão 1: produtor/consumidor com espera ocupada e sem sincronização.

O programa força uma troca de contexto entre a leitura e a escrita do contador
compartilhado para tornar a condição de corrida observável.
"""

from __future__ import annotations

import argparse
import threading
import time
from collections import Counter
from dataclasses import dataclass


TOTAL_PADRAO = 20_000
N_PADRAO = 6
TIMEOUT = 1.0


@dataclass
class Resultado:
    """Armazena as métricas finais de uma execução.

    Attributes:
        consumidas: Quantidade total de leituras válidas feitas pelo consumidor.
        perdidas: Amostras esperadas que não apareceram nenhuma vez.
        duplicadas: Leituras extras de números que já haviam sido consumidos.
        travou: Indica se o consumidor ficou um segundo sem receber uma amostra.
    """

    consumidas: int
    perdidas: int
    duplicadas: int
    travou: bool


def executar(total: int, tamanho: int) -> Resultado:
    """Executa a versão sem sincronização.

    Args:
        total: Número de amostras que o produtor deve gerar.
        tamanho: Número de posições do buffer circular.

    Returns:
        Métricas calculadas a partir da sequência recebida pelo consumidor.
    """

    buffer: list[int | None] = [None] * tamanho
    entrada = 0
    saida = 0
    ocupadas = 0
    produtor_terminou = False
    parar = threading.Event()
    recebidas: list[int] = []
    travou = False

    def produtor() -> None:
        """Gera amostras e altera o contador sem exclusão mútua."""

        nonlocal entrada, ocupadas, produtor_terminou
        for amostra in range(total):
            while ocupadas >= tamanho and not parar.is_set():
                time.sleep(0)
            if parar.is_set():
                break

            buffer[entrada] = amostra
            entrada = (entrada + 1) % tamanho

            valor_lido = ocupadas
            time.sleep(0)
            ocupadas = valor_lido + 1

        produtor_terminou = True

    def consumidor() -> None:
        """Retira amostras e encerra após um segundo sem progresso."""

        nonlocal saida, ocupadas, travou
        ultimo_recebimento = time.monotonic()

        while len(recebidas) < total and not parar.is_set():
            if ocupadas <= 0:
                if time.monotonic() - ultimo_recebimento >= TIMEOUT:
                    travou = True
                    parar.set()
                    break
                time.sleep(0)
                continue

            amostra = buffer[saida]
            buffer[saida] = None
            saida = (saida + 1) % tamanho

            valor_lido = ocupadas
            time.sleep(0)
            ocupadas = valor_lido - 1

            if amostra is not None:
                recebidas.append(amostra)
                ultimo_recebimento = time.monotonic()

            if produtor_terminou and ocupadas <= 0 and len(recebidas) < total:
                # Ainda aguardamos até o timeout: o contador pode ter sido
                # corrompido por uma atualização perdida.
                time.sleep(0)

    thread_produtor = threading.Thread(target=produtor, name="sensor")
    thread_consumidor = threading.Thread(target=consumidor, name="motor")
    thread_produtor.start()
    thread_consumidor.start()
    thread_produtor.join(timeout=10)
    thread_consumidor.join(timeout=10)

    if thread_produtor.is_alive() or thread_consumidor.is_alive():
        travou = True
        parar.set()
        thread_produtor.join(timeout=2)
        thread_consumidor.join(timeout=2)

    contagens = Counter(recebidas)
    unicas_validas = sum(1 for valor in range(total) if contagens[valor] > 0)
    duplicadas = sum(max(0, quantidade - 1) for quantidade in contagens.values())
    return Resultado(
        consumidas=len(recebidas),
        perdidas=total - unicas_validas,
        duplicadas=duplicadas,
        travou=travou,
    )


def ler_argumentos() -> argparse.Namespace:
    """Lê os parâmetros da linha de comando.

    Returns:
        Namespace com a quantidade de amostras e o tamanho do buffer.
    """

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--amostras", type=int, default=TOTAL_PADRAO)
    parser.add_argument("--buffer", type=int, default=N_PADRAO)
    return parser.parse_args()


def main() -> None:
    """Executa o experimento e imprime uma linha fácil de comparar."""

    args = ler_argumentos()
    resultado = executar(args.amostras, args.buffer)
    print("Versão 1 - sem sincronização")
    print(f"Amostras previstas: {args.amostras} | Buffer: {args.buffer}")
    print(
        f"Consumidas: {resultado.consumidas} | Perdidas: {resultado.perdidas} | "
        f"Duplicadas: {resultado.duplicadas} | Travou: {'sim' if resultado.travou else 'não'}"
    )


if __name__ == "__main__":
    main()
