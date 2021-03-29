# Non-point agents in space partitioning structures

When developing neighbor-finding data structures there's a significant difference in how point and non-point agents can be handled. Here point agents have no size in any dimension of space, just a location. Non-point agents cover a section of space, i.e. have a non-zero size in at least one of dimensions of space.

## Why are non-point agents different?

To answer that we have to go back a bit and show how partitioning spaces helps in neighbor-finding for point agents (for simplicity we can look at a grid structure). For point agents the simplest possible case is when we have only one agent type, and one interaction radius between all the agents. The obvious way to partition the space is to make grid cell size the same as the interaction radius (black rectangle is the cell the agent belongs to, red rectangle is the agent's interaction area, and the blue rectangle is the neighbor area determined by the structure):

![nonpoint1](/nonpoint1.png)

Here neighbor-finding is done by selecting a cell (black rectangle) and having all the agents in that cell interact with all agents in that cell and all immediately neighboring cells (blue rectangle). This works great for point agents, but let's see what happens if we have a non-point agent that happens to be located right on the boundary between two cells:

![nonpoint2](/nonpoint2.png)

First problem is to determine which cell the agent belongs to. We could say that non-point agents can only belong to one cell, and we could say that the agent's centroid determines the cell. This means that agent size determines how many layers of cells we have to take into account when looking for neighbors of such agents:

![nonpoint3](/nonpoint3.png)

If all agents are the same size, then this number is constant: `2 * agent_radius + interaction_radius` and in this case we can even say that this number *is* the cell size, and then we have basically the same situation as with point agents.

If non-point agents have varying sizes, then it becomes impossible to know how many layers we have to take into account. In short, the whole point of space partitioning is to be able to quickly find neighboring partitions. If how many layers of partitions we consider neighboring partitions depends on varying agent sizes in addition to interaction radius (`agent1_radius + agent2_radius + interaction_radius`), and one of the sizes involved in this calculation is the size of the neighboring agent which we are currently trying to find, then it's obvious that this cannot work.

The only solution would be to pessimistically say that all agents have the same size, and that would be the size of the largest agent (`2 * largest_agent_radius + interaction_radius`). This again reduces the problem to the same simple situation we have with point agents, but now we might have a large number of small agents whose supposed neighbors are actually too far away to be real neighbors, and this makes the whole structure inefficient:

![nonpoint4](/nonpoint4.png)

Alternatively, instead of each agent belongingto one cell, we could reference an agent from multiple cells (all cells that the agent intersects) which creates a different problem. If an agent can be referenced from multiple cells, and we find agents' neighbors by going through neighboring cells, we're going to come across same pairs of agents multiple times. This then requires a marking each pair of interacting agents so we can skip the same pair next time we encounter them. This can also make the structure inefficient.

## Solution

Trees. Trees are basically hierarchical space partitions, which means there's always a root tree node that encompasses all agents, and there are branch nodes of varying sizes that might be able to accomodate agents of corresponding sizes. In short, trees can store agents in branch nodes as well as in leaf nodes, and neighbor searching just has to take branch nodes into account (branch nodes are traversed anyway when looking for neighboring leaf nodes, so this is a natural extension).

Currently in [Tay](https://github.com/bcace/tay) I have only two tree structures implemented, a k-d tree (`CpuTree`) and an AABB tree (`CpuAabbTree`). My k-d tree always splits a parent partition in half along the selected axis, which means that sometimes even small non-point agents can get intersected by the splitting plane, causing those small agents to be stored in much larger branch node partitions (which in turn means that those agents get many more neighbors than they should). On the other hand AABB trees get built bottom up, with nodes always adapting to the shape and relative positions of agents. This keeps agents stored in appropriately sized tree node partitions, which then also reflects on the run-times.

> I didn't try to use grids for non-point agents, but if the trick is in the hierarchy of differently-sized partitions (as trees show) then I guess one reasonable way to do it would be to have a hierarchy of grids. Each grid partitioning the same space with different sized cells, and being able to search for neighboring cells in other grids.

## Tests

To test structures with non-point agents I created agents with sizes varying between 1 and 50.

**Agents**|10000
**Steps**|1000
**Space size**|1000 * 1000 * 1000
**Threads (CPU)**|8

I also tested with interaction radii 50 and 100, and these are average numbers of interactions each agent has during each simulation step:

**50**|47.3536
**100**|175.818

First, we can see how much better tree structures (`CpuTree` and `CpuAabbTree`) perform than brute-force simulation (`CpuSimple`):

![nonpoint_plot_1](/nonpoint_plot_1.png)

Comparing just the tree structures at interaction radius 50:

![nonpoint_plot_2](/nonpoint_plot_2.png)

and the same with interaction radius at 100:

![nonpoint_plot_3](/nonpoint_plot_3.png)

we can see how much faster the AABB tree is because it doesn't have the problem of storing awkwardly positioned agents into "wrong" partitions like the k-d tree. The consequences of AABB tree adapting all its nodes to their contents can be clearly seen in this neighbor-finding efficiency plot:

![nonpoint_plot_4](/nonpoint_plot_4.png)
