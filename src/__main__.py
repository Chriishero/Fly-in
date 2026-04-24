import sys
from .Parser import Parser
from pydantic import ValidationError


def main() -> None:
    try:
        argv = sys.argv[1:]
        parser = Parser(map_path=argv[0])
        parser.parse()
    except ValidationError as e:
        print(e)


if __name__ == "__main__":
    main()
