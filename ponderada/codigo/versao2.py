"""Versão 2: buffer circular protegido pelos três semáforos pedidos."""

from __future__ import annotations

import argparse
import threading
from collections import Counter
from dataclasses import dataclass


TOTAL_PADRAO = 20_000
N_PADRAO = 6


@dataclass
class Resultado:
    """Armazena as métricas finais de uma execução sincronizada."""

    consumidas: int
    perdidas: int
    duplicadas: int
    travou: bool


def executar(total: int, tamanho: int) -> Resultado:
    """Executa produtor e consumidor com vazio, cheio e mutex.

    Args:
        total: Número de amostras produzidas.
        tamanho: Capacidade do buffer circular.

    Returns:
        Métricas da sequência recebida pelo consumidor.
    """

    buffer: list[int | None] = [None] * tamanho
    entrada = 0
    saida = 0
    recebidas: list[int] = []
    vazio = threading.Semaphore(tamanho)
    cheio = threading.Semaphore(0)
    mutex = threading.Semaphore(1)

    def produtor() -> None:
        """Insere todas as amostras, esperando espaço antes do mutex."""

        nonlocal entrada
        for amostra in range(total):
            vazio.acquire()
            mutex.acquire()
            buffer[entrada] = amostra
            entrada = (entrada + 1) % tamanho
            mutex.release()
            cheio.release()

    def consumidor() -> None:
        """Retira exatamente o total de amostras produzido."""

        nonlocal saida
        for _ in range(total):
            cheio.acquire()
            mutex.acquire()
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
    thread_consumidor.start()
    thread_produtor.join(timeout=10)
    thread_consumidor.join(timeout=10)
    travou = thread_produtor.is_alive() or thread_consumidor.is_alive()

    contagens = Counter(recebidas)
    unicas_validas = sum(1 for valor in range(total) if contagens[valor] > 0)
    duplicadas = sum(max(0, quantidade - 1) for quantidade in contagens.values())
    return Resultado(len(recebidas), total - unicas_validas, duplicadas, travou)


def ler_argumentos() -> argparse.Namespace:
    """Lê total de amostras e capacidade do buffer.

    Returns:
        Namespace contendo os argumentos validados pelo argparse.
    """

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--amostras", type=int, default=TOTAL_PADRAO)
    parser.add_argument("--buffer", type=int, default=N_PADRAO)
    return parser.parse_args()


def main() -> None:
    """Executa a versão correta e imprime suas métricas."""

    args = ler_argumentos()
    resultado = executar(args.amostras, args.buffer)
    print("Versão 2 - três semáforos")
    print(f"Amostras previstas: {args.amostras} | Buffer: {args.buffer}")
    print(
        f"Consumidas: {resultado.consumidas} | Perdidas: {resultado.perdidas} | "
        f"Duplicadas: {resultado.duplicadas} | Travou: {'sim' if resultado.travou else 'não'}"
    )


if __name__ == "__main__":
    main()
