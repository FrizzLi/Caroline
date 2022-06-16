import heapq
import os
import pickle
from copy import deepcopy
from itertools import combinations, permutations
from os.path import dirname
from pathlib import Path
from sys import maxsize
from typing import Any, Dict, FrozenSet, List, Tuple, Union


class PositionError(Exception):
    pass


class MovementError(Exception):
    pass


class SubsetSizeError(Exception):
    pass


class AlgorithmError(Exception):
    pass


class Node:
    def __init__(self, pos, terrain):
        self.pos = pos  # type: Tuple[int, int]
        self.terrain = terrain  # type: int
        self.parent = -1  # type: Tuple[int, int]
        self.dist = maxsize  # type: int
        self.g = maxsize  # type: int
        self.h = maxsize  # type: int

    def __lt__(self, other):
        if self.dist != other.dist:
            return self.dist < other.dist
        return self.h < other.h


class Map:
    def __init__(self, fname) -> None:
        self.fname = ""  # type: str
        self.width = 0  # type: int
        self.height = 0  # type: int
        self.nodes = {}  # type: Dict[Tuple[int, int], Node]
        self.properties = {}  # type: Dict[str, Any]
        self._load_map(fname)

    def _load_map(self, fname) -> None:
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
            self.nodes = nodes
            self.properties = properties

    def __getitem__(self, pos):
        assert len(pos) == 2, "Coordinate must have two values."
        if not 0 <= pos[0] < self.height or not 0 <= pos[1] < self.width:
            raise PositionError(str(pos))
        return self.nodes[pos]


def get_movement_possibilities(movement_type: str) -> List[Tuple[int, int]]:
    """Gets movement possibilities from either Manhattan or
    Diagonal + Manhattan approach.

    Args:
        movement_type (str): determines the type of movement options
            Options: "M", "D"

    Raises:
        MovementError: movement_type has not "M" or "N" set

    Returns:
        List[Tuple[int, int]]: list of tuple coordinate movement options
    """

    moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if movement_type == "D":
        moves += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    elif movement_type != "M":
        raise MovementError("Invalid movement type!")

    return moves


def unpassable(neighbor: Tuple[int, int], data: Map):
    """Checks whether neighbor position is walled or out of map.

    Args:
        neighbor (Tuple[int, int]): position on which movement was applied
        data (Map): contains information about the map

    Returns:
        bool: passability
    """

    return (
        not 0 <= neighbor[0] < data.height
        or not 0 <= neighbor[1] < data.width
        or data[neighbor].terrain < 0
    )


def getNextDist(prev_terr: int, next_terr: int, climb: bool) -> int:
    """Gets next distance based on whether its climbing approach or not.

    Args:
        prev_terr (int): terrain of position from which we move
        next_terr (int): terrain of position to which we move
        climb (int): Climbing distance approach. If True, distance is measured
            with abs(current terrain number - next terrain number)

    Returns:
        int: distance to the next position
    """

    if climb:
        return abs(prev_terr - next_terr) + 1
    else:
        return next_terr


def dijkstra(
    data: Map,
    moves: List[Tuple[int, int]],
    climb: bool,
    start: Tuple[int, int],
) -> Map:
    """Finds and saves the shortest path to all destinations from the start.

    Args:
        data (Map): contains information about the map
        moves (List[Tuple[int, int]]): tuples of movement options
        climb (bool): Climbing distance approach. If True, distance is measured
            with abs(current terrain number - next terrain number)
        start (Tuple[int, int]): starting position

    Returns:
        Map: Contains distances from starting position to all destinations.
            Access via Map[start][destination].dist
    """

    heap = []  # type: List[Node]
    data[start].dist = 0
    heapq.heappush(heap, data[start])

    while heap:
        node = heapq.heappop(heap)
        for move in moves:
            neighbor = node.pos[0] + move[0], node.pos[1] + move[1]
            if not unpassable(neighbor, data):
                next_dist = (
                    getNextDist(node.terrain, data[neighbor].terrain, climb)
                    + node.dist
                )

                if data[neighbor].dist > next_dist:
                    data[neighbor].dist = next_dist
                    data[neighbor].parent = node.pos
                    heapq.heappush(heap, data[neighbor])

    return data


def a_star(
    data: Map,
    moves: List[Tuple[int, int]],
    climb: bool,
    start: Tuple[int, int],
    dest: Tuple[int, int],
) -> Map:
    """Finds and saves the shortest path from start to destination.

    Args:
        data (Map): contains information about the map
        moves (List[Tuple[int, int]]): movement options
        climb (bool): Climbing distance calculation approach. If True, distance
            is measured with abs(current terrain number - next terrain number)
        start (Tuple[int, int]): starting position
        dest (Tuple[int, int]): ending position

    Returns:
        Map: Contains distance between starting position and destination.
            Access via Map[start][destination].dist
    """

    open_list = []  # type: List[Node]
    close_list = []
    data[start].g = 0
    heapq.heappush(open_list, data[start])

    while open_list:
        node = heapq.heappop(open_list)
        if node.pos == dest:
            break

        close_list.append(node.pos)
        for move in moves:
            neighbor = node.pos[0] + move[0], node.pos[1] + move[1]
            if not unpassable(neighbor, data) and neighbor not in close_list:
                h = abs(data[neighbor].pos[0] - dest[0]) + abs(
                    data[neighbor].pos[1] - dest[1]
                )
                g = (
                    getNextDist(node.terrain, data[neighbor].terrain, climb)
                    + node.g
                )
                f = g + h

                if f < data[neighbor].dist:
                    data[neighbor].g = g
                    data[neighbor].h = h
                    data[neighbor].dist = f
                    data[neighbor].parent = node.pos
                if data[neighbor] not in open_list:
                    heapq.heappush(open_list, data[neighbor])

    return data


def naivePermutations(
    pro_data: Dict[Tuple[int, int], Map], subset_size: int
) -> Tuple[List[Any], int]:
    """Computes the distance between all possible combinations of properties in
    order to find the shortest paths.

    Args:
        pro_data (Dict[Tuple[int, int], Map]): Contains distances between
            all properties. Access via Dict[starting][destination].dist
        subset_size (int): number of points to visit (more than 1)

    Returns:
        Tuple[List[Any], int]: (order of properties' coordinates, distance)
    """

    points, home, start = tuple(pro_data.values())[0].properties.values()
    cost = maxsize

    for permutation in permutations(points, subset_size):
        distance = pro_data[start][home].dist
        for begin, finish in zip((home,) + permutation, permutation):
            distance += pro_data[begin][finish].dist
        if distance < cost:
            cost, pro_order = distance, permutation

    return list((start, home) + pro_order), cost


def heldKarp(
    pro_data: Dict[Tuple[int, int], Map], subset_size: int
) -> Tuple[List[Any], int]:
    """Finds the shortest combination of paths between properties
    using Held Karp's algorithm.

    Args:
        pro_data (Dict[Tuple[int, int], Map]): Contains distances between
            all properties. Access via Dict[starting][destination].dist
        subset_size (int): number of points to visit (more than 1)

    Returns:
        Tuple[List[Any], int]: (order of properties' coordinates, distance)
    """

    points, home, start = tuple(pro_data.values())[0].properties.values()
    points = frozenset(points)

    key = Tuple[Tuple[int, int], FrozenSet[int]]
    value = Tuple[int, Tuple[int, int]]
    nodes = {}  # type: Dict[key, value]

    # get the shortest combinations of all sizes
    for row in range(subset_size):
        for comb in combinations(points, row):
            comb_set = frozenset(comb)
            for dest in points - comb_set:
                routes = []
                if comb_set == frozenset():  # case for home starting
                    cost = (
                        pro_data[home][dest].dist + pro_data[start][home].dist
                    )
                    nodes[dest, frozenset()] = cost, home
                else:
                    for begin in comb_set:  # single val from set
                        sub_comb = comb_set - frozenset({begin})
                        prev_cost = nodes[begin, sub_comb][0]
                        cost = pro_data[begin][dest].dist + prev_cost
                        routes.append((cost, begin))
                    nodes[dest, comb_set] = min(routes)

    # get final destination and its parent
    com = []
    for i, node in enumerate(reversed(dict(nodes))):
        if i < len(points):
            com.append((nodes.pop(node), node[0]))
        elif i == len(points):
            val, step = min(com)
            points -= {step}
            path = [step]
            cost, next_step = val
            break

    # backtrack remaining properties
    for _ in range(subset_size - 1):
        path.append(next_step)
        points -= {next_step}
        next_step = nodes[next_step, points][1]
    path.extend([home, start])

    return path[::-1], cost


def noComb(
    pro_data: Dict[Tuple[int, int], Map], subset_size: int
) -> Tuple[List[Any], int]:
    """Gets the shortest path between properties with 0 or 1 point.

    Args:
        pro_data (Dict[Tuple[int, int], Map]): Contains distances between
            all properties. Access via Dict[starting][destination].dist
        subset_size (int): number of points to visit (0 or 1 in this case)

    Returns:
        Tuple[List[Any], int]: (order of properties' coordinates, distance)
    """

    points, home, start = tuple(pro_data.values())[0].properties.values()
    pro_order, dist = [start, home], pro_data[start][home].dist
    if subset_size:
        point, dist_to_p = min([(p, pro_data[home][p].dist) for p in points])
        pro_order.append(point)
        dist += dist_to_p

    return pro_order, dist


def find_shortest_distances(
    map_data: Map, moves: List[Tuple[int, int]], climb: bool
) -> Dict[Tuple[int, int], Map]:
    """Finds shortest distances between all properties (start, home, points).
    Uses A* algorithm from start, from the others Dijkstra is used.

    Args:
        map_data (Map): contains information about the map
        moves (List[Tuple[int, int]]): movement options
        climb (bool): Climbing distance calculation approach. If True, distance
            is measured with abs(current terrain number - next terrain number)

    Returns:
        Dict[Tuple[int, int], Map]: Contains distances between all properties.
            Access via Dict[start][destination].dist
    """

    points, home, start = map_data.properties.values()

    from_start_to_home = a_star(deepcopy(map_data), moves, climb, start, home)
    from_home = dijkstra(deepcopy(map_data), moves, climb, home)
    from_points = {
        point: dijkstra(deepcopy(map_data), moves, climb, point)
        for point in points
    }

    shortest_distances_between_properties = {
        start: from_start_to_home,
        home: from_home,
        **from_points,
    }
    return shortest_distances_between_properties


def getPaths(
    pro_data: Dict[Tuple[int, int], Map], pro_order: List[Any]
) -> List[List[Tuple[int, int]]]:
    """Gets routes from ordered coordinates of properties via parent attribute.

    Args:
        pro_data (Dict[Tuple[int, int], Map]): Contains distances between
            all properties. Access via Dict[starting][destination].dist
        pro_order (List[Any]): order of properties' coordinates

    Returns:
        List[List[Tuple[int, int]]]: lists of paths between ordered properties
    """

    paths = []
    for begin, finish in zip(pro_order, pro_order[1:]):
        path = []
        while finish != begin:
            path.append(finish)
            finish = pro_data[begin][finish].parent
        paths.append(path[::-1])

    return paths


def printSolution(paths: List[List[Tuple[int, int]]], distance: int) -> None:
    """Prints the order of paths between properties. Each line starts with
    order number followed by order of tuple coordinates that represent
    the movement progression from start to destination.

    Args:
        paths (List[List[Tuple[int, int]]]): lists of paths between
            ordered properties
        distance (int): total distance of solution
    """

    for i, path in enumerate(paths, 1):
        print(f"{i}: ", *path)

    print("Cost: " + str(distance) + "\n")


def save_solution(comb_path: List[List[Tuple[int, int]]], fname: str) -> None:
    """Saves solution (path) of finding the shortest combination of path
    into pickle file.

    Args:
        comb_path (List[List[Tuple[int, int]]]): lists of paths between
            ordered properties
        fname (str): name of pickle file into which the solution
            will be saved
    """

    current_dir = dirname(dirname(os.path.abspath(__file__)))
    solutions_dir = f"{current_dir}\\data\\solutions"
    Path(solutions_dir).mkdir(parents=True, exist_ok=True)
    with open(f"{solutions_dir}\\{fname}_path", "wb") as f:
        pickle.dump(comb_path, f)


def validate_visit_points_amount(
    visit_points_amount: Union[int, None], map_points: List[Tuple[int, int]]
) -> int:
    """Validates and sets amount of points to visit. If its None or higher than
    the amount of points on the map, it will be reduced down to the map's
    amount.

    Args:
        visit_points_amount (Union[int, None]): Points we want to visit.
            None means all
        map_points (List[Tuple[int, int]]): coordinate points on the map

    Raises:
        SubsetSizeError: visit_points_amount is negative number

    Returns:
        int: amount of points that are going to be visited on the map
    """

    if visit_points_amount is None or visit_points_amount > len(map_points):
        visit_points_amount = len(map_points)
    if visit_points_amount < 0:
        raise SubsetSizeError("Invalid subset size!")

    return visit_points_amount


def validate_algorithm(algorithm: str, visit_points_amount: int) -> str:
    """Validates algorithm option and sets the algorithm.

    Args:
        algorithm (str): algorithm abbreviation
            Options: "NP", "HK" (Naive Permutations or Held Karp)
        visit_points_amount (int): number of points to visit

    Raises:
        AlgorithmError: wrong algorithm abbreviation string (NP or HK)

    Returns:
        str: algorithm abbreviation
    """

    if visit_points_amount < 2:
        algorithm = "NC"
    elif algorithm not in ("NC", "NP", "HK"):
        raise AlgorithmError("Invalid algorithm input!")

    return algorithm


def find_shortest_path(
    fname: str,
    movement_type: str,
    climb: bool,
    algorithm: str,
    visit_points_amount: Union[int, None],
) -> None:
    """Runs pathfinding algorithm on a map that is loaded from the text file.

    Args:
        fname (string): name of the file to load (with no suffix)
        movement_type (string): "M" - Manhattan, "D" - Diagonal + Manhattan
        climb (bool): Climbing distance approach. If True, distance is
            measured with abs(current terrain number - next terrain number)
        algorithm (string): algorithm abbreviation string
            Options: "NP", "HK" (Naive Permutations or Held Karp)
        visit_points_amount (Union[int, None]): amount of points to visit
            None means all
    """

    algorithm_opts = {
        "NC": noComb,
        "NP": naivePermutations,
        "HK": heldKarp,
    }

    try:
        # set up parameters for pathfinding algs
        map_data = Map(fname)
        moves = get_movement_possibilities(movement_type)
        visit_points_amount = validate_visit_points_amount(
            visit_points_amount, map_data.properties["points"]
        )
        # ? NC.. really? -> if nn, search for "and sets the algorithm" docstr
        algorithm = validate_algorithm(algorithm, visit_points_amount)

        # ! STAYING HERE NOW
        pro_data = find_shortest_distances(map_data, moves, climb)
        pro_order, dist = algorithm_opts[algorithm](
            pro_data, visit_points_amount
        )
        paths = getPaths(pro_data, pro_order)

        printSolution(paths, dist)
        save_solution(paths, fname)

    except FileNotFoundError as e:
        print(e)
    except MovementError as e:
        print(e)
    except SubsetSizeError as e:
        print(e)


if __name__ == "__main__":

    FNAME = "queried"
    MOVEMENT_TYPE = "M"
    CLIMB = False
    ALGORITHM = "HK"
    VISIT_POINTS_AMOUNT = None

    path_parameters = dict(
        fname=FNAME,
        movement_type=MOVEMENT_TYPE,
        climb=CLIMB,
        algorithm=ALGORITHM,
        visit_points_amount=VISIT_POINTS_AMOUNT,
    )  # type: Dict[str, Any]

    find_shortest_path(**path_parameters)
