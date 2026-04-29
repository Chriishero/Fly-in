*This project has been created as part of the 42 curriculum by <cvillene\>*

# Fly-in

## Description
Fly-in is a project tha simulates a fleet of drones traveling from a base (start hub) to a target location (end hub). Several 'maps' are provided, each defining hubs and the connections between them aong with constraints for each zone (blocked, restricted, max drones, etc).
The goal is to develop an algorithm capable of finding the shortest path for EACH drones, while respecting all constraints.

## Instructions
### Install dependencies
```bash
make install
```
### Run
```bash
make run MAP=<map path>
```
### Run in debug mode
```bash
make debug
```
### Clean temporary files
```bash
make clean
```
### Lint (flake8 and mypy)
```bash
make lint
```
or
```bash
make lint-strict
```

## Resources
- Documentation on the Dijkstra and A* algorithm
- Documentation of pygame (and few tutorial)
- AI to understand the Dijkstra algorithm

## Algorithm explanation
The main algorithm used is the Dijkstra algorithm.
A weight/cost is assigned to each hub (node), defining a weighted undirected graph. This algorithm computes the shortest path from the source (start hub) to all other hubs (nodes) in the graph.
#### Detailed steps:
- Create an empty priority queue (heap).
- Create a distance dictionary 'dist' of size n_hubs and set all values to infinity. It maps each hub to their distance from the start.
- Create a previous dictionary 'prev' of size n_hubs and set all values to None. It maps each hub to their previous hub in the graph.
- Set the start hub distance to 0 and insert it into the heap.
- While the heap is not empty
  - Pop the hub with the smallest distance value.
  - If the popped distance is greater than the recorded distance.  
    - skip it and continue
  - For each neighbors v of curr_hub
    - If dist[curr_hub] + cost of v < dist[v]:
      - Update dist[v] = dist[u] + cost
      - Update prev[v] = curr_hub
      - Push (dist[v], v) to the heap
  - Repeat until the heap is empty
#### Conflicts handling
Dijkstra computes the PLANNED move for each drone. At this stage, the number of drones in each hub is still unchanged, but I simulate the movement by updating the 'n_drones' attribute of each location. This ensures that the next Dijkstra iteration (for the next drone) takese the updated hub/connection capacities into account.

## Visual representation
Each hub has an associated color, defined in the maps files.
### Terminal
```bash
D<drone id>-<location name>
```
### Graphical Interface
Represent all the drones in the graph.
- Space: start/pause the simulation
- Left Arrow: go to the previous turn
- Right Arraw: go to the next turn
- Clicking on a hub or connectino displays its information (name, zone type, max_drones, n_drones, etc).