import collections as col
import json
import random
import re
from itertools import islice
from pathlib import Path
from typing import Any, Dict, List, Tuple


def init_rules(fname_rules: str) -> List[Any]:
    """Loads rules from the file and initializes them to namedtuple structure.

    Args:
        fname_rules (str): name of the file from which we load rules

    Returns:
        List[Any]: namedtuples with these attributes:
            name - name of the rule (unused)
            conds - conditions to fulfill actions
            acts - actions (message, add or remove fact from the set of facts)
    """

    Rules = col.namedtuple("Rules", "name conds acts")

    # regexp for loading a rule - name, conds and acts, each in one line
    patterns = [
        re.compile(r"\S+"),
        re.compile(r"((\?[A-Z]+)[^,]*, )*.*\?[A-Z].*"),
        re.compile(
            r"((add|remove|message) \?\w.*?, )*(add|remove|message).*\?\w.*"
        ),  # instead of ".*?," we could use "[^,]*,", or combine it "[^,]*?,"
    ]

    current_dir = Path(__file__).parents[1]
    fname_path = Path(f"{current_dir}/data/knowledge/{fname_rules}.txt")

    rules = []
    with open(fname_path, encoding="utf-8") as file:
        while rule := _get_4_lines_from_file(file):
            fields_amount = len(Rules._fields)
            for i in range(fields_amount):
                if not patterns[i].match(rule[i]):
                    print(Rules._fields[i], "field is set wrong!")
                    exit()  # TODO: tests for this..!

            rules.append(Rules(*rule))

    return rules


def _get_4_lines_from_file(file) -> Tuple[str, str, str]:
    """Reads and prepares 3 lines from the file for next processing.

    Args:
        file (file): opened file

    Returns:
        Tuple[str]: 3 lines that represent single rule
    """

    rule = tuple(line.rstrip("\n:") for line in islice(file, 4))

    # last line of file is not being read for some reason
    # need to skip last element (empty string) except for the last line
    if len(rule) == 4:
        rule = rule[:-1]

    return rule



def init_facts(
    fname_facts: str, facts_amount: int, randomize_facts_order: bool
) -> List[str]:
    """Loads facts from the file, initializes amount and order of them.

    Args:
        fname_facts (str): name of the file from which we load facts
        facts_amount (int): number of facts we want to load (points)
        randomize_facts_order (bool): option to shuffle loaded facts

    Returns:
        List[str]: known facts in sentences
    """

    current_dir = Path(__file__).parents[1]
    fname_path = Path(f"{current_dir}/data/knowledge/{fname_facts}.txt")

    with open(fname_path, encoding="utf-8") as file:
        facts = [fact.rstrip() for fact in file][:facts_amount]

    if randomize_facts_order:
        random.shuffle(facts)

    return facts


def find_actions(rules: List[Any], facts: List[str]) -> List[str]:
    """Finds all actions that can be done given the rules and facts.

    Args:
        rules (List[Any]): namedtuples with these attributes:
            name - name of the rule (unused)
            conds - conditions to fulfill actions
            acts - actions (message, add or remove fact from the set of facts)
        facts (List[str]): known facts in sentences

    Returns:
        List[str]: actions that can be done
    """

    found_actions = []
    for rule in rules:
        labelled_actions = expand(rule.conds.split(), facts, {})  # TODO
        actions = rule.acts.split(", ")
        
        for labelled_action in labelled_actions:
            for action in actions:
                action_type, action = action.split(" ", maxsplit=1)
                for key, value in labelled_action.items():
                    action = action.replace(key, value)
                found_actions.append(action_type + " " + action)

    return found_actions


def remove_duplicates(
    actions: List[str], facts: List[str]
) -> List[str]:
    """Removes those actions whose outcomes are already present in the facts.

    Args:
        found_actions (List[List[str]]): actions found given the rules and facts
        using_facts (List[str]): facts that we're using

    Returns:
        List[str]: appliable actions
    """

    appliable_actions = []
    for action in actions:
        type_, act = action.split(" ", 1)
        if (
            (type_ == "add" and act not in facts)
            or (type_ == "remove" and act in facts)
        ):
            appliable_actions.append(action)
    
    return appliable_actions


def apply_actions(
    appliable_actions: List[str], facts: List[str]
) -> Tuple[List[str], List[str]]:
    """Applies list of actions that is first in the queue.

    Args:
        appliable_actions (List[str]): lists of appliable actions
        facts (List[str]): known facts in sentences

    Returns:
        Tuple[List[str], List[str]]: (applied action, known facts in sentences)
    """

    applied_actions = []
    for action in appliable_actions:
        type_, act = action.split(" ", 1)
        if type_ == "add":
            facts.append(act)
        elif type_ == "remove":
            facts.remove(act)
        applied_actions.append(act)

    return applied_actions, facts


def expand(
    conds: List[str], facts: List[str], label: Dict[str, str]
) -> List[Dict[str, str]]:
    """Loops over conditions of rule recursively and finds all
    condition-matching labels from given facts.

    Args:
        conds (List[str]): conditions on rule's actions
        facts (List[str]): known facts in sentences
        label (Dict[str, str]): represent entities (?X -> <entity from fact>)

    Returns:
        List[Dict[str, str]]: labels
    """

    if conds[0] == "<>":  # identity checking is included in label checking
        return [label]

    labels = []
    # loop over facts
    for fact_str in facts:
        fact_list = fact_str.split()
        tmp_label = {}
        continue_ = True
        for i, (c, f) in enumerate(zip(conds, fact_list)):
            c_key = c.rstrip(",")
            # label checking for "?"
            if c_key.startswith("?") and f[0].isupper():  # new entity
                if c_key not in label:
                    if f not in label.values():
                        tmp_label[c_key] = f
                    else:
                        continue_ = False  # f already exist
                elif label[c_key] != f:
                    continue_ = False  # c and f does not match
            elif c_key != f:
                continue_ = False  # unmatched condition with fact

            if not continue_:
                break

            # next condition -> recursive call
            if c.endswith(","):
                labels += expand(conds[i + 1 :], facts, {**label, **tmp_label})

        # label match found for action
        if continue_ and not c.endswith(","):
            labels.append({**label, **tmp_label})

    return labels


def save_facts(facts: List[str], save_fname_facts: str) -> None:
    """Saves all facts into text file.

    Args:
        facts (List[List[str]]): updated facts
        save_fname_facts (str): name of file into which we save updated facts
    """

    current_dir = Path(__file__).parents[1]
    knowledge_dir = Path(f"{current_dir}/data/knowledge")
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    fname_path = Path(f"{knowledge_dir}/{save_fname_facts}.txt")
    with open(fname_path, "w", encoding="utf-8") as file:
        file.write("\n".join(facts))


def save_solution(fact_discovery_flow: Dict[str, List[str]], fname: str) -> None:
    """Saves solution of production system with stepped facts into json file
    for gif visualization and also viewing.

    Args:
        fact_discovery_flow (Dict[str, List[str]]): path of discovering the facts
        fname (str): name of json file into which the solution will be saved
    """

    current_dir = Path(__file__).parents[1]
    solutions_dir = Path(f"{current_dir}/data/solutions")
    solutions_dir.mkdir(parents=True, exist_ok=True)
    fname_path = f"{solutions_dir}/{fname}_rule.json"
    with open(fname_path, "w", encoding="utf-8") as file:
        json.dump(fact_discovery_flow, file, indent=4)


def run_production(
    save_fname_facts: str,
    load_fname_facts: str,
    load_fname_rules: str,
    step_by_step: bool,
    facts_amount: int,
    randomize_facts_order: bool,
    fname: str,
) -> None:
    """Sets parameters for running rule-based system with forward chaining.

    Args:
        save_fname_facts (str): name of file into which facts will be saved
        load_fname_facts (str): name of file from which we load facts
        load_fname_rules (str): name of file from which we load rules
        step_by_step (bool): entering one loaded fact by each production run
        facts_amount (int): number of facts we want to load (points)
        randomize_facts_order (bool): option to shuffle loaded facts
        fname (str): name of json file into which the solution will be saved
    """

    rules = init_rules(load_fname_rules)
    known_facts = init_facts(
        load_fname_facts, facts_amount, randomize_facts_order
    )

    if step_by_step:
        facts = []  # type: List[str]
        fact_discovery_flow = {}

        for known_fact in known_facts:
            using_facts = facts + [known_fact]
            new_facts, facts = run_forward_chain(
                using_facts, rules, save_fname_facts
            )
            fact_discovery_flow[known_fact] = new_facts

    else:
        new_facts, facts = run_forward_chain(
            known_facts, rules, save_fname_facts
        )
        fact_discovery_flow = {"All steps at once": new_facts}

    save_facts(facts, save_fname_facts)
    print_solution(fact_discovery_flow)
    save_solution(fact_discovery_flow, fname)


def print_solution(fact_discovery_flow: Dict[str, List[str]]) -> None:
    """Prints the flow of finding out new facts.

    Args:
        fact_discovery_flow (Dict[str, List[str]]): path of discovering the facts
    """

    for i, fact in enumerate(fact_discovery_flow, 1):
        print(f"{str(i)}:  {fact} -> " + ", ".join(fact_discovery_flow[fact]))


def run_forward_chain(
    using_facts: List[str], rules: List[Any], save_fname_facts: str
) -> Tuple[List[str], List[str]]:
    """Runs forward chaining to discover all possible facts. Discovered
    new facts along with already known facts will be saved to text file.

    Args:
        using_facts (List[str]): facts that we're using
        rules (List[Any]): namedtuples with these attributes:
            name - name of the rule (unused)
            conds - conditions to fulfill actions
            acts - actions (message, add or remove fact from the set of facts)
        save_fname_facts (str): name of the file into which facts will be saved

    Returns:
        Tuple[List[str], List[str]]: (applied facts, all facts)
    """

    new_facts = []
    while True:
        found_actions = find_actions(rules, using_facts)
        appliable_actions = remove_duplicates(found_actions, using_facts)

        if not appliable_actions:
            break

        applied_acts, using_facts = apply_actions(appliable_actions, using_facts)
        new_facts += applied_acts

    return new_facts, using_facts


if __name__ == "__main__":

    SAVE_FNAME_FACTS = "facts"
    LOAD_FNAME_FACTS = "facts_init"
    LOAD_FNAME_RULES = "rules"
    STEP_BY_STEP = True
    FACTS_AMOUNT = 11
    RANDOMIZE_FACTS_ORDER = False
    FNAME = "queried"

    chain_parameters = dict(
        save_fname_facts=SAVE_FNAME_FACTS,
        load_fname_facts=LOAD_FNAME_FACTS,
        load_fname_rules=LOAD_FNAME_RULES,
        step_by_step=STEP_BY_STEP,
        facts_amount=FACTS_AMOUNT,
        randomize_facts_order=RANDOMIZE_FACTS_ORDER,
        fname=FNAME,
    )  # type: Dict[str, Any]

    run_production(**chain_parameters)
