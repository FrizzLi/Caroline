"""This module serves to run, choose parameters and display the output of AI
Algorithms into the console.
"""

import stage_1_ai_evolution
import stage_2_ai_pathfinding
import stage_3_ai_forward_chain
import stage_4_view


if __name__ == "__main__":

    # walls:       fname
    # terrain:     fname, points_amount, climb
    # properties:  fname, points_amount
    # view:        fname,                climb
    SHARED_FNAME = "queried"
    SHARED_POINTS_AMOUNT = 10
    SHARED_CLIMB = False

    # harder variant: "10x12 (1,5) (2,1) (3,4) (4,2) (6,8) (6,9) (6,7)"
    EVO_QUERY = "10x12 (1,5) (2,1) (3,4) (4,2) (6,8) (6,9) (6,9)"
    EVO_BEGIN_CREATE = "walls"
    EVO_MAX_RUNS = 3

    PATH_MOVEMENT_TYPE = "M"
    PATH_ALGORITHM = "HK"

    CHAIN_FNAME_SAVE_FACTS = "facts"
    CHAIN_FNAME_LOAD_FACTS = "facts_init"
    CHAIN_FNAME_LOAD_RULES = "rules"
    CHAIN_STEP_BY_STEP = True
    CHAIN_RANDOMIZE_FACTS_ORDER = False

    VIEW_SKIP_RAKE = False

    evo_parameters = dict(
        fname=SHARED_FNAME,
        begin_from=EVO_BEGIN_CREATE,
        query=EVO_QUERY,
        max_runs=EVO_MAX_RUNS,
        points_amount=SHARED_POINTS_AMOUNT,
    )

    path_parameters = dict(
        fname=SHARED_FNAME,
        movement_type=PATH_MOVEMENT_TYPE,
        climb=SHARED_CLIMB,
        algorithm=PATH_ALGORITHM,
        visit_points_amount=SHARED_POINTS_AMOUNT,
    )

    chain_parameters = dict(
        fname_save_facts=CHAIN_FNAME_SAVE_FACTS,
        fname_load_facts=CHAIN_FNAME_LOAD_FACTS,
        fname_load_rules=CHAIN_FNAME_LOAD_RULES,
        step_by_step=CHAIN_STEP_BY_STEP,
        facts_amount=SHARED_POINTS_AMOUNT,
        randomize_facts_order=CHAIN_RANDOMIZE_FACTS_ORDER,
        fname=SHARED_FNAME,
    )

    view_parameters = dict(
        fname=SHARED_FNAME,
        skip_rake=VIEW_SKIP_RAKE,
        climb=SHARED_CLIMB,
    )

    stage_1_ai_evolution.create_maps(**evo_parameters)
    stage_2_ai_pathfinding.find_shortest_path(**path_parameters)
    stage_3_ai_forward_chain.run_production(**chain_parameters)
    stage_4_view.create_gif(**view_parameters)
