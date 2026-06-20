from __future__ import annotations

import sys

from dotenv import load_dotenv

from agent.agent import ask
from logger import setup_logging

load_dotenv()


def main() -> None:
    setup_logging()
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        question = input("Question: ")
    print(ask(question))


if __name__ == "__main__":
    main()
