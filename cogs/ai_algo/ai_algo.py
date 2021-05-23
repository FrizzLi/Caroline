import os

from discord.ext import commands
from discord import File

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
    def __init__(self, client):
        self.client = client

    # walls uses: query, fname, max_runs, points_amount
    # terrain uses: fname, max_runs, points_amount
    # properties uses: fname, points_amount
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

    # @property
    # def points_amount(self):
    #     return self._points_amount

    # @points_amount.setter
    # def points_amount(self, new_val):
    #     self._points_amount = new_val
    #     self.facts_amount = new_val + 1

    # modifying evolution attributes
    @commands.command(brief=f"{begin_create}")
    async def change_begin_create(self, ctx, begin_create):
        """begin_create (str): defines from which part of creating maps to
        start until the ending properties part (walls/terrain/properties)"""

        self.begin_create = begin_create
        await ctx.send(f"begin_create changed to {begin_create}.")

    @commands.command(brief=f"{query}")
    async def change_query(self, ctx, query):
        """query (str): contains size of map and tuple coordinates of walls
        example: "10x12 (1,5) (2,1) (3,4) (4,2) (6,8) (6,9)"""

        self.query = query
        await ctx.send(f"query changed to {query}.")

    @commands.command(brief=f"{max_runs}")
    async def change_max_runs(self, ctx, max_runs):
        """max_runs: (int): max number of attempts to find a solution"""

        self.max_runs = int(max_runs)
        await ctx.send(f"max_runs changed to {max_runs}.")

    @commands.command(brief=f"{points_amount}")
    async def change_points_amount(self, ctx, points_amount):
        """points_amount (int): amount of destination points to visit"""

        self.points_amount = int(points_amount)
        self.facts_amount = int(points_amount) + 1
        await ctx.send(f"points_amount changed to {points_amount}.")
        await ctx.send(f"facts_amount changed to {str(self.facts_amount)}.")

    # modifying pathfinding attributes
    @commands.command(brief=f"{movement}")
    async def change_movement(self, ctx, movement):
        """movement (string): "M" - Manhattan, "D" - Diagonal + Manhattan"""

        self.movement = movement
        await ctx.send(f"movement changed to {movement}.")

    @commands.command(brief=f"{climb}")
    async def change_climb(self, ctx, climb):
        """climb (bool): Climbing distance approach. If True, distance is
        measured with abs(current terrain number - next terrain number)"""

        self.climb = bool(climb)
        await ctx.send(f"climb changed to {climb}.")

    @commands.command(brief=f"{algorithm}")
    async def change_algorithm(self, ctx, algorithm):
        """algorithm (string): NP - Naive Permutations, HK - Held Karp"""

        self.algorithm = int(algorithm)
        await ctx.send(f"algorithm changed to {algorithm}.")

    @commands.command(brief=f"{subset_size}")
    async def change_subset_size(self, ctx, subset_size):
        """subset_size (Union[int, None]): number of points to visit
        None means all"""

        self.subset_size = None if subset_size == "None" else subset_size
        await ctx.send(f"subset_size changed to {subset_size}.")

    # modifying forward_chain parameters
    @commands.command(brief=f"{save_fname_facts}")
    async def change_save_fname_facts(self, ctx, save_fname_facts):
        """save_fname_facts (str): name of file into which facts will be saved"""

        self.save_fname_facts = save_fname_facts
        await ctx.send(f"save_fname_facts changed to {save_fname_facts}.")

    @commands.command(brief=f"{load_fname_facts}")
    async def change_load_fname_facts(self, ctx, load_fname_facts):
        """load_fname_facts (str): name of file from which we load facts"""

        self.load_fname_facts = load_fname_facts
        await ctx.send(f"load_fname_facts changed to {load_fname_facts}.")

    @commands.command(brief=f"{load_fname_rules}")
    async def change_load_fname_rules(self, ctx, load_fname_rules):
        """load_fname_rules (str): name of file from which we load rules"""

        self.load_fname_rules = load_fname_rules
        await ctx.send(f"load_fname_rules changed to {load_fname_rules}.")

    @commands.command(brief=f"{step_by_step}")
    async def change_step_by_step(self, ctx, step_by_step):
        """step_by_step (bool): entering one fact by each production run"""

        self.step_by_step = True if step_by_step.lower() == "true" else False
        await ctx.send(f"step_by_step changed to {step_by_step}.")

    @commands.command(brief=f"{facts_amount}")
    async def change_facts_amount(self, ctx, facts_amount):
        """facts_amount (int): number of facts we want to load (points)"""

        self.facts_amount = int(facts_amount)
        await ctx.send(f"facts_amount changed to {facts_amount}.")

    @commands.command(brief=f"{facts_random_order}")
    async def change_facts_random_order(self, ctx, facts_random_order):
        """facts_random_order (bool): shuffle loaded facts"""

        self.facts_random_order = (
            True if facts_random_order.lower() == "true" else False
        )
        await ctx.send(f"facts_random_order changed to {facts_random_order}.")

    # main method for creating gif
    @commands.command(brief="Creates gif and shows it.")
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
        with open(f"{current_dir}\\data\\{self.fname}.gif", "rb") as f:
            await ctx.message.channel.send(file=File(f))


def setup(client):
    client.add_cog(AiAlgo(client))


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
# TODO: create tests
# TODO: parameters could be done better in create method
