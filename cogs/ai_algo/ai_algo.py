from pathlib import Path

from discord import File
from discord.ext import commands

from cogs.ai_algo import (
    stage_1_evolution,
    stage_2_pathfinding,
    stage_3_forward_chain,
    view,
)


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

    # harder variant: "10x12 (1,5) (2,1) (3,4) (4,2) (6,8) (6,9) (6,7)"
    evo_query = "10x12 (1,5) (2,1) (3,4) (4,2) (6,8) (6,9) (6,9)"
    evo_begin_create = "walls"
    evo_max_runs = 3

    path_movement_type = "M"
    path_algorithm = "HK"

    chain_fname_save_facts = "facts"
    chain_fname_load_facts = "facts_init"
    chain_fname_load_rules = "rules"
    chain_step_by_step = True
    chain_randomize_facts_order = False

    view_skip_rake = False

    @commands.command(brief=shared_points_amount)
    async def change_points_amount(self, ctx, points_amount: int):
        """amount of destination points to visit"""

        points_amount = int(points_amount)
        self.shared_points_amount = points_amount
        await ctx.send(f"points_amount changed to {points_amount}.")

    @commands.command(brief=shared_climb)
    async def change_climb(self, ctx, climb: int):
        """Climbing distance approach. If True, distance is measured with
        abs(current terrain number - next terrain number)"""

        self.shared_climb = bool(climb)
        await ctx.send(f"climb changed to {climb}.")

    @commands.command(brief=evo_query)
    async def change_query(self, ctx, query: str):
        """contains size of map and tuple coordinates of walls
        example: "10x12 (1,5) (2,1) (3,4) (4,2) (6,8) (6,9)"""

        self.evo_query = query
        await ctx.send(f"query changed to {query}.")

    @commands.command(brief=path_movement_type)
    async def change_movement_type(self, ctx, movement_type: str):
        """ "M" - Manhattan, "D" - Diagonal + Manhattan"""

        self.path_movement_type = movement_type
        await ctx.send(f"movement_type changed to {movement_type}.")

    @commands.command(brief=chain_randomize_facts_order)
    async def change_randomize_facts_order(
        self, ctx, randomize_facts_order: str
    ):
        """shuffle loaded facts"""

        self.chain_randomize_facts_order = (
            True if randomize_facts_order.lower() == "true" else False
        )
        msg = f"randomize_facts_order changed to {randomize_facts_order}."
        await ctx.send(msg)

    @commands.command(brief=view_skip_rake)
    async def change_skip_rake(self, ctx, skip_rake: int):
        """Determines whether the animation will also have the raking part."""

        self.view_skip_rake = bool(skip_rake)
        await ctx.send(f"climb changed to {skip_rake}.")

    async def send_file_message(self, ctx):
        source_dir = Path(__file__).parents[0]
        gif_path = Path(f"{source_dir}/data/{self.shared_fname}.gif")
        with open(gif_path, "rb") as file:
            await ctx.message.channel.send(file=File(file))

    @commands.command(brief="Runs AI algs and shows gif animation of it.")
    async def run_ai(self, ctx):
        evo_parameters = dict(
            fname=self.shared_fname,
            begin_from=self.evo_begin_create,
            query=self.evo_query,
            max_runs=self.evo_max_runs,
            points_amount=self.shared_points_amount,
        )

        path_parameters = dict(
            fname=self.shared_fname,
            movement_type=self.path_movement_type,
            climb=self.shared_climb,
            algorithm=self.path_algorithm,
            visit_points_amount=self.shared_points_amount,
        )

        chain_parameters = dict(
            fname_save_facts=self.chain_fname_save_facts,
            fname_load_facts=self.chain_fname_load_facts,
            fname_load_rules=self.chain_fname_load_rules,
            step_by_step=self.chain_step_by_step,
            facts_amount=self.shared_points_amount,
            randomize_facts_order=self.chain_randomize_facts_order,
            fname=self.shared_fname,
        )

        view_parameters = dict(
            fname=self.shared_fname,
            skip_rake=self.view_skip_rake,
            climb=self.shared_climb,
        )

        stage_1_evolution.create_maps(**evo_parameters)
        stage_2_pathfinding.find_shortest_path(**path_parameters)
        stage_3_forward_chain.run_production(**chain_parameters)
        view.create_gif(**view_parameters)

        await self.send_file_message(ctx)


async def setup(bot):
    await bot.add_cog(AiAlgo(bot))
