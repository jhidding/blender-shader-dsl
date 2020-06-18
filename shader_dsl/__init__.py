# ~\~ language=Python filename=shader_dsl/__init__.py
# ~\~ begin <<docs/python_dsl.md|shader_dsl/__init__.py>>[0]
# ~\~ begin <<docs/python_dsl.md|imports>>[0]
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple, Any, Union
# ~\~ end
# ~\~ begin <<docs/python_dsl.md|graph>>[0]
@dataclass
class Graph:
    nodes: List[Node]
    links: List[Tuple[Output, Input]]

    @property
    def root(self):
        return self.nodes[0]

    # ~\~ begin <<docs/python_dsl.md|graph-getattr>>[0]
    def __getattr__(self, name):
        return Promise(self, Output(self.root, name))
    # ~\~ end
# ~\~ end
# ~\~ begin <<docs/python_dsl.md|graph>>[1]
@dataclass
class Node:
    name: str
    properties: Dict[str, Any]
    input_defaults: Dict[Union[int, str], Value]
# ~\~ end
# ~\~ begin <<docs/python_dsl.md|graph>>[2]
@dataclass
class Output:
    node: Node
    name: str
# ~\~ end
# ~\~ begin <<docs/python_dsl.md|graph>>[3]
@dataclass
class Input:
    node: Node
    name: Union[int, str]
# ~\~ end
# ~\~ begin <<docs/python_dsl.md|graph>>[4]
@dataclass
class Value:
    value: Any
# ~\~ end
# ~\~ begin <<docs/python_dsl.md|graph>>[5]
@dataclass
class Promise:
    graph: Graph
    output: Output
# ~\~ end

# ~\~ begin <<docs/python_dsl.md|decorator>>[0]
def decorator(f):
    """Creates a paramatric decorator from a function. The resulting decorator
    will optionally take keyword arguments."""
    @functools.wraps(f)
    def decoratored_function(*args, **kwargs):
        if args and len(args) == 1:
            return f(*args, **kwargs)

        if args:
            raise TypeError(
                "This decorator only accepts extra keyword arguments.")

        return lambda g: f(g, **kwargs)

    return decoratored_function
# ~\~ end
# ~\~ begin <<docs/python_dsl.md|node>>[0]
@decorator
def node(f, properties=["location"]):
    @functools.wraps(f)
    def g(*args, **kwargs):
        # ~\~ begin <<docs/python_dsl.md|node-body>>[0]
        name = f.__name__
        property_values = {}
        input_defaults = {}
        # ~\~ end
        # ~\~ begin <<docs/python_dsl.md|node-body>>[1]
        links = []
        nodes = [Node(name, property_values, input_defaults)]
        # ~\~ end
        # ~\~ begin <<docs/python_dsl.md|node-body>>[2]
        def merge_graph(g):
            for n in g.nodes:
                if n not in nodes:
                    nodes.append(n)
            for link in g.links:
                if link not in links:
                    links.append(link)
        # ~\~ end
        # ~\~ begin <<docs/python_dsl.md|node-body>>[3]
        for i, a in enumerate(args):
            if isinstance(a, Value):
                input_defaults[i] = a
            elif isinstance(a, Promise):
                merge_graph(a.graph)
                links.append((a.output, Input(nodes[0], i)))
        # ~\~ end
        # ~\~ begin <<docs/python_dsl.md|node-body>>[4]
        for k, v in kwargs.items():
            if k in properties:
                property_values[k] = v
            elif isinstance(v, Value):
                input_defaults[k] = v
            elif isinstance(v, Promise):
                merge_graph(v.graph)
                links.append((v.output, Input(nodes[0], k)))
        # ~\~ end
        # ~\~ begin <<docs/python_dsl.md|node-body>>[5]
        return Graph(nodes, links)
        # ~\~ end
    return g
# ~\~ end

# ~\~ begin <<docs/python_dsl.md|make-material>>[0]
def demangle(name: Union[int, str]) -> Union[int, str]:
    if isinstance(name, int):
        return name

    def cap(s):
        return s[0].upper() + s[1:]

    return ' '.join([cap(w) for w in name.split('_')])
# ~\~ end
# ~\~ begin <<docs/python_dsl.md|make-material>>[1]
def make_material(name: str, graph: Graph, **kwargs):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()

    nodemap = {}
    for n in graph.nodes:
        s = nodes.new(type=f"ShaderNode{n.name}")
        nodemap[id(n)] = s
        for k, v in n.properties.items():
            setattr(s, k, v)
        for q, v in n.input_defaults.items():
            key = demangle(q)
            s.inputs[key].default_value = v.value

    links = material.node_tree.links
    for (o, i) in graph.links:
        node_out = nodemap[id(o.node)]
        node_in = nodemap[id(i.node)]
        links.new(node_out.outputs[demangle(o.name)],
                  node_in.inputs[demangle(i.name)])

    for k, v in kwargs.items():
        setattr(material, k, v)

    return material
# ~\~ end
# ~\~ begin <<docs/python_dsl.md|shaders>>[0]
@node(properties=["location", "layer_name"])
def VertexColor(**kwargs):
    pass
# ~\~ end
# ~\~ begin <<docs/python_dsl.md|shaders>>[1]
@node(properties=["location"])
def BsdfPrincipled(**kwargs):
    pass


@node(properties=["location"])
def OutputMaterial(**kwargs):
    pass


@node(properties=["location"])
def MixShader(*args, **kwargs):
    pass


@node
def BsdfTransparent(**kwargs):
    pass


@node
def BsdfDiffuse(**kwargs):
    pass
# ~\~ end
# ~\~ end
