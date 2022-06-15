import copy
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
        map_list (List[List[int]]): 2D walled map that will be terrained
        max_runs (int): max number of attempts to find solution with evo. alg.
        print_stats (bool, optional): Turns on debug mode that prints stats
            and solution. Defaults to True.

    Returns:
        Tuple[List[List[int]], Dict[Tuple[int, int], int], bool]: (
            2D map with integers indicating terrain (wall being -1 now),
            chromosome - solution that consist of genes,
            fact announcing if the solution was found or not
        )
    """

    found_solution = False
    attempt_number = 1

    while not found_solution and attempt_number <= max_runs:

        # simplify 2D map_list into 1D dict
        map_tuple = {
            (i, j): -col
            for i, row in enumerate(map_list)
            for j, col in enumerate(row)
        }

        rows, cols = len(map_list), len(map_list[0])
        rocks_amount = sum(map(sum, map_list))
        to_rake_amount = rows * cols - rocks_amount
        map_perimeter = (rows + cols) * 2

        CHROMOSOMES = 30  # chromosome - solution defined by genes
        GENERATIONS = 100  # generation - set of all chromosomes
        MIN_MUT_RATE = 0.05
        MAX_MUT_RATE = 0.80
        CROSS_RATE = 0.90

        # generating chromosome for first generation/population
        population = []
        genes = random.sample(range(map_perimeter - 1), map_perimeter - 1)
        for _ in range(CHROMOSOMES):
            random.shuffle(genes)
            chromosome = [num * random.choice([-1, 1]) for num in genes]
            population.append(chromosome)

        start_time = time.time()
        generation_times = []

        # loop over generations - evolution
        prev_max = 0
        mut_rate = MIN_MUT_RATE
        for i in range(GENERATIONS):
            generation_time = time.time()

            # evaluate all chromosomes and save the best one
            fit_vals, fit_max, fit_max_index = [], 0, 0
            for j in range(CHROMOSOMES):
                map_tuple_filled, raking_paths = rake_map(
                    population[j], copy.copy(map_tuple), rows, cols
                )

                unraked_count = list(map_tuple_filled.values()).count(0)
                raked_count = to_rake_amount - unraked_count
                fit_vals.append(raked_count)
                if raked_count > fit_max:
                    fit_max = raked_count
                    fit_max_map = map_tuple_filled
                    fit_max_path = raking_paths
                    fit_max_index = j

            if prev_max < fit_max:
                print(f"Generation: {i+1},", end="\t")
                print(f"Raked: {fit_max} (out of {to_rake_amount})", end="\t")
                print(f"Mutation rate: {round(mut_rate, 2)}")
            if fit_max == to_rake_amount:
                found_solution = True
                generation_times.append(time.time() - generation_time)
                break

            # increase mutation rate each generation to prevent local maximum
            mut_rate = mut_rate + 0.01 if mut_rate < MAX_MUT_RATE else MAX_MUT_RATE

            # creating next generation, 1 iteration for 2 populations
            children = []  # type: List[Any]
            for i in range(0, CHROMOSOMES, 2):

                # pick 2 winning chromosomes out of 4
                pick = random.sample(range(CHROMOSOMES), 4)
                win1 = pick[0] if fit_vals[pick[0]] > fit_vals[pick[1]] else pick[1]
                win2 = pick[2] if fit_vals[pick[2]] > fit_vals[pick[3]] else pick[3]

                # copying winning chromosomes into 2 children
                children.extend([[], []])
                for j in range(map_perimeter - 1):
                    children[i].append(population[win1][j])
                    children[i + 1].append(population[win2][j])

                if random.random() > CROSS_RATE:
                    continue

                # mutating 2 chromosomes with uniform crossover
                # (both inherit the same amount of genetic info)
                for j in range(2):
                    for rand_index in range(map_perimeter - 1):
                        if random.random() < mut_rate:

                            # create random gene, search for such gene in children
                            rand_val = random.randint(0, map_perimeter - 1)
                            rand_val *= random.choice([-1, 1])

                            # try to find such gene in children
                            if rand_val in children[i + j]:
                                found_gene_index = children[i + j].index(rand_val)
                            else:
                                found_gene_index = 0

                            # swap it with g gene if it was found
                            if found_gene_index:
                                tmp = children[i + j][rand_index]
                                children[i + j][rand_index] = children[i + j][found_gene_index]
                                children[i + j][found_gene_index] = tmp
                            # replace it with rand_val
                            else:
                                children[i + j][rand_index] = rand_val

            # keep the best chromosome for next generation
            for i in range(map_perimeter - 1):
                children[0][i] = population[fit_max_index][i]

            population = children
            prev_max = fit_max
            generation_times.append(time.time() - generation_time)

        # printing stats, solution and map
        if print_stats:
            total = round(time.time() - start_time, 2)
            avg = round(sum(generation_times) / len(generation_times), 2)
            chromo = " ".join(map(str, population[fit_max_index]))
            answer = "found" if found_solution else "not found"
            print(f"Solution is {answer}!")
            print(f"Total time elapsed is {total}s,", end="\t")
            print(f"each generation took {avg}s in average.")
            print(f"Chromosome: {chromo}")

            attempt_number += 1
            if not found_solution and attempt_number <= max_runs:
                print(f"\nAttempt number {attempt_number}.")

    # add the conversion of map here! it is faster with tuples...
    # TODO:   map_tuple_filled
    filled_map = []  # type: List[List[int]]
    row_number = -1
    for i, terrain_num in enumerate(terr_map.values()):  # fit_max_map
        if i % cols == 0:
            row_number += 1
            filled_map.append([])
        filled_map[row_number].append(terrain_num)

    return filled_map, rake_paths, found_solution

def get_start_pos(
    gene: int, rows: int, cols: int
) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """Gets start position and movement direction.

    Args:
        gene (int): instruction that defines the starting movement
            and position coordinate that is number number between 
            (0) and (perimeter - 1)
        rows (int): amount of rows in the map (helping variable)
        cols (int): amount of cols in the map (helping variable)

    Returns:
        Tuple[Tuple[int, int], Tuple[int, int]]: 
            (start position coordinate, movement direction coordinate)
    """

    half_perimeter = rows + cols
    
    pos_num = abs(gene)
    if pos_num < cols:  # go DOWN
        pos, move = (0, pos_num), (1, 0)
    elif pos_num < half_perimeter:  # go RIGHT
        pos, move = (pos_num - cols, 0), (0, 1)
    elif pos_num < half_perimeter + rows:  # go LEFT
        pos, move = (pos_num - half_perimeter, cols - 1), (0, -1)
    else:  # go UP
        pos, move = (
            (rows - 1, pos_num - half_perimeter - rows),
            (-1, 0),
        )
    
    return pos, move


def get_row_movement(
    pos: Tuple[int, int],
    cols: int,
    map_tuple: Dict[Tuple[int, int], int],
    gene: int,
) -> Tuple[int, int]:
    """Gets next movement coordinate that changes positions between columns.

    Args:
        pos (Tuple[int, int]): current position we are at
        cols (int): amount of cols in the map
        map_tuple (Dict[Tuple[int, int], int]): map defined by dict with:
            keys being tuples as coordinates, 
            value being values of terrain (0 is unraked)
        gene (int): instruction that also carries the information about which
            direction to choose in case of having two movement possibilities

    Returns:
        Tuple[int, int]: movement direction coordinate
    """

    R_pos = pos[0], pos[1] + 1
    L_pos = pos[0], pos[1] - 1
    R_inbound = R_pos[1] < cols
    L_inbound = L_pos[1] >= 0
    R_free = R_inbound and not map_tuple[R_pos]
    L_free = L_inbound and not map_tuple[L_pos]

    # if both ways are free, the gene will decide where to go
    if R_free and L_free:
        move = (0, 1) if gene > 0 else (0, -1)

    elif R_free:
        move = 0, 1
    elif L_free:
        move = 0, -1

    # we are in bounds of the map, but we cannot move anywhere
    elif R_inbound and L_inbound:
        move = 0, 0

    # one movement side is out of bounds, which means we can leave the map
    else:
        move = 1, 1

    return move


def get_col_movement(
    pos: Tuple[int, int],
    rows: int,
    map_tuple: Dict[Tuple[int, int], int],
    gene: int,
) -> Tuple[int, int]:
    """Gets next movement coordinate that changes positions between columns.

    Args:
        pos (Tuple[int, int]): current position we are at
        rows (int): amount of rows in the map
        map_tuple (Dict[Tuple[int, int], int]): map defined by dict with:
            keys being tuples as coordinates, 
            value being values of terrain (0 is unraked)
        gene (int): instruction that also carries the information about which
            direction to choose in case of having two movement possibilities

    Returns:
        Tuple[int, int]: movement direction coordinate
    """

    D_pos = pos[0] + 1, pos[1]
    U_pos = pos[0] - 1, pos[1]
    D_inbound = D_pos[0] < rows
    U_inbound = U_pos[0] >= 0
    D_free = D_inbound and not map_tuple[D_pos]
    U_free = U_inbound and not map_tuple[U_pos]

    if D_free and U_free:
        move = (1, 0) if gene > 0 else (-1, 0)
    elif D_free:
        move = 1, 0
    elif U_free:
        move = -1, 0
    elif D_inbound and U_inbound:
        move = 0, 0
    else:
        move = 1, 1

    return move


def in_bounds(pos: Tuple[int, int], rows: int, cols: int) -> bool:
    """Checks whether current position is not out of bounds of the map.

    Args:
        pos (Tuple[int, int]): current position we are at
        rows (int): amount of rows in the map
        cols (int): amount of cols in the map

    Returns:
        bool: indicates rake availability
    """
    
    return 0 <= pos[0] < rows and 0 <= pos[1] < cols


def rake_map(
    chromosome: List[int],
    map_tuple: Dict[Tuple[int, int], int],
    rows: int,
    cols: int,
) -> Tuple[int, List[List[int]], Dict[Tuple[int, int], int]]:
    """Rakes the map with terrain by chromosome that consists of instructions
    known as genes. 
    Each gene defines the starting position and directionof raking.

    Args:
        chromosome (List[int]): ordered set of genes (instructions)
        map_tuple (Dict[Tuple[int, int], int]): map defined by dict with:
            keys being tuples as coordinates, 
            value being values of terrain (0 is unraked)
        rows (int): amount of rows in the map
        cols (int): amount of cols in the map

    Returns:
        Tuple[List[List[int]], Dict[Tuple[int, int], int]]:
            (terrained map, raking path)
    """

    rake_paths = {}  # type: Dict[Tuple[int, int], int]
    terrain_num = 1  # first raking number

    for gene in chromosome:
        pos, move = get_start_pos(gene, rows, cols)
        
        # collision check (to rock or raked sand)
        if map_tuple[pos]:
            continue
        
        parents = {}  # type: Dict[Any, Any]
        parent = 0
        while in_bounds(pos, rows, cols):
            if map_tuple[pos]:
                pos = parent
                parent = parents[pos]

                # change moving direction
                if move[0]:
                    move = get_row_movement(pos, cols, map_tuple, gene)
                else:
                    move = get_col_movement(pos, rows, map_tuple, gene)

                # cant change direction - remove the path
                if not any(move):
                    terrain_num -= 1
                    while parents[pos] != 0:
                        map_tuple[pos] = 0
                        pos = parents[pos]
                    map_tuple[pos] = 0
                    break

                # can change direction to just move out of the map
                if all(move):
                    break

            # move to the next pos
            map_tuple[pos] = terrain_num
            parents[pos] = parent
            parent = pos
            pos = pos[0] + move[0], pos[1] + move[1]

        # save paths for gif visualization
        if any(move):
            rake_path = {key: terrain_num for key in parents}
            rake_paths = {**rake_paths, **rake_path}

        terrain_num += 1

    return map_tuple, rake_paths


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
        rake_paths (Dict[Tuple[int, int], int]): terrain_num of raking the map
        fname (str): name of pickle file into which the solution will be saved
    """

    source_dir = Path(__file__).parents[1]
    solutions_dir = Path(f"{source_dir}/data/solutions")
    Path(solutions_dir).mkdir(parents=True, exist_ok=True)
    fname_path = Path(f"{solutions_dir}/{fname}_rake")
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
            i, j = map(int, wall_coordinate[1:-1].split(","))
            try:
                walled_map[i][j] = "1"
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

    int_walled_map = [list(map(int, subarray)) for subarray in walled_map]
    # TODO: evo deep check
    int_terrained_map, rake_paths, solution = evolutionize(int_walled_map, max_runs)

    

    # TODO: mark remaining unraked space with -2 (why actually?), add to docstring
    terrained_map = [
        [str(i) if i else "-2" for i in subarray] for subarray in int_terrained_map
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
    Creates and saves walled, terrained and propertied maps into text files.

    There are three dependant stages of creating a complete map. Each stage
    uses map that was created by the previous stage. We can therefore start
    from any stage as long as the previous stage one was run. (except for the
    first one). All remaining stages will run after that.

    Args:
        fname (str): name of file(s) that is/are going to be created
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
    except (QueryError, FileNotFoundError) as err:
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

# TODO: tests
# TODO: docstring everywhere for check
# TODO: terrain_num of methods/funcs
# TODO: amount vs count naming convention
