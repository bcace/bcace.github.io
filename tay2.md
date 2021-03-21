# Non-point agents in space partitioning structures (Tay 2)

When trying to develop data structures that help with efficient neighbor-finding, such as various trees and grids, there's a marked difference between agents being point agents (only a location in space) and non-point (cover a section of that space, i.e. have a size in at least one of the space dimensions).

The difference is easiest to see in grids. If we have an agent which spans several grid cells, do we reference this agent from just a single grid cell or from all grid cells the agent intersects?

## What's the problem with non-point agents?

To answer that we have to go back a bit and how partitioning spaces helps finding neighbors in the more simple case of point agents, and try to apply the same on non-point agents. So for point agents the simplest possible case is that we have only a single agent type, and a single interaction radius between all those agents. Then we obviously partition the space so that grid cell size is actually the interaction radius:

![nonpoint1](/nonpoint1.png)

Then neighbor finding simply comes down to selecting a cell and making all the agents in that cell interact with all agents in that cell and all immediately neighboring cells. This works perfectly for point agents, but let's see what happens if we have a non-point agent that happens to be located right on the boundary between two cells.

![nonpoint2](/nonpoint2.png)

First question is to which cell does this agent belong? If we for example say that all non-point agents belong to only one cell, and let's just say that the agent's centroid determines which cell the agent belongs to. This means that the size of the agent suddenly determines how many layers of cells we have to take into account when looking for neighbors of such agents. If all agents are the same size, then this number is constant

![nonpoint3](/nonpoint3.png)

and we can even just enlarge the cell size to be 2 * agent radius plus interaction radius and go back to only looking for neighbors in the first layer of cells only, which returns us to the same situation we had with point agents.

If non-point agents are all of different sizes, then it would be impossible to know how many layers we have to take into account, because might know how large each agent from the "seer" cell is, but we also have to know that for all the agents which it has to interact with, which we don't know in advance - this is exactly the thing we're trying to find out.

The only alternative would be to pessimistically say that all agents have the same size, and that would be the size of the largest agent. This brings us back ot the point agent territory, but now we might have a large number of small agents whose supposed neighbors are actually way too far away to be real neighbors, and this makes the whole structure inefficient.

![nonpoint4](/nonpoint4.png)

Alternatively, we could reference an agent from multiple cells, and there we get a different problem. If an agent can belong to multiple cells, and we find agents' neighbors by going hrough cells and looking at their neighboring cells, then we're going to come across same pairs of agents multiple times, which then requires a whole mechanism to mark a pair of agents as already interacted, which again makes the structure inefficient.

## Solution

Trees. Trees are basically hierarchical space partitions, which means there's always a single tree node that encompasses the entire space with all agents in it, and there's also all the branch nodes of varying sizes in between that might be able to accomodate agents of appropriate sizes. So basically trees can store agents in branch nodes, as well as in leaf nodes. Then neighbor searching should not just consider leaf nodes but also check out all branch nodes along the way to finding neighboring leaf nodes.

Currently I have only two tree structures implemented, a k-d tree (`CpuTree`) and an AABB tree (`CpuAabbTree`), and regarding storing non-point agents in their branches they differ in ther effectiveness. A k-d tree always splits a parent partition in half along the chosen axis, but that means that even small non-point agents can get intersected by that splitting plane, and just because of their position have to be stored in a much larger branch node partition. On the other hand AABB trees get built bottom up, its nodes always adapting ot the shape and relative positions of agents, and this keeps agents stored in appropriately sized tree node partitions, which then reflects on the run-times.

I didn't even try to use grids for non-point agents, but if the trick is in the partitions hierarchy (as trees show) then I guess one reasonable way to do it would be to have a hierarchy of grids, each partitioning the same space, but with different sized cells. And then those grids can interact easily.

## Tests

- model description
- which structures were used
    - simple
    - K-d tree
    - AABB tree
- results
