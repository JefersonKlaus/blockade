"""Every text shown on screen, in English (the default) and Portuguese.

One `Texts` object holds all the texts of one language; the app picks it once, from the
device's language (`texts_for`), and hands it to whatever shows text. Each text is a
field, so a missing translation is an error when the module loads, not a blank label.

Texts with `{placeholders}` are filled in with `str.format`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .bot import Level
from .models import Player


@dataclass(frozen=True)
class Texts:
    # ---------------------------------------------------------------- names
    blue: str
    orange: str
    you: str                      # the human player, against the phone
    phone: str                    # the phone as a player
    easy: str
    medium: str
    hard: str
    one_block: str
    many_blocks: str              # {count}

    # ---------------------------------------------------------------- menu
    who_plays: str
    a_friend: str
    the_phone: str
    how_smart: str
    math_title: str
    play: str
    record: str                   # {wins} {losses} {draws}

    # ---------------------------------------------------------------- math page
    times_tables: str
    back: str

    # ---------------------------------------------------------------- tutorial
    how_to_play: str
    step_tap: str
    step_tap_again: str
    step_capture: str
    step_most_wins: str
    step_math: str
    got_it: str

    # ---------------------------------------------------------------- game
    your_turn: str
    phone_turn: str
    player_turn: str              # {name} {symbol}
    game_over: str
    draw: str
    you_won: str
    phone_won: str
    player_won: str               # {name}
    start: str
    start_math: str
    preview: str                  # {blocks}
    preview_nothing: str
    answer_prompt: str
    wrong_answer: str             # {answer} {name}
    turned: str                   # {name} {blocks}
    placed: str                   # {name}
    undone: str
    cant_undo: str
    hint_message: str
    thinking: str
    hint: str
    undo: str                     # {count}
    play_again: str
    menu: str

    def player(self, player: Player) -> str:
        return self.blue if player is Player.BLUE else self.orange

    def level(self, level: Level) -> str:
        return {Level.EASY: self.easy, Level.MEDIUM: self.medium, Level.HARD: self.hard}[level]

    def blocks(self, count: int) -> str:
        return self.one_block if count == 1 else self.many_blocks.format(count=count)


ENGLISH = Texts(
    blue="Blue",
    orange="Orange",
    you="You",
    phone="Phone",
    easy="Easy",
    medium="Medium",
    hard="Hard",
    one_block="1 block",
    many_blocks="{count} blocks",
    who_plays="Who will play with you?",
    a_friend="A friend",
    the_phone="The phone",
    how_smart="How smart is the phone?",
    math_title="Practice math",
    play="Play!",
    record="At this level: {wins} won, {losses} lost, {draws} tied",
    times_tables="Times tables",
    back="◀ Back",
    how_to_play="How to play",
    step_tap="1. Tap an empty square.",
    step_tap_again="2. Tap it again to place your block.",
    step_capture="The other side's blocks caught between two of your blocks become yours!",
    step_most_wins="Whoever has the most blocks at the end wins!",
    step_math="Get the question right to place your block!",
    got_it="Got it!",
    your_turn="Your turn",
    phone_turn="Phone's turn",
    player_turn="{name}'s turn {symbol}",
    game_over="Game over",
    draw="It's a tie!",
    you_won="You won!",
    phone_won="The phone won this time.",
    player_won="{name} won!",
    start="Tap a square to see what turns.",
    start_math="Tap a square. After confirming, answer the question.",
    preview="Turns {blocks}. Tap again to play.",
    preview_nothing="Nothing turns. Tap again to play anyway.",
    answer_prompt="Answer right to place your block!",
    wrong_answer="Oops! The answer was {answer}. {name} lost the turn.",
    turned="{name} turned {blocks}.",
    placed="{name} placed a block.",
    undone="Move undone.",
    cant_undo="Can't undo right now.",
    hint_message="Hint: the green square turns a lot.",
    thinking="The phone is thinking...",
    hint="Hint",
    undo="Undo ({count})",
    play_again="Play again",
    menu="Menu",
)

PORTUGUESE = Texts(
    blue="Azul",
    orange="Laranja",
    you="Você",
    phone="Celular",
    easy="Fácil",
    medium="Médio",
    hard="Difícil",
    one_block="1 bloco",
    many_blocks="{count} blocos",
    who_plays="Quem vai jogar com você?",
    a_friend="Um amigo",
    the_phone="O celular",
    how_smart="Quão esperto é o celular?",
    math_title="Praticar matemática",
    play="Jogar!",
    record="Neste nível: {wins} vitórias, {losses} derrotas, {draws} empates",
    times_tables="Tabuada",
    back="◀ Voltar",
    how_to_play="Como jogar",
    step_tap="1. Toque numa casa vazia.",
    step_tap_again="2. Toque de novo para colocar o seu bloco.",
    step_capture="Os blocos do outro presos entre dois blocos seus viram seus!",
    step_most_wins="Quem tiver mais blocos no fim ganha!",
    step_math="Acerte a conta para colocar o bloco!",
    got_it="Entendi!",
    your_turn="Sua vez",
    phone_turn="Vez do celular",
    player_turn="Vez do {name} {symbol}",
    game_over="Fim de jogo",
    draw="Empate!",
    you_won="Você venceu!",
    phone_won="O celular venceu desta vez.",
    player_won="{name} venceu!",
    start="Toque numa casa para ver o que vira.",
    start_math="Toque numa casa. Depois de confirmar, responda a conta.",
    preview="Vira {blocks}. Toque de novo para jogar.",
    preview_nothing="Não vira nada. Toque de novo para jogar mesmo assim.",
    answer_prompt="Responda certo para colocar o bloco!",
    wrong_answer="Errou! A resposta era {answer}. {name} perdeu a vez.",
    turned="{name} virou {blocks}.",
    placed="{name} colocou um bloco.",
    undone="Jogada desfeita.",
    cant_undo="Não dá para desfazer agora.",
    hint_message="Dica: a casa verde vira bastante coisa.",
    thinking="O celular está pensando...",
    hint="Dica",
    undo="Desfazer ({count})",
    play_again="Jogar de novo",
    menu="Menu",
)


def texts_for(language_code: Optional[str]) -> Texts:
    """Portuguese when the device's language is Portuguese (pt, pt-BR, pt-PT...);
    English for any other language, or when the device does not say."""
    if language_code and language_code.lower().split("-")[0].split("_")[0] == "pt":
        return PORTUGUESE
    return ENGLISH
