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
    # view:        fname,               climb
    shared_fname = "queried"
    shared_points_amount = 10
    shared_climb = False

    wall_query = "10x12 (1,5) (2,1) (3,4) (4,2) (6,8) (6,9) (6,7)"
    wall_begin_create = "walls"

    terrain_movement = "M"
    terrain_algorithm = "HK"
    terrain_subset_size = None
    terrain_max_runs = 1

    property_save_fname_facts = "facts"
    property_load_fname_facts = "facts_init"
    property_load_fname_rules = "rules"
    property_step_by_step = True
    property_facts_random_order = True

    view_skip_rake = False

    async def send_file_message(self, ctx):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        gif_path = f"{current_dir}\\data\\{self.shared_fname}.gif"
        with open(gif_path, "rb") as file:
            await ctx.message.channel.send(file=File(file))

    @commands.command(brief="Creates gif and shows it. (pars in file)")
    async def create(self, ctx):
        evo_parameters = dict(
            begin_from=self.wall_begin_create,
            query=self.wall_query,
            fname=self.shared_fname,
            max_runs=self.terrain_max_runs,
            points_amount=self.shared_points_amount,
        )

        path_parameters = dict(
            fname=self.shared_fname,
            movement=self.terrain_movement,
            climb=self.shared_climb,
            algorithm=self.terrain_algorithm,
            subset_size=self.terrain_subset_size,
        )

        chain_parameters = dict(
            save_fname_facts=self.property_save_fname_facts,
            load_fname_facts=self.property_load_fname_facts,
            load_fname_rules=self.property_load_fname_rules,
            step_by_step=self.property_step_by_step,
            facts_amount=self.shared_points_amount + 1,
            facts_random_order=self.property_facts_random_order,
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


# TODO: evo - remember previous fitness attempts
# TODO: evo - parameters could be done better in create_maps(?) method
# TODO: chain - optimize creating props
# TODO: gspread parameter loading
# TODO: update ai repo and make local parameter loading there
