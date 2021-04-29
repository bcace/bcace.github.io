# Cache-friendly space partitioning structures

Until recently agents in [Tay](https://github.com/bcace/tay) were in the same fixed location in memory during their entire lifetime and any sorting into space partitions was done through pointers. Each space partition was an object that had a pointer to a list of its agents, and this list got updated at the beginning of each simulation step.

Decision to make agents static in memory and just work with pointers was made because of three main reasons:

* Agents can easily be sorted into and moved around a space partitioning structure
* Keeping pointers to agents (from the structure or other agents) stable
* Easier implementation of adding/removing agents during simulation

The problem with that approach is that during the most expensive parts of the simulation, when agents interact, they interact with their neighbors which, while close in model space, are actually at random distances from each other in memory. Because of how data is [cached](https://en.wikipedia.org/wiki/Locality_of_reference) accessing data that's close in memory is much faster and the solution would be to relate position in space and position in memory as much as possible. In other words, as well as sorting agents in space partitioning structures for neighbor-finding we have to then move agents in memory to mirror their spatial position as much as possible for fast data access.

As for the above reasons for keeping agents' positions in memory fixed:

* Sorting agents into linked lists is not necessarily faster (although it intuitively seems like it should be), and as it turns out the cache effects outweigh the overhead of moving agents around in memory
* If we don't keep agents in lists the only remaining pointers to agents are from other agents (e.g. cloth simulation), and even then we can specify where in the agent structure pointers are and automatically fix addresses after the pointed agents get sorted (I already implemented something similar in [Coo](https://github.com/bcace/coo))
* Adding/removing agents to and from a linked list during simulation might seem easier but there's a lot of other considerations regarding when those agents actually enter/exit the simulation that make the whole thing less straightforward (more on that in a future post)

## Sorting agents

So basically when agents move around in space whe have to keep neighboring agents close in memory as well. In Tay CPU structures this is done in three phases: sorting agents into partitions, sorting partitions themselves, and then copying agents into correct locations. Note that we don't have to sort agents within partitions because during broad phase of neighbor-finding we only need to know neighboring partitions, and assume all agents in those partitions are neighbors.

*Sorting agents into partitions*: We first determine for each agent which partition it belongs to and its sequence number in that partition. Each partition keeps count of all its agents.

*Sorting partitions*: We iterate through partitions so that neighboring ones are close together (this depends on the structure) and based on previous partitions agent counts calculate the index of each partition's first agent.

*Copying agents*: Now we know how partitions are ordered and exactly where its agents should go. For each agent we get its partition (determined in the first step), from that partition get the index of its first agent (calculated in the second step) and add to it the agents sequence number for that partition (first step). This gives us the new agent position and we can use it to copy the agent from one buffer to another. After all agents are copied (and pointer addresses fixed) we simply swap the buffers so the rest of the code works as if nothing happened.

In tree structures (`CpuKdTree` and `CpuAabbTree`) partitions are sorted simply by traversing the trees depth-first, and the grid structure (`CpuGrid`) partitions are not currently sorted. The obvious way to sort grid partitions would be to use the equivalent of the depth-first tree traversal - a [Morton curve](https://en.wikipedia.org/wiki/Z-order_curve), but the current implementation of `CpuGrid` doesn't regulate its numbers of partitions along each side so that the curve doesn't get cut off. I believe a better option would be to implement a completely new grid structure specifically to order its partitions in this way.

## Results

For both point and non-point agents best times improved noticeably, first the point agents in the `CpuKdTree` structure:

![cached_plot_1](/cached_plot_1.png)

then the same in the `CpuGrid` structure:

![cached_plot_2](/cached_plot_2.png)

Non-point agents performance for the `CpuKdTree` improved a bit less:

![cached_nonpoint_plot_1](/cached_nonpoint_plot_1.png)

and the same for the `CpuAabbTree`:

![cached_nonpoint_plot_2](/cached_nonpoint_plot_2.png)

These plots show the improvement that can be gained by just allowing the machine to work as it's supposed to, but there's still a lot that can be done. 

Currently agent sorting is single-threaded and it's noticeable when monitoring the utilization of CPUs. All 16 threads run at around 70%, but when I add more work to the interaction code (the code that gets executed in parallel) utilization jumps up. For instance if I make the interaction code 10 times slower utilization jumps to above 85%. Still, I like to keep the interaction code as small as possible exactly because it highlights these kinds of inefficiencies. 
