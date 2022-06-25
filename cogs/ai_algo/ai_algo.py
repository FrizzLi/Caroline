import os

from discord import File
from discord.ext import commands

import cogs.ai_algo.model.evolution as evo
import cogs.ai_algo.model.forward_chain as chain
import cogs.ai_algo.model.pathfinding as path
import cogs.ai_algo.view as view


class AiAlgo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # walls:       fname
    # terrain:     fname, points_amount, climb
    # properties:  fname, points_amount
    # view:        fname,                climb
    shared_fname = "queried"
    shared_points_amount = 10
    shared_climb = False

    evo_query = "10x12 (1,5) (2,1) (3,4) (4,2) (6,8) (6,9) (6,7)"
    evo_begin_create = "walls"
    evo_max_runs = 1

    path_movement = "M"
    path_algorithm = "HK"
    path_visit_points_amount = None

    chain_save_fname_facts = "facts"
    chain_load_fname_facts = "facts_init"
    chain_load_fname_rules = "rules"
    chain_step_by_step = True
    chain_facts_random_order = True

    view_skip_rake = False

    async def send_file_message(self, ctx):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        gif_path = f"{current_dir}\\data\\{self.shared_fname}.gif"
        with open(gif_path, "rb") as file:
            await ctx.message.channel.send(file=File(file))

    @commands.command(brief="Creates gif and shows it. (pars in file)")
    async def create(self, ctx):
        evo_parameters = dict(
            begin_from=self.evo_begin_create,
            query=self.evo_query,
            fname=self.shared_fname,
            max_runs=self.evo_max_runs,
            points_amount=self.shared_points_amount,
        )

        path_parameters = dict(
            fname=self.shared_fname,
            movement=self.path_movement,
            climb=self.shared_climb,
            algorithm=self.path_algorithm,
            visit_points_amount=self.path_visit_points_amount,
        )

        chain_parameters = dict(
            save_fname_facts=self.chain_save_fname_facts,
            load_fname_facts=self.chain_load_fname_facts,
            load_fname_rules=self.chain_load_fname_rules,
            step_by_step=self.chain_step_by_step,
            facts_amount=self.shared_points_amount + 1,
            facts_random_order=self.chain_facts_random_order,
            fname=self.shared_fname,
        )

        evo.create_maps(**evo_parameters)
        path.findShortestPath(**path_parameters)
        chain.runProduction(**chain_parameters)
        view.createGif(
            self.shared_fname, self.view_skip_rake, self.shared_climb
        )

        self.send_file_message(ctx)


async def setup(bot):
    await bot.add_cog(AiAlgo(bot))

# TODO: var names outside and inside functions - NOTE: Naming onsistency in f. calls is rly not necessary-using_facts ex.
# TODO: chain - optimize creating props

# TODO: use consistent variable naming inside and outside functions?
# TODO: gspread parameter loading
# TODO: update ai repo and make local parameter loading there
