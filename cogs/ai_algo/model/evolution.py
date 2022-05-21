import copy
import os
import pickle
import random
import re
import time
from pathlib import Path
from typing import Any, Dict, Generator, List, Tuple


class QueryError(Exception):
    pass


def evolutionize(
    map_list: List[List[int]], max_runs: int, print_stats: bool = True
) -> Tuple[List[List[int]], Dict[Tuple[int, int], int], bool]:
    """Runs evolutionary algorithm on a map with walls to fill it with terrain.

    Args:
        map_list (List[List[int]]): 2D map of 0 and 1 (walls) integers
        max_runs (int): max number of attempts to find solution with evo. alg.
        print_stats (bool, optional): turns on debug mode that prints stats
            and solution

    Returns:
        Tuple[List[List[int]], Dict[Tuple[int, int], int], bool]: (
            2D map of various integers (wall being -1 now),
            chromosome - solution that consist of genes,
            fact announcing if the solution was found or not
        )
    """

    found_solution = False
    attempt_number = 1

    while not found_solution and attempt_number <= max_runs:

        # convert map_list into dict of tuples
        map_tuple = {
            (i, j): -col
            for i, row in enumerate(map_list)
            for j, col in enumerate(row)
        }

        shape = len(map_list), len(map_list[0])
        rocks_amount = sum(val != 0 for val in map_tuple.values())
        to_rake_amount = shape[0] * shape[1] - rocks_amount
        genes_amount = (shape[0] + shape[1]) * 2

        CHROMOSOMES = 30  # chromosome - solution defined by genes
        GENERATIONS = 100  # generation - set of all chromosomes
        MIN_MUT_RATE = 0.05
        MAX_MUT_RATE = 0.80
        CROSS_RATE = 0.90

        # generating chromosomes for one population/generation
        population = []
        genes = random.sample(range(1, genes_amount), genes_amount - 1)
        for _ in range(CHROMOSOMES):
            random.shuffle(genes)
            chromosome = [num * random.choice([-1, 1]) for num in genes]
            population.append(chromosome)

        start_time = time.time()
        gen_times = []

        # loop of generations
        prev_max = 0
        mu_rate = MIN_MUT_RATE
        for i in range(GENERATIONS):
            generation_time = time.time()

            # evaluate all chromosomes and save the best one
            fit, fit_max, best_index = [], 0, 0
            for j in range(CHROMOSOMES):
                unraked_amount, filled_map, tmp_rake_paths = rakeMap(
                    population[j], copy.copy(map_tuple), shape
                )
                raked_amount = to_rake_amount - unraked_amount
                fit.append(raked_amount)
                if raked_amount > fit_max:
                    best_index, fit_max = j, raked_amount
                    terr_map, rake_paths = filled_map, tmp_rake_paths

            if prev_max < fit_max:
                print(f"Generation: {i+1},", end="\t")
                print(f"Raked: {fit_max} (out of {to_rake_amount})", end="\t")
                print(f"Mutation rate: {round(mu_rate, 2)}")
            if fit_max == to_rake_amount:
                found_solution = True
                gen_times.append(time.time() - generation_time)
                break

            # increase mutation rate each generation to prevent local maximums
            mu_rate = mu_rate if mu_rate >= MAX_MUT_RATE else mu_rate + 0.01

            # next generation creating, 1 iteration for 2 populations
            children = []  # type: List[Any]
            for i in range(0, CHROMOSOMES, 2):

                # pick 2 better chromosomes out of 4
                pick = random.sample(range(CHROMOSOMES), 4)
                better1 = pick[0] if fit[pick[0]] > fit[pick[1]] else pick[1]
                better2 = pick[2] if fit[pick[2]] > fit[pick[3]] else pick[3]

                # copying better genes to 2 child chromosomes
                children.extend([[], []])
                for j in range(genes_amount - 1):
                    children[i].append(population[better1][j])
                    children[i + 1].append(population[better2][j])

                # mutating 2 chromosomes with uniform crossover
                # (both inherit the same amount of genetic info)
                if random.random() < CROSS_RATE:
                    for c in range(2):
                        for g in range(genes_amount - 1):
                            if random.random() < mu_rate:

                                # search for gene with mut_num number
                                mut_num = random.randint(1, genes_amount)
                                mut_num *= random.choice([-1, 1])
                                f = 0
                                for k, gene in enumerate(children[i + c]):
                                    if gene == mut_num:
                                        f = k

                                # swap it with g gene, else replace g with it
                                if f:
                                    tmp = children[i + c][g]
                                    children[i + c][g] = children[i + c][f]
                                    children[i + c][f] = tmp
                                else:
                                    children[i + c][g] = mut_num

            # keep the best chromosome for next generation
            for i in range(genes_amount - 1):
                children[0][i] = population[best_index][i]

            population = children
            prev_max = fit_max
            gen_times.append(time.time() - generation_time)

        # printing stats, solution and map
        if print_stats:
            total = round(time.time() - start_time, 2)
            avg = round(sum(gen_times) / len(gen_times), 2)
            chromo = " ".join(map(str, population[best_index]))
            answer = "found" if found_solution else "not found"
            print(f"Solution is {answer}!")
            print(f"Total time elapsed is {total}s,", end="\t")
            print(f"each generation took {avg}s in average.")
            print(f"Chromosome: {chromo}")

            attempt_number += 1
            if not found_solution and attempt_number <= max_runs:
                print(f"\nAttempt number {attempt_number}.")

    return terr_map, rake_paths, found_solution


def rakeMap(
    chromosome: List[int],
    map_tuple: Dict[Tuple[int, int], int],
    shape: Tuple[int, int],
) -> Tuple[int, List[List[int]], Dict[Tuple[int, int], int]]:
    """Attempts to fill the map terrain with chromosome that is defined
    by the order of instructions known as genes.

    Args:
        chromosome (List[int]): ordered set of genes (instructions)
        map_tuple (Dict[Tuple[int, int], int]): map defined by tuples
            of (x, y) being as coordinate keys
        shape (Tuple[int, int]): height and width lengths of the map

    Returns:
        Tuple[int, List[List[int]], Dict[Tuple[int, int], int]]:
            (amount of unraked spots, terrained map, raking paths)
    """

    rows, cols = shape
    half_perimeter = sum(shape)
    UNRAKED = 0
    parents = {}  # type: Dict[Any, Any]
    rake_paths = {}  # type: Dict[Tuple[int, int], int]
    pos = 0  # type: Any
    order = 1

    for gene in chromosome:

        # get starting position and movement direction
        pos_num = abs(gene)
        if pos_num <= cols:  # go DOWN
            pos, move = (0, pos_num - 1), (1, 0)
        elif pos_num <= half_perimeter:  # go RIGHT
            pos, move = (pos_num - cols - 1, 0), (0, 1)
        elif pos_num <= half_perimeter + rows:  # go LEFT
            pos, move = (pos_num - half_perimeter - 1, cols - 1), (0, -1)
        else:  # go UP
            pos, move = (
                (rows - 1, pos_num - half_perimeter - rows - 1),
                (-1, 0),
            )

        # checking whether we can enter the garden with current pos
        if map_tuple[pos] == UNRAKED:
            parents = {}
            parent = 0

            # move until we reach end of the map
            while 0 <= pos[0] < rows and 0 <= pos[1] < cols:

                # collision to raked sand/rock
                if map_tuple[pos] != UNRAKED:
                    pos = parent  # get previous pos
                    parent = parents[pos]  # get previous parent

                    # change moving direction
                    if move[0] != 0:  # Y -> X
                        R_pos = pos[0], pos[1] + 1
                        L_pos = pos[0], pos[1] - 1
                        R_inbound = R_pos[1] < cols
                        L_inbound = L_pos[1] >= 0
                        R_free = R_inbound and map_tuple[R_pos] == UNRAKED
                        L_free = L_inbound and map_tuple[L_pos] == UNRAKED

                        if R_free and L_free:
                            move = (0, 1) if gene > 0 else (0, -1)
                        elif R_free:
                            move = 0, 1
                        elif L_free:
                            move = 0, -1
                        elif R_inbound and L_inbound:
                            move = 0, 0
                        else:
                            break  # reached end of the map so we can leave

                    else:  # X -> Y
                        D_pos = pos[0] + 1, pos[1]
                        U_pos = pos[0] - 1, pos[1]
                        D_inbound = D_pos[0] < rows
                        U_inbound = U_pos[0] >= 0
                        D_free = D_inbound and map_tuple[D_pos] == UNRAKED
                        U_free = U_inbound and map_tuple[U_pos] == UNRAKED

                        if D_free and U_free:
                            move = (1, 0) if gene > 0 else (-1, 0)
                        elif D_free:
                            move = 1, 0
                        elif U_free:
                            move = -1, 0
                        elif D_inbound and U_inbound:
                            move = 0, 0
                        else:
                            break

                    # if we cant change direction, remove the path
                    if not any(move):
                        order -= 1
                        while parents[pos] != 0:
                            map_tuple[pos] = 0
                            pos = parents[pos]
                        map_tuple[pos] = 0
                        break

                # save the order num and parent, move by setting new pos
                map_tuple[pos] = order
                parents[pos] = parent
                parent = pos
                pos = pos[0] + move[0], pos[1] + move[1]

            # save paths for visualization
            if any(move):
                rake_path = {key: order for key in parents}
                rake_paths = {**rake_paths, **rake_path}
            order += 1

    filled_map = []  # type: List[List[int]]
    unraked_amount = 0
    row_number = -1

    for i, order_num in enumerate(map_tuple.values()):
        if order_num == UNRAKED:
            unraked_amount += 1
        if i % cols == 0:
            row_number += 1
            filled_map.append([])
        filled_map[row_number].append(order_num)

    return unraked_amount, filled_map, rake_paths


def generate_properties(
    map_list: List[List[str]], points_count: int
) -> List[List[str]]:
    """Adds properties to terrained map.

    Properties are represented with a bracket around the number of terrain.
    {} - starting position, [] - first position to visit, () - point to visit.

    Args:
        map_list (List[List[str]]): 2D terrained map that will be propertied
        points_count (int): amount of destination points to visit

    Returns:
        List[List[str]]: 2D propertied map
    """

    def free_position_finder(
        terrained_map: List[List[str]],
    ) -> Generator[Tuple[int, int], None, None]:
        """Finder of free positions for properties.

        Args:
            terrained_map (List[List[str]]): 2D terrained map

        Yields:
            Generator[Tuple[int, int], None, None]: coordinate of free position
        """

        reserved = set()
        for i, row in enumerate(terrained_map):
            for j, col in enumerate(row):
                if int(col) < 0:
                    reserved.add((i, j))

        while True:
            i = random.randint(0, len(terrained_map) - 1)
            j = random.randint(0, len(terrained_map[0]) - 1)
            if (i, j) not in reserved:
                reserved.add((i, j))
                yield (i, j)

    free = free_position_finder(map_list)

    first_i, first_j = next(free)
    start_i, start_j = next(free)
    map_list[first_i][first_j] = "[" + map_list[first_i][first_j] + "]"
    map_list[start_i][start_j] = "{" + map_list[start_i][start_j] + "}"
    for _ in range(points_count):
        i, j = next(free)
        map_list[i][j] = "(" + map_list[i][j] + ")"

    return map_list


def save_map(
    fname: str,
    map_list: List[List[str]],
    show: bool = False,
    spacing: str = "{:^3}",
) -> None:
    """Saves a map from 2D list array of strings into file.

    Args:
        fname (str): name of the file into which the map is going to be saved.
        map_list (List[List[str]]): 2D map
        show (bool, optional): Option to print saved map into console.
            Defaults to False.
        spacing (str, optional): Spacing between map values.
            Defaults to "{:^3}".
    """

    source_dir = Path(__file__).parents[1]
    map_dir = Path(f"{source_dir}/data/maps")
    map_dir.mkdir(parents=True, exist_ok=True)

    fname_path = Path(f"{map_dir}/{fname}.txt")
    with open(fname_path, "w", encoding="utf-8") as file:
        for i, row in enumerate(map_list):
            for j in range(len(row)):
                file.write(spacing.format(map_list[i][j]))
                if show:
                    print(spacing.format(map_list[i][j]), end=" ")
            file.write("\n")
            if show:
                print()


def load_map(fname: str, suffix: str) -> List[List[str]]:
    """Loads a map from file into 2D list array of strings.

    Args:
        fname (str): name of the file to load (with _wal/_ter/_pro suffix)
        suffix (str): Suffix of fname.
            Options: "walls", "terrain", "properties"

    Returns:
        List[List[str]]: 2D map
    """

    source_dir = Path(__file__).parents[1]
    fname_path = Path(f"{source_dir}/data/maps/{fname}{suffix}.txt")
    map_ = []
    try:
        with open(fname_path, encoding="utf-8") as file:
            line = file.readline().rstrip()
            map_.append(line.split())
            prev_length = len(line)

            for line in file:
                line = line.rstrip()
                if prev_length != len(line):
                    map_ = []
                    break
                map_.append(line.split())
                prev_length = len(line)
    except FileNotFoundError:
        map_ = []

    return map_


def save_solution(rake_paths: Dict[Tuple[int, int], int], fname: str) -> None:
    """Saves solution (paths) of evolutionary alg. into pickle file.

    Args:
        rake_paths (Dict[Tuple[int, int], int]): order of raking the map
        fname (str): name of pickle file into which the solution will be saved
    """

    source_dir = Path(__file__).parents[1]
    solutions_dir = Path(f"{source_dir}\\data\\solutions")
    Path(solutions_dir).mkdir(parents=True, exist_ok=True)
    fname_path = Path(f"{solutions_dir}/{fname}_rake.txt")
    with open(fname_path, "wb") as file:
        pickle.dump(rake_paths, file)


def create_walls(fname: str, query: str, show: bool = False) -> None:
    """Creates a file that represents walled map.

    Map is filled with "1" being walls and "0" being walkable space.

    Args:
        fname (str): name of the file that is going to be created
        query (str): Contains size of map and coordinates of walls.
            Option: "10x12 (1,5) (2,1) (3,4) (4,2) (6,8) (6,9")
        show (bool, optional): Option to print created walls into console.
            Defaults to False.

    Raises:
        QueryError: query does not match regular expression
    """

    walled_map = []
    if re.search(r"[0-9]+x[0-9]+(\ \([0-9]+,[0-9]+\))+$", query):
        query_split = query.split()
        row_count, col_count = map(int, query_split[0].split("x"))
        walled_map = [["0"] * col_count for _ in range(row_count)]
        wall_coordinates = query_split[1:]

        for wall_coordinate in wall_coordinates:
            x, y = map(int, wall_coordinate[1:-1].split(","))
            try:
                walled_map[x][y] = "1"
            except IndexError:
                walled_map = []

    if not walled_map:
        raise QueryError("Invalid query!")

    walled_fname = fname + "_wal"
    save_map(walled_fname, walled_map, show)


def create_terrain(fname: str, max_runs: int, show: bool = False) -> str:
    """Creates a file that represents terrained map with walls.

    Map is filled with "-1" being walls and walkable places are filled
    with various numbers generated by evolutionary algorithm.

    Args:
        fname (str): name of the file that is going to be created
        max_runs (int): max number of attempts to find solution with evo. alg.
        show (bool, optional): Option to print created terrain into console.
            Defaults to False.

    Raises:
        FileNotFoundError: file does not exist

    Returns:
        str: message announcing whether the solution was found or not
    """

    walled_map = load_map(fname, "_wal")
    if not walled_map:
        raise FileNotFoundError("Invalid file name for creating terrain!")

    map_list = [list(map(int, subarray)) for subarray in walled_map]
    # TODO: evo deep check
    map_list, rake_paths, solution = evolutionize(map_list, max_runs)

    # TODO: mark remaining unraked space with -2 (why actually?), add to docstring
    terrained_map = [
        [str(i) if i else "-2" for i in subarray] for subarray in map_list
    ]

    save_solution(rake_paths, fname)  # TODO: after evolutionize checkout -> check docstring here

    terrained_fname = fname + "_ter"
    save_map(terrained_fname, terrained_map, show)

    return "Solution was found." if solution else "Solution was not found."


def create_properties(
    fname: str,
    points_count: int,
    show: bool = False,
) -> None:
    """Creates a file that represents propertied map with walls and terrain.

    Args:
        points_count (int): amount of destination points to visit
        fname (str): name of the file that is going to be created
        show (bool, optional): Option to print created properties into
            console. Defaults to False.

    Raises:
        FileNotFoundError: file does not exist
    """

    terrained_map = load_map(fname, "_ter")
    if not terrained_map:
        raise FileNotFoundError("Invalid import name for creating properties!")

    propertied_map = generate_properties(terrained_map, points_count)

    propertied_fname = fname + "_pro"
    save_map(propertied_fname, propertied_map, show, "{:^5}")


def create_maps(
    fname: str,
    begin_from: str,
    query: str,
    max_runs: int,
    points_count: int,
) -> None:
    """
    Creates and saves variously filled maps into text files.

    There are three dependant stages of creating a complete map. Each stage
    uses map that was created and saved into text file from the previous stage
    We can start from any stage as long as the previous one was run. (except
    for the first one). All remaining stages will run after that.

    Args:
        fname (str): name of the file(s) that is/are going to be created
        begin_from (str): Defines which stage to start from.
            Options: "walls", "terrain", "properties"
        query (str): Contains size of map and coordinates of walls.
            Option: "10x12 (1,5) (2,1) (3,4) (4,2) (6,8) (6,9)"
        max_runs (int): max number of attempts to find solution with evo. alg.
        points_count (int): amount of destination points to visit
    """

    next_ = False
    try:
        if begin_from == "walls":
            create_walls(fname, query)
            next_ = True
        if begin_from == "terrain" or next_:
            create_terrain(fname, max_runs)
            next_ = True
        if begin_from == "properties" or next_:
            create_properties(fname, points_count, show=True)
    except QueryError as err:
        print(err)
    except FileNotFoundError as err:
        print(err)


if __name__ == "__main__":

    # walls uses: query, fname, max_runs, points_count
    # terrain uses: fname, max_runs, points_count
    # properties uses: fname, points_count
    begin_from = "walls"
    query = "10x12 (1,5) (2,1) (3,4) (4,2) (6,8) (6,9) (6,9)"
    fname = "queried"
    max_runs = 3
    points_count = 10

    evo_parameters = dict(
        begin_from=begin_from,
        query=query,
        fname=fname,
        max_runs=max_runs,
        points_count=points_count,
    )  # type: Dict[str, Any]

    create_maps(**evo_parameters)
