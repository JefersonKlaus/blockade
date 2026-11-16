"""Robô contra robô: serve para conferir o equilíbrio dos níveis.

Uso:  python -m blockwar.simulate --games 40 --size 7 --blue dificil --orange facil
"""
from __future__ import annotations

import argparse
import random
from collections import Counter
from typing import Optional, Sequence

from .bot import Level, choose_move, level_from_value
from .game import Game
from .models import Player


def play_game(size: int, blue: Level, orange: Level, seed: int) -> Optional[Player]:
    """Joga uma partida completa entre dois robôs e devolve o vencedor (None = empate)."""
    rng = random.Random(seed)
    game = Game(size)
    levels = {Player.BLUE: blue, Player.ORANGE: orange}
    while not game.over:
        pos = choose_move(game.board, game.current, levels[game.current], rng)
        assert pos is not None  # partida não acabou, então há casa livre
        game.play(pos)
    return game.winner


def tournament(games: int, size: int, blue: Level, orange: Level, seed: int = 0) -> Counter:
    """Joga várias partidas; em metade delas os lados trocam de nível (para ser justo)."""
    if games < 1:
        raise ValueError("games deve ser pelo menos 1")
    tally: Counter = Counter()
    for i in range(games):
        swap = i % 2 == 1
        b, o = (orange, blue) if swap else (blue, orange)
        winner = play_game(size, b, o, seed + i)
        if winner is None:
            tally["draw"] += 1
        else:
            first_is_blue = (winner is Player.BLUE) != swap
            tally["first" if first_is_blue else "second"] += 1
    return tally


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Simula partidas entre robôs.")
    parser.add_argument("--games", type=int, default=40)
    parser.add_argument("--size", type=int, default=7)
    parser.add_argument("--blue", default="dificil")
    parser.add_argument("--orange", default="facil")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)
    first, second = level_from_value(args.blue), level_from_value(args.orange)
    tally = tournament(args.games, args.size, first, second, args.seed)
    print(f"{first.value} x {second.value} em {args.size}x{args.size}, {args.games} partidas: "
          f"{first.value} {tally['first']}, {second.value} {tally['second']}, "
          f"empates {tally['draw']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
