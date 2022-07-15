from pathlib import Path

from discord import File
from discord.ext import commands

from cogs.ai_algo import stage_1_evolution
from cogs.ai_algo import stage_2_pathfinding
from cogs.ai_algo import stage_3_forward_chain
from cogs.ai_algo import view


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

    chain_fname_save_facts = "facts"
    chain_fname_load_facts = "facts_init"
    chain_fname_load_rules = "rules"
    chain_step_by_step = True
    chain_randomize_facts_order = True

    view_skip_rake = False

    async def send_file_message(self, ctx):
        source_dir = Path(__file__).parents[0]
        gif_path = Path(f"{source_dir}/data/{self.shared_fname}.gif")
        with open(gif_path, "rb") as file:
            await ctx.message.channel.send(file=File(file))

    @commands.command(brief="Runs AI algs and shows gif animation of it.")
    async def run_ai(self, ctx):
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
            save_fname_facts=self.chain_fname_save_facts,
            load_fname_facts=self.chain_fname_load_facts,
            load_fname_rules=self.chain_fname_load_rules,
            step_by_step=self.chain_step_by_step,
            facts_amount=self.shared_points_amount + 1,
            facts_random_order=self.chain_randomize_facts_order,
            fname=self.shared_fname,
        )

        view_parameters = dict(
            fname=self.shared_fname,
            skip_rake=self.view_skip_rake,
            climb=self.shared_climb,
        )

        stage_1_evolution.create_maps(**evo_parameters)
        stage_2_pathfinding.run_production(**chain_parameters)
        stage_3_forward_chain.find_shortest_path(**path_parameters)
        view.create_gif(**view_parameters)

        self.send_file_message(ctx)


async def setup(bot):
    await bot.add_cog(AiAlgo(bot))


# TODO: Check what python techniques were used from the gdoc - mark it into doc
# TODO: Run the gdoc and fix parts that errors the program
# TODO: Update AI repo + integrate this into discord!
