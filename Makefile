PYTHON = python3
UV = uv
MAP ?=
MYPY_FLAGS = --warn-return-any --warn-unused-ignores --ignore-missing-imports \
				--disallow-untyped-defs --check-untyped-defs

.PHONY: install run debug clean lint lint-strict

install:
	$(UV) sync

run:
ifeq ($(MAP),)
	$(error MAP is mandatory: ex. make run MAP=maps/easy/01_linear_path.txt)
endif
	$(UV) run $(PYTHON) -m src --map $(MAP)

debug:
	$(UV) run $(PYTHON) -m pdb -m src

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +

lint:
	$(UV) run $(PYTHON) -m flake8 .
	$(UV) run $(PYTHON) -m mypy . $(MYPY_FLAGS)

lint-strict:
	$(UV) run $(PYTHON) -m flake8 .
	$(UV) run $(PYTHON) -m mypy . --strict
