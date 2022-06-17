import heapq
import pickle
from copy import deepcopy
from itertools import combinations, permutations
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
    fname = ""  # type: str
    width = 0  # type: int
    height = 0  # type: int
    properties = {}  # type: Dict[str, Any]

    def __init__(self, fname) -> None:
        self.nodes = {}  # type: Dict[Tuple[int, int], Node]
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
            Map.fname = fname
            Map.height = height + 1
            Map.width = width + 1
            Map.properties = properties
            self.nodes = nodes

    def __getitem__(self, pos):
        assert len(pos) == 2, "Coordinate must have two values."
        if not (0 <= pos[0] < self.height and 0 <= pos[1] < self.width):
            raise PositionError(str(pos))
        return self.nodes[pos]


def passable(next_pos: Tuple[int, int], nodes_map: Map):
    """Checks whether next_pos position is passable (not walled or out of map).

    Args:
        next_pos (Tuple[int, int]): position on which movement was applied
        nodes_map (Map): contains information about the map

    Returns:
        bool: passability
    """

    return (
        0 <= next_pos[0] < nodes_map.height
        and 0 <= next_pos[1] < nodes_map.width
        and not nodes_map[next_pos].terr < 0
    )


def get_next_dist(prev_terr: int, next_terr: int, climb: bool) -> int:
    """Gets next distance based on whether its climbing approach or not.

    Args:
        prev_terr (int): terrain of position from which we move
        next_terr (int): terrain of position to which we move
        climb (bool): Climbing distance calculation approach. If True, distance
            is measured with abs(current terrain number - next terrain number)

    Returns:
        int: distance to the next position
    """

    if climb:
        return abs(prev_terr - next_terr) + 1
    else:
        return next_terr


def dijkstra(
    nodes_map: Map,
    moves: List[Tuple[int, int]],
    climb: bool,
    start: Tuple[int, int],
) -> Map:
    """Finds and saves the shortest path from start to all destinations.

    Args:
        nodes_map (Map): contains information about the map
        moves (List[Tuple[int, int]]): movement options
        climb (bool): Climbing distance calculation approach. If True, distance
            is measured with abs(current terrain number - next terrain number)
        start (Tuple[int, int]): starting position

    Returns:
        Map: Contains distances from start to all destinations.
            Access via Map[start][destination].dist
    """

    nodes = deepcopy(nodes_map.nodes)
    nodes[start].dist = 0
    heap = []  # type: List[Node]
    heapq.heappush(heap, nodes[start])

    while heap:
        node = heapq.heappop(heap)
        for move in moves:
            next_pos = node.pos[0] + move[0], node.pos[1] + move[1]
            if passable(next_pos, nodes_map):
                next_node = nodes[next_pos]
                step_dist = get_next_dist(node.terr, next_node.terr, climb)
                next_node_dist = node.dist + step_dist

                if next_node.dist > next_node_dist:
                    next_node.dist = next_node_dist
                    next_node.parent = node.pos
                    heapq.heappush(heap, next_node)

    return nodes


def a_star(
    nodes_map: Map,
    moves: List[Tuple[int, int]],
    climb: bool,
    start: Tuple[int, int],
    dest: Tuple[int, int],
) -> Map:
    """Finds and saves the shortest path from start to destination.

    Args:
        nodes_map (Map): contains information about the map
        moves (List[Tuple[int, int]]): movement options
        climb (bool): Climbing distance calculation approach. If True, distance
            is measured with abs(current terrain number - next terrain number)
        start (Tuple[int, int]): starting position
        dest (Tuple[int, int]): ending position

    Returns:
        Map: Contains distance from start to destination.
            Access via Map[start][destination].dist
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
            if passable(next_pos, nodes_map) and next_pos not in close_list:
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


def naive_permutations(
    nodes_map: Dict[Tuple[int, int], Map], subset_size: int
) -> Tuple[List[Any], int]:
    """Computes the distance between all possible combinations of property
    nodes in order to find the shortest paths.

    Args:
        nodes_map (Dict[Tuple[int, int], Map]): Contains distances between
            all properties. Access via Dict[starting][destination].dist
        subset_size (int): number of points to visit (more than 1)

    Returns:
        Tuple[List[Any], int]: (order of properties' coordinates, distance)
    """

    points, home, start = tuple(nodes_map.values())[0].properties.values()
    # points2, home2, start2 = nodes_map.properties.values() DO SOMETHING ABOUT THIS!
    cost = maxsize

    for permutation in permutations(points, subset_size):
        distance = nodes_map[start][home].dist
        for begin, finish in zip((home,) + permutation, permutation):
            distance += nodes_map[begin][finish].dist
        if distance < cost:
            cost, pro_order = distance, permutation

    return list((start, home) + pro_order), cost


def held_karp(
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

    points, home, start = pro_data.properties.values()
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


def no_comb(
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
    nodes_map: Map, moves: List[Tuple[int, int]], climb: bool
) -> Dict[Tuple[int, int], Map]:
    """Finds shortest distances between all properties (start, home, points).
    Uses A* algorithm from start, from the others Dijkstra is used.

    Args:
        nodes_map (Map): contains information about the map
        moves (List[Tuple[int, int]]): movement options
        climb (bool): Climbing distance calculation approach. If True, distance
            is measured with abs(current terrain number - next terrain number)

    Returns:
        Dict[Tuple[int, int], Node]: Contains distances between all properties.
            Access via Dict[start][destination].dist
    """

    points, home, start = nodes_map.properties.values()

    from_start_to_home = a_star(nodes_map, moves, climb, start, home)
    from_home_to_all = dijkstra(nodes_map, moves, climb, home)
    from_points_to_all = {
        point: dijkstra(nodes_map, moves, climb, point)
        for point in points
    }

    shortest_distance_nodes_between_properties = {
        start: from_start_to_home,
        home: from_home_to_all,
        **from_points_to_all,
    }

    # been creating maps for every property
    # every map had access to all nodes, which was not needed
    # reduced to just one map, and only have propertied nodes!
    nodes_map.nodes = shortest_distance_nodes_between_properties

    return nodes_map


def get_paths(
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


def print_solution(paths: List[List[Tuple[int, int]]], distance: int) -> None:
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
    """Saves solution (path) of the shortest distance combination between nodes
    into pickle file.

    Args:
        comb_path (List[List[Tuple[int, int]]]): lists of paths between
            ordered properties
        fname (str): name of pickle file into which the solution
            will be saved
    """

    source_dir = Path(__file__).parents[1]
    solutions_dir = Path(f"{source_dir}/data/solutions")
    solutions_dir.mkdir(parents=True, exist_ok=True)

    fname_path = Path(f"{solutions_dir}/{fname}_path")
    with open(fname_path, "wb") as f:
        pickle.dump(comb_path, f)


def validate_and_set_input_pars(
    movement_type: str,
    visit_points_amount: Union[int, None],
    nodes_mappoints: List[Tuple[int, int]],
    algorithm: str,
) -> Tuple[List[Tuple[int, int]], int, str]:
    """Validates and sets parameters from input for pathfinding algorithms.
    
    Gets movement possibilities from either Manhattan or Diagonal + Manhattan
    approach.
    Validates and sets amount of points to visit. If its None or higher than
    the amount of points on the map, it will be reduced down to the map's
    amount.
    Validates algorithm option and sets the algorithm.

    Args:
        movement_type (str): movement_type (str): determines the type of movement options
            Options: "M", "D"
        visit_points_amount (Union[int, None]): Points we want to visit. / number of points to visit
            None means all
        nodes_mappoints (List[Tuple[int, int]]): coordinate points on the map
        algorithm (str): algorithm abbreviation
            Options: "NP", "HK" (Naive Permutations or Held Karp)

    Raises:
        MovementError: movement_type has not "M" or "N" set
        SubsetSizeError: visit_points_amount is negative number
        AlgorithmError: wrong algorithm abbreviation string (NP or HK)

    Returns:
        Tuple[List[Tuple[int, int]], int, str]: (
            list of tuple coordinate movement options
            amount of points that are going to be visited on the map
            algorithm abbreviation
        )
    """

    # validate and get movement possibilities
    moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if movement_type == "D":
        moves += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    elif movement_type != "M":
        raise MovementError("Invalid movement type!")

    # validate visit_points_amount
    if visit_points_amount is None or visit_points_amount > len(nodes_mappoints):
        visit_points_amount = len(nodes_mappoints)
    if visit_points_amount < 0:
        raise SubsetSizeError("Invalid subset size!")

    # validate algorithm
    # ? NC.. really? -> if nn, search for "and sets the algorithm" docstr
    if visit_points_amount < 2:
        algorithm = "NC"
    elif algorithm not in ("NC", "NP", "HK"):
        raise AlgorithmError("Invalid algorithm input!")

    return moves, visit_points_amount, algorithm


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
        climb (bool): Climbing distance calculation approach. If True, distance
            is measured with abs(current terrain number - next terrain number)
        algorithm (string): algorithm abbreviation string
            Options: "NP", "HK" (Naive Permutations or Held Karp)
        visit_points_amount (Union[int, None]): amount of points to visit
            None means all
    """

    alg_opts = {
        "NC": no_comb,
        "NP": naive_permutations,
        "HK": held_karp,
    }

    try:
        # set up parameters for pathfinding algs
        nodes_map = Map(fname)
        moves, visit_points_amount, algorithm = validate_and_set_input_pars(
            movement_type,
            visit_points_amount,
            nodes_map.properties["points"],
            algorithm,
        )

        nodes_map = find_shortest_distances(nodes_map, moves, climb)
        # ! START HERE
        pro_order, dist = alg_opts[algorithm](nodes_map, visit_points_amount)
        paths = get_paths(nodes_map, pro_order)

        print_solution(paths, dist)

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
    VISIT_POINTS_AMOUNT = None  # bug.. doesnt work with numbers

    path_parameters = dict(
        fname=FNAME,
        movement_type=MOVEMENT_TYPE,
        climb=CLIMB,
        algorithm=ALGORITHM,
        visit_points_amount=VISIT_POINTS_AMOUNT,
    )  # type: Dict[str, Any]

    find_shortest_path(**path_parameters)
