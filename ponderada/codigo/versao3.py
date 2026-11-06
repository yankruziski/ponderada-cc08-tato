"""Versão 3: ordem incorreta, com mutex adquirido antes de vazio.

Um pequeno atraso na partida do consumidor permite que o produtor encha o
buffer. Na amostra seguinte ele segura mutex enquanto espera vazio; o
consumidor segura cheio e espera mutex, expondo o deadlock.
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
    """Armazena as métricas e o diagnóstico de travamento."""

    consumidas: int
    perdidas: int
    duplicadas: int
    travou: bool


def executar(total: int, tamanho: int) -> Resultado:
    """Executa a ordem de aquisição capaz de produzir deadlock.

    Args:
        total: Número planejado de amostras.
        tamanho: Capacidade do buffer circular.

    Returns:
        Métricas observadas até a detecção do travamento.
    """

    buffer: list[int | None] = [None] * tamanho
    entrada = 0
    saida = 0
    recebidas: list[int] = []
    vazio = threading.Semaphore(tamanho)
    cheio = threading.Semaphore(0)
    mutex = threading.Semaphore(1)
    parar = threading.Event()
    deadlock_detectado = threading.Event()

    def produtor() -> None:
        """Adquire mutex antes de vazio, que é a ordem propositalmente errada."""

        nonlocal entrada
        for amostra in range(total):
            if parar.is_set():
                break
            mutex.acquire()
            if not vazio.acquire(timeout=TIMEOUT):
                deadlock_detectado.set()
                parar.set()
                mutex.release()
                break
            buffer[entrada] = amostra
            entrada = (entrada + 1) % tamanho
            mutex.release()
            cheio.release()

    def consumidor() -> None:
        """Consome dados até terminar ou até o watchdog detectar o ciclo."""

        nonlocal saida
        while len(recebidas) < total and not parar.is_set():
            if not cheio.acquire(timeout=TIMEOUT):
                deadlock_detectado.set()
                parar.set()
                break
            if not mutex.acquire(timeout=TIMEOUT):
                deadlock_detectado.set()
                parar.set()
                cheio.release()
                break
            amostra = buffer[saida]
            buffer[saida] = None
            saida = (saida + 1) % tamanho
            mutex.release()
            vazio.release()
            if amostra is not None:
                recebidas.append(amostra)

    thread_produtor = threading.Thread(target=produtor, name="sensor")
    thread_consumidor = threading.Thread(target=consumidor, name="motor")
    thread_produtor.start()
    time.sleep(0.02)
    thread_consumidor.start()
    thread_produtor.join(timeout=3)
    thread_consumidor.join(timeout=3)

    travou = deadlock_detectado.is_set() or thread_produtor.is_alive() or thread_consumidor.is_alive()
    parar.set()
    contagens = Counter(recebidas)
    unicas_validas = sum(1 for valor in range(total) if contagens[valor] > 0)
    duplicadas = sum(max(0, quantidade - 1) for quantidade in contagens.values())
    return Resultado(len(recebidas), total - unicas_validas, duplicadas, travou)


def ler_argumentos() -> argparse.Namespace:
    """Lê os parâmetros da execução.

    Returns:
        Namespace com número de amostras e tamanho do buffer.
    """

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--amostras", type=int, default=TOTAL_PADRAO)
    parser.add_argument("--buffer", type=int, default=N_PADRAO)
    return parser.parse_args()


def main() -> None:
    """Executa a versão com ordem trocada e mostra o resultado."""

    args = ler_argumentos()
    resultado = executar(args.amostras, args.buffer)
    print("Versão 3 - ordem mutex -> vazio")
    print(f"Amostras previstas: {args.amostras} | Buffer: {args.buffer}")
    print(
        f"Consumidas: {resultado.consumidas} | Perdidas: {resultado.perdidas} | "
        f"Duplicadas: {resultado.duplicadas} | Travou: {'sim' if resultado.travou else 'não'}"
    )


if __name__ == "__main__":
    main()
