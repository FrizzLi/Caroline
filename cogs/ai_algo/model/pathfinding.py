"""Runs second stage of creating simulation - Pathfinding.

find_shortest_path                  - main function
    _validate_and_set_input_pars    - sets parameters
    _find_shortest_distances        - gets shortest distances between points
        _a_star                     - from start to end
        _dijkstra                   - from start to everywhere
            _passable               - checks whether place on map is passable
            get_next_dist           - gets next distance (climb/no climb)
    _held_karp                      - optimal way to find shortest combo path
    _naive_permutations             - greedy way to find shortest combo path
    _get_routes                     - gets the whole path via parent nodes
    _print_solution                 - prints the routes - solution
    _save_solution                  - saves the solution into pickle file
"""

import heapq
import pickle
from copy import deepcopy
from itertools import combinations, permutations
from pathlib import Path
from sys import maxsize
from typing import Any, Dict, FrozenSet, List, Tuple


class MovementError(Exception):
    pass


class SubsetSizeError(Exception):
    pass


class AlgorithmError(Exception):
    pass


class Node:

    __slots__ = ("pos", "terr", "parent", "dist", "g", "h")

    def __init__(self, position, terrain):
        self.pos = position  # type: Tuple[int, int]
        self.terr = terrain  # type: int
        self.parent = -1  # type: Tuple[int, int]
        self.dist = maxsize  # type: int

        # A* heuristic variables
        self.g = maxsize  # type: int
        self.h = maxsize  # type: int

    def __lt__(self, other):
        if self.dist != other.dist:
            return self.dist < other.dist
        return self.h < other.h


class Map:

    __slots__ = ("fname", "width", "height", "properties", "nodes", "h")

    def __init__(self, fname) -> None:
        self.fname = ""  # type: str
        self.width = 0  # type: int
        self.height = 0  # type: int
        self.properties = {}  # type: Dict[str, Any]
        self.nodes = {}  # type: Dict[Tuple[int, int], Node]
        self.load_map(fname)

    def load_map(self, fname) -> None:
        properties = {
            "points": [],
            "home": 0,
            "start": 0,
        }  # type: Dict[str, Any]
        nodes = {}  # type: Dict[Tuple[int, int], Node]

        source_dir = Path(__file__).parents[1]
        fname_path = Path(f"{source_dir}/data/maps/{fname}_pro.txt")
        with open(fname_path, encoding="utf-8") as file:
            for i, row in enumerate(file):
                for j, col in enumerate(row.split()):

                    # if there are brackets, add propertied point
                    if not col.isnumeric():
                        if col.startswith("("):
                            properties["points"].append((i, j))
                        elif col.startswith("["):
                            properties["home"] = (i, j)
                        elif col.startswith("{"):
                            properties["start"] = (i, j)
                        if not col.startswith("-"):
                            col = col[1:-1]

                    nodes[i, j] = Node((i, j), int(col))

        height, width = max(nodes)
        if all(properties.values()):
            self.fname = fname
            self.height = height + 1
            self.width = width + 1
            self.properties = properties
            self.nodes = nodes

    def __getitem__(self, pos):
        assert len(pos) == 2, "Coordinate must have two values."
        if not (0 <= pos[0] < self.height and 0 <= pos[1] < self.width):
            return None  # position out of bounds of the map
        return self.nodes[pos]


def find_shortest_path(
    fname: str,
    movement_type: str,
    climb: bool,
    algorithm: str,
    visit_points_amount: int,
) -> None:
    """Finds the shortest visiting path order between all the properties on the
    map.

    Args:
        fname (string): name of the file to load (with no suffix)
        movement_type (string): determines movement options throughout the map
            Options: "M", "D" (Manhattan or Diagonal + Manhattan)
        climb (bool): determines distance calculcation approach. If True,
            distance is measured as abs(current terrain number - next terrain
            number)
        algorithm (string): determines what algorithm to use to find the
            shortest path
            Options: "NP", "HK" (Naive Permutations or Held Karp)
        visit_points_amount (int): Amount of points to visit.
            0 means all. Must be at least 1.
    """

    alg_opts = {
        "NP": _naive_permutations,
        "HK": _held_karp,
    }

    try:
        map_ = Map(fname)
        moves, visit_points_amount, algorithm = _validate_and_set_input_pars(
            movement_type,
            visit_points_amount,
            map_.properties["points"],
            algorithm,
        )

        disted_map = _find_shortest_distances(map_, moves, climb)
        node_paths, dist = alg_opts[algorithm](disted_map, visit_points_amount)
        routed_paths = _get_routes(disted_map, node_paths)

        _print_solution(routed_paths, dist)

        _save_solution(routed_paths, fname)

    except FileNotFoundError as err:
        print(err)
    except MovementError as err:
        print(err)
    except SubsetSizeError as err:
        print(err)


def _validate_and_set_input_pars(
    movement_type: str,
    visit_points_amount: int,
    map_points: List[Tuple[int, int]],
    algorithm: str,
) -> Tuple[List[Tuple[int, int]], int, str]:
    """Validates and sets parameters from input for pathfinding.

    Gets movement possibilities from either Manhattan or Diagonal + Manhattan
    approach.
    Validates and sets amount of points to visit. If its None or higher than
    the amount of points on the map, it will be reduced down to the map's
    amount.
    Validates algorithm option.

    Args:
        movement_type (str): determines movement options throughout the map
            Options: "M", "D" (Manhattan or Diagonal + Manhattan)
        visit_points_amount (int): Amount of points to visit.
            0 means all. Must be at least 1.
        map_points (List[Tuple[int, int]]): coordinates of points on the map
        algorithm (str): determines what algorithm to use to find the
            shortest path
            Options: "NP", "HK" (Naive Permutations or Held Karp)

    Raises:
        MovementError: movement_type is not "M" or "N"
        SubsetSizeError: visit_points_amount is negative number
        AlgorithmError: wrong algorithm abbreviation string (NP or HK only!)

    Returns:
        Tuple[List[Tuple[int, int]], int, str]: (
            movement options
            amount of points to visit
            algorithm that is going to be used
        )
    """

    # validate and get movement possibilities
    moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if movement_type == "D":
        moves += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    elif movement_type != "M":
        raise MovementError("Invalid movement type!")

    # validate and set visit_points_amount
    if not visit_points_amount or visit_points_amount > len(map_points):
        visit_points_amount = len(map_points)
    if visit_points_amount < 0:
        raise SubsetSizeError("Invalid subset size!")

    # validate algorithm
    if algorithm not in ("NP", "HK"):
        raise AlgorithmError("Invalid algorithm input!")

    return moves, visit_points_amount, algorithm


def _find_shortest_distances(
    map_: Map, moves: List[Tuple[int, int]], climb: bool
) -> Map:
    """Finds shortest distances between all properties.

    Uses A* algorithm from start, from all the others _Dijkstra is used.

    Args:
        map_ (Map): contains information about the map
        moves (List[Tuple[int, int]]): movement options
        climb (bool): determines distance calculcation approach. If True,
            distance is measured as abs(current terrain number - next terrain
            number)

    Returns:
        Map: Map that contains information about the shortest distances between
            all properties in nodes attribute.
            (Access via Dict[start][destination].dist)
    """

    points, home, start = map_.properties.values()

    from_start_to_home = _a_star(map_, moves, climb, start, home)
    from_home_to_all = _dijkstra(map_, moves, climb, home)
    from_points_to_all = {
        point: _dijkstra(map_, moves, climb, point)
        for point in points
    }

    shortest_distance_nodes_between_properties = {
        start: from_start_to_home,
        home: from_home_to_all,
        **from_points_to_all,
    }

    map_.nodes = shortest_distance_nodes_between_properties  # TODO?

    return map_


def _a_star(
    nodes_map: Map,
    moves: List[Tuple[int, int]],
    climb: bool,
    start: Tuple[int, int],
    dest: Tuple[int, int],
) -> Dict[Tuple[int, int], Node]:
    """Finds the shortest path from start to destination and saves it into the
    map.

    Args:
        nodes_map (Map): contains information about the map
        moves (List[Tuple[int, int]]): movement options
        climb (bool): determines distance calculcation approach. If True,
            distance is measured as abs(current terrain number - next terrain
            number)
        start (Tuple[int, int]): starting position
        dest (Tuple[int, int]): ending position

    Returns:
        Dict[Tuple[int, int], Node]: contains path and distance from start to
            destination
    """

    nodes = deepcopy(nodes_map.nodes)
    nodes[start].g = 0
    open_list = []  # type: List[Node]
    close_list = []
    heapq.heappush(open_list, nodes[start])

    while open_list:
        node = heapq.heappop(open_list)
        if node.pos == dest:
            break

        close_list.append(node.pos)
        for move in moves:
            next_pos = node.pos[0] + move[0], node.pos[1] + move[1]
            if _passable(next_pos, nodes_map) and next_pos not in close_list:
                next_node = nodes[next_pos]

                # heuristic - distance between destination and next_node
                x_diff = abs(next_node.pos[0] - dest[0])
                y_diff = abs(next_node.pos[1] - dest[1])
                h = x_diff + y_diff

                # distance between start and next_node
                step_dist = get_next_dist(node.terr, next_node.terr, climb)
                g = node.g + step_dist

                f = g + h  # estimated distance between start and destination
                if f < next_node.dist:
                    next_node.g = g
                    next_node.h = h
                    next_node.dist = f
                    next_node.parent = node.pos
                if next_node not in open_list:
                    heapq.heappush(open_list, next_node)

    return nodes


def _dijkstra(
    nodes_map: Map,
    moves: List[Tuple[int, int]],
    climb: bool,
    start: Tuple[int, int],
) -> Dict[Tuple[int, int], Node]:
    """Finds the shortest path from start to all destinations and saves it into
    the map.

    Args:
        nodes_map (Map): contains information about the map
        moves (List[Tuple[int, int]]): movement options
        climb (bool): determines distance calculcation approach. If True,
            distance is measured as abs(current terrain number - next terrain
            number)
        start (Tuple[int, int]): starting position

    Returns:
        Dict[Tuple[int, int], Node]: contains path and distance from start to
            all destinations
    """

    nodes = deepcopy(nodes_map.nodes)
    nodes[start].dist = 0
    heap = []  # type: List[Node]
    heapq.heappush(heap, nodes[start])

    while heap:
        node = heapq.heappop(heap)
        for move in moves:
            next_pos = node.pos[0] + move[0], node.pos[1] + move[1]
            if _passable(next_pos, nodes_map):
                next_node = nodes[next_pos]
                step_dist = get_next_dist(node.terr, next_node.terr, climb)
                next_node_dist = node.dist + step_dist

                if next_node.dist > next_node_dist:
                    next_node.dist = next_node_dist
                    next_node.parent = node.pos
                    heapq.heappush(heap, next_node)

    return nodes


def _passable(next_pos: Tuple[int, int], nodes_map: Map):
    """Checks whether next_pos position is passable (not walled or out of map).

    Args:
        next_pos (Tuple[int, int]): position on which movement was applied
        nodes_map (Map): contains information about the map

    Returns:
        bool: passability
    """

    valid_pos = nodes_map[next_pos]
    if valid_pos:
        valid_pos = not valid_pos.terr < 0

    return valid_pos


def get_next_dist(prev_terr: int, next_terr: int, climb: bool) -> int:
    """Gets next distance based on whether its climbing approach or not.

    Args:
        prev_terr (int): terrain of position from which we move
        next_terr (int): terrain of position to which we move
        climb (bool): determines distance calculcation approach. If True,
            distance is measured as abs(current terrain number - next terrain
            number)

    Returns:
        int: distance to the next position
    """

    if climb:
        return abs(prev_terr - next_terr) + 1
    else:
        return next_terr


def _held_karp(
    map_: Map, visit_points_amount: int
) -> Tuple[List[Tuple[int, int]], int]:
    """Finds the shortest visiting path order between all the properties on the
    map using Held Karp's algorithm.

    Args:
        map_ (Map): Map that contains information about the shortest distances
            between all properties in nodes attribute.
            (Access via Dict[start][destination].dist)
        visit_points_amount (int): amount of points to visit (more than 1)

    Returns:
        Tuple[List[Tuple[int, int]], int]: (shortest visiting path order of
            properties, distance of the path)
    """

    points, home, start = map_.properties.values()
    points_set = frozenset(points)

    coor_and_comb = Tuple[Tuple[int, int], FrozenSet[int]]
    cost_and_parent_coor = Tuple[int, Tuple[int, int]]
    nodes: Dict[coor_and_comb, cost_and_parent_coor] = {}

    for comb_size in range(visit_points_amount):
        for comb in combinations(points_set, comb_size):
            comb_set = frozenset(comb)
            points_to_visit = points_set - comb_set
            for dest in points_to_visit:
                routes = []
                if comb_set:
                    for begin in comb_set:
                        sub_comb = comb_set - frozenset({begin})
                        prev_cost = nodes[begin, sub_comb][0]
                        cost = map_[begin][dest].dist + prev_cost
                        routes.append((cost, begin))
                    nodes[dest, comb_set] = min(routes)

                else:  # first visit (start -> home)
                    cost = (
                        map_[home][dest].dist + map_[start][home].dist
                    )
                    nodes[dest, frozenset()] = cost, home

    # get total cost, ending node and its parent
    last_nodes_raw = list(nodes.items())[-len(points_set):]
    last_nodes = [(*node[1], node[0][0]) for node in last_nodes_raw]
    last_optimal_node = min(last_nodes)
    cost, parent, end = last_optimal_node
    points_set -= {end}
    path = [end]

    # backtrack remaining nodes
    for _ in range(visit_points_amount - 1):
        path.append(parent)
        points_set -= {parent}
        parent = nodes[parent, points_set][1]
    path.extend([home, start])

    return path[::-1], cost


def _naive_permutations(
    map_: Map, visit_points_amount: int
) -> Tuple[List[Tuple[int, int]], int]:
    """Gets all visiting path orders between all the properties on the map in
    order to find the shortest path order.

    Args:
        map_ (Map): Map that contains information about the shortest distances
            between all properties in nodes attribute.
            (Access via Dict[start][destination].dist)
        visit_points_amount (int): amount of points to visit (more than 1)

    Returns:
        Tuple[List[Tuple[int, int]], int]: (shortest visiting path order of
            properties, distance of the path)
    """

    points, home, start = map_.properties.values()
    total_cost = maxsize

    for permutation in permutations(points, visit_points_amount):
        distance = map_[start][home].dist
        for begin, finish in zip((home,) + permutation, permutation):
            distance += map_[begin][finish].dist
        if distance < total_cost:
            total_cost, permutation_path = distance, permutation

    return list((start, home) + permutation_path), total_cost


def _get_routes(
    map_: Map, node_paths: List[Tuple[int, int]]
) -> List[List[Tuple[int, int]]]:
    """Gets step by step coordinate routes from the shortest visiting path
    order of properties via parent attribute.

    Args:
        map_ (Map): Map that contains information about the shortest distances
            between all properties in nodes attribute.
            (Access via Dict[start][destination].dist)
        node_paths (List[Tuple[int, int]]): shortest visiting path order
            of properties

    Returns:
        List[List[Tuple[int, int]]]: routed paths
    """

    paths = []

    for begin, route in zip(node_paths, node_paths[1:]):
        path = []
        while route != begin:
            path.append(route)
            route = map_[begin][route].parent
        paths.append(path[::-1])

    return paths


def _print_solution(
    routed_paths: List[List[Tuple[int, int]]], dist: int
) -> None:
    """Prints the routed paths.

    Each line starts with order number followed by order of tuple coordinates
    that represent the movement progression from start to destination.

    Args:
        routed_paths (List[List[Tuple[int, int]]]): routed paths (solution)
        dist (int): total distance
    """

    for i, routed_path in enumerate(routed_paths, 1):
        print(f"{i}: ", *routed_path)

    print("Cost: " + str(dist) + "\n")


def _save_solution(
    routed_paths: List[List[Tuple[int, int]]], fname: str
) -> None:
    """Saves the solution (routed paths) into pickle file for gif
    visualization.

    Args:
        routed_paths (List[List[Tuple[int, int]]]): routed paths (solution)
        fname (str): name of pickle file into which solution will be saved
    """

    source_dir = Path(__file__).parents[1]
    solutions_dir = Path(f"{source_dir}/data/solutions")
    solutions_dir.mkdir(parents=True, exist_ok=True)

    fname_path = Path(f"{solutions_dir}/{fname}_path")
    with open(fname_path, "wb") as file:
        pickle.dump(routed_paths, file)


if __name__ == "__main__":

    FNAME = "queried"
    MOVEMENT_TYPE = "M"
    CLIMB = False
    ALGORITHM = "HK"
    VISIT_POINTS_AMOUNT = 4

    path_parameters = dict(
        fname=FNAME,
        movement_type=MOVEMENT_TYPE,
        climb=CLIMB,
        algorithm=ALGORITHM,
        visit_points_amount=VISIT_POINTS_AMOUNT,
    )  # type: Dict[str, Any]

    find_shortest_path(**path_parameters)
