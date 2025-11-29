# Server

This is basically the core of the tool. All analysis happens here. It receives messages from the user's shim processes and controls the UI. I.e., communication goes shim <-> server <-> UI.


Manually start, stop, restart server:

 - `aco-server start` 
 - `aco-server stop`
 - `aco-server restart`

Some basics: 

 - To check if the server process is still running: `ps aux | grep develop_server.py` or check which processes are holding the port: `lsof -i :5959`

 - When you make changes to `develop_server.py`, remember to restart the server to see them take effect.


## Editing and caching

### Goal

Overall, we want the following user experience:

 - We have our dataflow graph in the UI where each node is an LLM call. The user can click "edit input" and "edit output" and the develop epxeriment will rerun using cached LLM calls (so things are quick) but then apply the user edits.
 - If there are past runs, the user can see the graph and it's inputs and ouputs, but not re-run (we can leave the dialogs, and all UI the same, we just need to remember what the graph looked like and what input, output, colors and labels were).

We want to achieve this with the following functionality:

1. For any past run, we can display the graph and all the inputs, outputs, labels and colors like when it was executed. This must also work if VS Code is closed and restarted again.
2. LLM calls are cached so calls with the same prompt to the same model can be replayed.
3. The user can overwrite LLM inputs and ouputs.


### Database

We use a [SQLite](https://sqlite.org) database to cache LLM results and store user overwrites. See `db.py` for their schemas.

The `graph_topology` in the `experiments` table is a dict representation of the graph, that is used inside the develop server. I.e., the develop server can dump and reconstruct in-memory graph representations from that column.

When we run a workflow, new nodes with new `node_ids` are created (the graph may change based on an edited input). So instead of querying the cache based on `node_id`, we query based on `input_hash`.

`CacheManager` is responsible for look ups in the DB.

`EditManager` is responible for updating the DB.
