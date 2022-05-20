import os

from discord import File
from discord.ext import commands

# This import is for version without discord
if __name__ == "__main__":
    import model.evolution as evo
    import model.forward_chain as chain
    import model.pathfinding as path
    import view
else:
    import cogs.ai_algo.model.evolution as evo
    import cogs.ai_algo.model.forward_chain as chain
    import cogs.ai_algo.model.pathfinding as path
    import cogs.ai_algo.view as view


class AiAlgo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # walls uses:       fname, points_amount, max_runs, query
    # terrain uses:     fname, points_amount, max_runs,
    # properties uses:  fname, points_amount
    begin_create = "walls"
    query = "10x12 (1,5) (2,1) (3,4) (4,2) (6,8) (6,9) (6,7)"
    fname = "queried"
    max_runs = 1
    points_amount = 10

    movement = "M"
    climb = False
    algorithm = "HK"
    subset_size = None

    save_fname_facts = "facts"
    load_fname_facts = "facts_init"
    load_fname_rules = "rules"
    step_by_step = True
    facts_amount = 11
    facts_random_order = True

    skip_rake = False

    # main method for creating gif
    @commands.command(brief="Creates gif and shows it. (pars in file)")
    async def create(self, ctx):
        evo_parameters = dict(
            begin_create=self.begin_create,
            query=self.query,
            fname=self.fname,
            max_runs=self.max_runs,
            points_amount=self.points_amount,
        )

        path_parameters = dict(
            fname=self.fname,
            movement=self.movement,
            climb=self.climb,
            algorithm=self.algorithm,
            subset_size=self.subset_size,
        )

        chain_parameters = dict(
            save_fname_facts=self.save_fname_facts,
            load_fname_facts=self.load_fname_facts,
            load_fname_rules=self.load_fname_rules,
            step_by_step=self.step_by_step,
            facts_amount=self.points_amount + 1,
            facts_random_order=self.facts_random_order,
            fname=self.fname,
        )

        evo.createMaps(**evo_parameters)
        path.findShortestPath(**path_parameters)
        chain.runProduction(**chain_parameters)

        view.createGif(self.fname, self.skip_rake, self.climb)

        current_dir = os.path.dirname(os.path.abspath(__file__))
        # TODO: check whether it works as intended (file keyword)
        with open(f"{current_dir}\\data\\{self.fname}.gif", "rb") as file:
            await ctx.message.channel.send(file=File(file))


async def setup(bot):
    await bot.add_cog(AiAlgo(bot))


if __name__ == "__main__":

    # map creation parameters
    # walls uses: query, fname, max_runs, points_amount
    # terrain uses: fname, max_runs, points_amount
    # properties uses: fname, points_amount
    begin_create = "walls"
    query = "10x12 (1,5) (2,1) (3,4) (4,2) (6,8) (6,9)"
    fname = "queried"
    max_runs = 1
    points_amount = 10

    # pathfinding parameters
    movement = "M"
    climb = False
    algorithm = "HK"
    subset_size = None

    # production parameters
    save_fname_facts = "facts"
    load_fname_facts = "facts_init"
    load_fname_rules = "rules"
    step_by_step = True
    facts_random_order = True

    # view parameters
    skip_rake = False

    evo_parameters = dict(
        begin_create=begin_create,
        query=query,
        fname=fname,
        max_runs=max_runs,
        points_amount=points_amount,
    )

    path_parameters = dict(
        fname=fname,
        movement=movement,
        climb=climb,
        algorithm=algorithm,
        subset_size=subset_size,
    )

    chain_parameters = dict(
        save_fname_facts=save_fname_facts,
        load_fname_facts=load_fname_facts,
        load_fname_rules=load_fname_rules,
        step_by_step=step_by_step,
        facts_amount=points_amount + 1,
        facts_random_order=facts_random_order,
        fname=fname,
    )

    evo.createMaps(**evo_parameters)
    path.findShortestPath(**path_parameters)
    chain.runProduction(**chain_parameters)

    view.createGif(fname, skip_rake, climb)

# TODO: remember previous fitness attempts
# TODO: optimize creating props
# TODO: parameters could be done better in create method
