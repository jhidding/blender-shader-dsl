The goal is to get this code snippet to generate a Blender material for us:

``` {.python}
color_input = VertexColor(layer_name="color layer")
transparent = BsdfTransparent(color=Value((1,1,1,1)))
diffuse = BsdfDiffuse(color=color_input.color)
mix = MixShader(color_input.alpha, transparent.BSDF, diffuse.BSDF)
output_material = OutputMaterial(surface=mix.shader)
```

As we saw in the wishfull shader code, it is not that hard to come up with a language that could conceivably work. How do we fool Python to have these `VertexColor`, `BsdfTransparent`, ... functions to create a graph structure for us? It turns out, all we need are **functions** and **data**. We need to have our function calls self-translate into a graph data structure. We use `@dataclass` to create our structures, and use ample **type annotation** to document our code.

```python id="imports"
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple, Any, Union
```

The first import `from __future__` makes sure that we can use type annotations with forwardly defined types.

## Data structures
The graph show in Figure 1 is actually a **Directed Acyclic Graph** or DAG. The graph is *directed* because the links have a direction from input to output; it is *acyclic* because no output can serve as input for a node earlier in the chain. You could think of systems where such a link could be made to work: you would need to iterate over a loop until some criterion for convergence is met. Our application however, does not allow for this.

We define a `Graph` as a list of `Node`s and a list of connections going from an `Output` to an `Input`. The `root` of a graph is the node that only takes input. In a [topological sort](https://en.wikipedia.org/wiki/Topological_sorting) the `root` node is always on top. By construction this will always be the first element of the list of nodes. Later, we will show why we need to overload `__getattr__` on this class.

```python id="graph"
@dataclass
class Graph:
    nodes: List[Node]
    links: List[Tuple[Output, Input]]

    @property
    def root(self):
        return self.nodes[0]

    <<graph-getattr>>
```

Each `Node` has a name, properties and input_defaults. The properties are settings that cannot be controlled by input from another node. In some cases the names of inputs are not unique: see for instance the *Mix Shader*, it has two inputs called *Shader*. We have to identify those inputs by location, which is why the indices into `input_defaults` allow for both strings and integers.

```python id="graph"
@dataclass
class Node:
    name: str
    properties: Dict[str, Any]
    input_defaults: Dict[Union[int, str], Value]
```

An `Output` is a tuple of a `Node` and a string identifying the output element.

```python id="graph"
@dataclass
class Output:
    node: Node
    name: str
```

An `Input` is a tuple of a `Node` and a string or integer.

```python id="graph"
@dataclass
class Input:
    node: Node
    name: Union[int, str]
```

Our functions will take two kinds of arguments: `Value` and `Output`. To formalise this, value arguments should be wrapped in a `Value` container. This is not strictly necessary, but this way we can type-check the programmers intentions.

```python id="graph"
@dataclass
class Value:
    value: Any
```

Now that we have worked out the data structure, we can look at the programming interface. A `Graph` is representative of a computation, where the result is represented by the `root` node of the graph. We may ask for any output value on this root node: for this we overload the `__getattr__` method. Another choice could be to overload the `__getitem__` method. Take a look at the following expression:

``` {.python}
mix = MixShader(color_input.alpha, transparent.BSDF, diffuse.BSDF)
```

The *Mix Shader* takes three inputs here, all of which are given by attributes of previously defined graphs. Any of these attributes should result in a structure giving the parent graph, and the `Output` element that is refered to.

```python id="graph-getattr"
def __getattr__(self, name):
    return Promise(self, Output(self.root, name))
```

We collected these into a `Promise`, since the combination of a graph and an output give the *promise* of a value.

```python id="graph"
@dataclass
class Promise:
    graph: Graph
    output: Output
```

## Decorating functions
Now, all we need to do is to write functions that will build the graph structure. We will use function decorators to create the desired behaviour. You may have seen this syntax before:

``` {.python}
@decorate(extra_arguments=True)
def foo(bar):
    pass
```

In practice, what this does is the following:

``` {.python}
def foo(bar):
    pass

foo = decorate(extra_arguments=True)(foo)
```

You may have seen function decorators that can be used with or without extra arguments. If used without arguments,

``` {.python}
@decorate
def foo(bar):
    pass
```

is expanded to

``` {.python}
foo = decorate(foo)
```

The behaviour of the decorater changes when called with or without arguments! To create such a decorator it is convenient to use another decorator.

```python id="imports"
import functools
```

```python id="decorator"
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
```

Now we can define our `node` decorator.

```python id="node"
@decorator
def node(f, properties=["location"]):
    @functools.wraps(f)
    def g(*args, **kwargs):
        <<node-body>>
    return g
```

The `properties` argument takes names that should be treated as properties, as opposed to names that are inputs. Every node can be given a `location` argument to indicate the position it should take in the Blender GUI. For example, the `VertexColor` shader has a property called `layer_name`, which can be indicated as follows:

```python id="shaders"
@node(properties=["location", "layer_name"])
def VertexColor(**kwargs):
    pass
```

The following line shows how this is used.

``` {.python}
color_input = VertexColor(layer_name="color layer")
```

Given the arguments to a node-function `f`, we now need to build the graph that has the resulting node as a root element.

```python id="node-body"
name = f.__name__
property_values = {}
input_defaults = {}
```

The graph is built starting with an empty set of links and the single root node.

```python id="node-body"
links = []
nodes = [Node(name, property_values, input_defaults)]
```

Every time we encounter an argument that is an `Promise` from a different node, we need to merge the graph in that promise with the new graph. We would like to work with the Python builtin `set` type, however that type doesn't allow for hashing using Python object ids. One way to implement `set`-like behaviour is to use a `dict` with `id(value)` as keys. For the moment, we'll use a `list`.

```python id="node-body"
def merge_graph(g):
    for n in g.nodes:
        if n not in nodes:
            nodes.append(n)
    for link in g.links:
        if link not in links:
            links.append(link)
```

We loop over all positional arguments to the function, discriminating between `Value` arguments and `Promise` arguments.

```python id="node-body"
for i, a in enumerate(args):
    if isinstance(a, Value):
        input_defaults[i] = a
    elif isinstance(a, Promise):
        merge_graph(a.graph)
        links.append((a.output, Input(nodes[0], i)))
```

We do the same for the keyword arguments, with the distinction that we need to check for property arguments that need to be treated differently.

```python id="node-body"
for k, v in kwargs.items():
    if k in properties:
        property_values[k] = v
    elif isinstance(v, Value):
        input_defaults[k] = v
    elif isinstance(v, Promise):
        merge_graph(v.graph)
        links.append((v.output, Input(nodes[0], k)))
```

Once all that is done, we return the graph.

```python id="node-body"
return Graph(nodes, links)
```

We have now turned the function calls into a DAG. Upto now this has been a very generic exercise in developing an EDSL in Python. We still need to turn our `Graph` data structure into Blender API calls.

## Building the shader
We used object attributes to access output elements of nodes. In Blender these output elements have title cased names with spaces. We need to turn an attribute like `subsurface_color` into a name like `Subsurface Color`. For this we have a helper function called `demangle`.

```python id="make-material"
def demangle(name: Union[int, str]) -> Union[int, str]:
    if isinstance(name, int):
        return name

    def cap(s):
        return s[0].upper() + s[1:]

    return ' '.join([cap(w) for w in name.split('_')])
```

Since we already have a data structure where nodes and links are stored explicitely, we can just loop over all nodes and links and call the relevant Blender API functions. The name of the shaders are prefixed with `ShaderNode`.

```python id="imports"
import bpy
```

```python id="make-material"
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
```

## Shaders
The actual shader functions have no implementation since they are never evaluated. The reason why we still want to define them as functions is that they will become **qualified names**. Any odd variable name in Python, like `a = 42` is not qualified. We cannot later ask for the name of the variable. Functions and classes however are different. A second reason why defining the shaders as empty functions is a good idea, is that we can add documentation later on.

```python id="shaders"
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

@node
def Emission(**kwargs):
    pass
```

## Module

```python file="shader_dsl.py"
<<imports>>
<<graph>>

<<decorator>>
<<node>>

<<make-material>>
<<shaders>>
<<about>>
```
