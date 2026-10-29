"""Weighted shortest-path routing over a small demo road graph. Replace with OSMnx graph for real maps."""
import networkx as nx

# zone id -> road-graph node
ZONE_NODE = {1: "Riverside", 2: "OldTown", 3: "Hillcrest", 4: "Industrial",
             5: "Lakeside", 6: "Airport", 7: "TechPark", 8: "Market"}

def build_graph(closed=()):
    G = nx.Graph()
    edges = [("Base", "Riverside", 18), ("Base", "OldTown", 25), ("Base", "Industrial", 30),
             ("OldTown", "Riverside", 10), ("OldTown", "Hillcrest", 20),
             ("Industrial", "Hillcrest", 15), ("Riverside", "Hillcrest", 28),
             ("Base", "Lakeside", 22), ("Base", "Market", 20), ("Market", "OldTown", 8),
             ("Market", "Lakeside", 12), ("Lakeside", "TechPark", 14), ("Market", "TechPark", 15),
             ("TechPark", "Airport", 10), ("Industrial", "Airport", 12), ("Lakeside", "Airport", 20)]
    for a, b, w in edges:
        if (a, b) not in closed and (b, a) not in closed:
            G.add_edge(a, b, weight=w)
    return G

def safest_route(src, dst, closed=()):
    G = build_graph(closed)
    path = nx.dijkstra_path(G, src, dst, weight="weight")
    return {"path": path, "minutes": nx.dijkstra_path_length(G, src, dst, weight="weight")}
