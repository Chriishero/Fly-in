import sys
from .Parser import Parser
from .GUI import GUI
from .Simulation import Simulation


def main() -> None:
    """Main function, parse the map file, instantiate and launch
    GUI and simulation."""
    try:
        map = None
        argv = sys.argv[1:]
        if argv[0] != "--map":
            raise ValueError("Argument '--map <file>' is mandatory.")
        parser = Parser(map_path=argv[1])
        parser.parse()
        if parser.map is not None:
            map = parser.map
            simulation = Simulation(map=map)
            gui = GUI(
                map=map,
                simulation=simulation,
                drone_size_scaling_factor=0.1)
            gui.init()
            gui.run()
    except Exception as e:
        print(e)


if __name__ == "__main__":
    main()
