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


def find_actions(rules: List[Any], using_facts: List[str]) -> List[str]:
    """Finds all actions that could be done given the rules and facts.

    Args:
        rules (List[Any]): namedtuples with these attributes:
            name - name of the rule (unused)
            conds - conditions to fulfill actions
            acts - actions (message, add or remove fact from the set of facts)
        using_facts (List[str]): facts that we're using

    Returns:
        List[str]: all actions that could be done
    """

    found_acts = []
    for rule in rules:
        cond_words = rule.conds.split()
        labelled_acts = expand(cond_words, using_facts, {})
        acts = rule.acts.split(", ")

        for labelled_act in labelled_acts:
            for act in acts:
                act_type, act = act.split(" ", maxsplit=1)
                for key, value in labelled_act.items():
                    act = act.replace(key, value)
                found_acts.append(act_type + " " + act)

    return found_acts


def remove_duplicates(
    found_acts: List[str], using_facts: List[str]
) -> List[str]:
    """Removes those actions whose outcomes are already present in the facts.

    Args:
        found_acts (List[List[str]]): actions that were found
        using_facts (List[str]): facts that we're using

    Returns:
        List[str]: applicable actions
    """

    applicable_acts = []
    for found_act in found_acts:
        type_, act = found_act.split(" ", 1)
        if (type_ == "add" and act not in using_facts) or (
            type_ == "remove" and act in using_facts
        ):
            applicable_acts.append(found_act)

    return applicable_acts


def apply_actions(
    acts: List[str], facts: List[str]
) -> Tuple[List[str], List[str]]:
    """Applies actions to create newly found facts.

    Args:
        acts (List[str]): actions that we are about to perform
        facts (List[str]): known facts in sentences

    Returns:
        Tuple[List[str], List[str]]: (newly found facts, updated facts)
    """

    newly_found_facts = []
    for act in acts:
        type_, act = act.split(" ", 1)
        if type_ == "add":
            facts.append(act)
        elif type_ == "remove":
            facts.remove(act)
        newly_found_facts.append(act)

    return newly_found_facts, facts


def expand(
    cond_words: List[str], facts: List[str], labels: Dict[str, str]
) -> List[Dict[str, str]]:
    """Runs through the rule's conditions recursively and tries to label 
    entities from given facts and rules.

    Entities must start with capitalized characters!

    Args:
        cond_words (List[str]): words of condition(s) on rule's actions
        facts (List[str]): known facts in sentences
        labels (Dict[str, str]): labels of entities (?X -> entity)

    Returns:
        List[Dict[str, str]]: found labels
    """

    if cond_words[0] == "<>":  # labels must be different
        if labels[cond_words[1]] == labels[cond_words[2]]:
            return []  # TODO: test
        return [labels]

    found_labels = []
    for fact in facts:
        fact_words = fact.split()
        tmp_label = {}
        continue_ = True

        for i, (c_word, f_word) in enumerate(zip(cond_words, fact_words)):
            next_condition = c_word.endswith(",")
            c_word = c_word.rstrip(",") if next_condition else c_word

            # encountering label with entity
            if c_word.startswith("?") and f_word[0].isupper():
                if c_word not in labels:
                    if f_word not in labels.values():
                        tmp_label[c_word] = f_word  # saving label for entity

                    else:
                        continue_ = False  # entity already exist in labels
                elif labels[c_word] != f_word:
                    continue_ = False  # label already exist for other entity
            elif c_word != f_word:
                continue_ = False  # words in the sentence stopped matching

            if not continue_:
                break

            if next_condition:
                next_cond_words = cond_words[i + 1 :]
                found_labels += expand(
                    next_cond_words, facts, {**labels, **tmp_label}
                )

        # new label found
        if continue_ and not next_condition:
            found_labels.append({**labels, **tmp_label})

    return found_labels


def save_facts(facts: List[str], fname_save_facts: str) -> None:
    """Saves all facts into text file.

    Args:
        facts (List[List[str]]): all (known and found) facts that will be saved
        fname_save_facts (str): name of file into which we save facts
    """

    current_dir = Path(__file__).parents[1]
    knowledge_dir = Path(f"{current_dir}/data/knowledge")
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    fname_path = Path(f"{knowledge_dir}/{fname_save_facts}.txt")
    with open(fname_path, "w", encoding="utf-8") as file:
        file.write("\n".join(facts))


def save_solution(
    fact_discovery_flow: Dict[str, List[str]], fname: str
) -> None:
    """Saves the flow of finding out new facts into json file for gif
    visualization and viewing.

    Args:
        fact_discovery_flow (Dict[str, List[str]]): path of discovering facts
        fname (str): name of json file into which the solution will be saved
    """

    current_dir = Path(__file__).parents[1]
    solutions_dir = Path(f"{current_dir}/data/solutions")
    solutions_dir.mkdir(parents=True, exist_ok=True)
    fname_path = f"{solutions_dir}/{fname}_rule.json"
    with open(fname_path, "w", encoding="utf-8") as file:
        json.dump(fact_discovery_flow, file, indent=4)


def run_production(
    fname_save_facts: str,
    fname_load_facts: str,
    fname_load_rules: str,
    step_by_step: bool,
    facts_amount: int,
    randomize_facts_order: bool,
    fname: str,
) -> None:
    """Sets parameters for running rule-based system with forward chaining.

    Args:
        fname_save_facts (str): name of file into which facts will be saved
        fname_load_facts (str): name of file from which we load facts
        fname_load_rules (str): name of file from which we load rules
        step_by_step (bool): entering one loaded fact by each production run
        facts_amount (int): number of facts we want to load (points)
        randomize_facts_order (bool): option to shuffle loaded facts
        fname (str): name of json file into which the solution will be saved
    """

    rules = init_rules(fname_load_rules)
    known_facts = init_facts(
        fname_load_facts, facts_amount, randomize_facts_order
    )

    if step_by_step:
        facts = []  # type: List[str]
        fact_discovery_flow = {}

        for known_fact in known_facts:
            using_facts = facts + [known_fact]
            new_facts, facts = run_forward_chain(
                using_facts, rules, fname_save_facts
            )
            fact_discovery_flow[known_fact] = new_facts

    else:
        new_facts, facts = run_forward_chain(
            known_facts, rules, fname_save_facts
        )
        fact_discovery_flow = {"All steps at once": new_facts}

    save_facts(facts, fname_save_facts)
    print_solution(fact_discovery_flow)
    save_solution(fact_discovery_flow, fname)


def print_solution(fact_discovery_flow: Dict[str, List[str]]) -> None:
    """Prints the flow of finding out new facts.

    Args:
        fact_discovery_flow (Dict[str, List[str]]): path of discovering facts
    """

    for i, fact in enumerate(fact_discovery_flow, 1):
        print(f"{str(i)}:  {fact} -> " + ", ".join(fact_discovery_flow[fact]))


def run_forward_chain(
    using_facts: List[str], rules: List[Any], fname_save_facts: str
) -> Tuple[List[str], List[str]]:
    """Runs forward chaining to discover new facts given the facts and rules.

    Saves new facts along with already known ones into text file.

    Args:
        using_facts (List[str]): facts that we're using
        rules (List[Any]): namedtuples with these attributes:
            name - name of the rule (unused)
            conds - conditions to fulfill actions
            acts - actions (message, add or remove fact from the set of facts)
        fname_save_facts (str): name of the file into which facts will be saved

    Returns:
        Tuple[List[str], List[str]]: (applied facts, facts that we used)
    """

    new_facts = []
    while True:
        found_acts = find_actions(rules, using_facts)
        acts = remove_duplicates(found_acts, using_facts)

        if not acts:
            break

        newly_found_facts, using_facts = apply_actions(acts, using_facts)
        new_facts += newly_found_facts

    return new_facts, using_facts


if __name__ == "__main__":

    FNAME_SAVE_FACTS = "facts"
    FNAME_LOAD_FACTS = "facts_init"
    FNAME_LOAD_RULES = "rules"
    STEP_BY_STEP = True
    FACTS_AMOUNT = 11
    RANDOMIZE_FACTS_ORDER = False
    FNAME = "queried"

    chain_parameters = dict(
        fname_save_facts=FNAME_SAVE_FACTS,
        fname_load_facts=FNAME_LOAD_FACTS,
        fname_load_rules=FNAME_LOAD_RULES,
        step_by_step=STEP_BY_STEP,
        facts_amount=FACTS_AMOUNT,
        randomize_facts_order=RANDOMIZE_FACTS_ORDER,
        fname=FNAME,
    )  # type: Dict[str, Any]

    run_production(**chain_parameters)
