8:00 - 10:40

## FLAG
1 |  


## Task description *
The first goal is 'close' the apps' design, improve the colors and the UI, and create many screeshot pictures.
The second goal is fix some bug, like the device action bar (top) is hidding some buttons
The last goal is improve the UX, because is hard to understand how need to play (player one or player two).

## How to judge completion *
Run the project play the game, validate the UI, check if is easy to see wich player needs to play, open the tutorial, play the game 1x1 and 1xcomputer.
Run test pytest and all tests need to pass.
The current version has 568 tests

## Other notes for the reviewer (optional)
This is a mobile game make to play with my family, we call it 'block war', but the game is called 'blokade'.
this is a open source game that you can find in this URL https://github.com/JefersonKlaus/blockade.
This version is already good to play, but, we need fix some bugs and improve a little bit the UI.


## How to test
I ran the projec using 'flet run' and I could play the game, against my tester and against the computer (cellphone), after that I tested the version using math, the app is more easy to understand and more beatiful, and all bugs were fixed.
After I run the pytest.

SETUP:
python -m venv .venv
source .venv/bin/activate            
pip install -e ".[dev]"


ACTION: flet run
RESULT: play the game

ACTION: pytest
RESULT: 182 passed in 4.82
