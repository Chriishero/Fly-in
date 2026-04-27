import sys
from .Parser import Parser
from .GUI import GUI
from .Simulation import Simulation


def main() -> None:
    map = None
    argv = sys.argv[1:]
    if argv[0] != "--map":
        raise ValueError("Argument '--map <file>' is mandatory.")
    parser = Parser(map_path=argv[1])
    parser.parse()
    if parser.map is not None:
        map = parser.map
        simulation = Simulation(map=map)
        gui = GUI(map=map, simulation=simulation)
        gui.init()
        gui.run()


if __name__ == "__main__":
    main()
