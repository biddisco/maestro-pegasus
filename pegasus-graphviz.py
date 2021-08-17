#!/usr/bin/env python3

import colorsys
import os
import sys
import xml.sax
import xml.sax.handler
from collections import OrderedDict
from functools import cmp_to_key
from optparse import OptionParser

from Pegasus import yaml

COLORS = [
    "#1b9e77",
    "#d95f02",
    "#7570b3",
    "#e7298a",
    "#66a61e",
    "#e6ab02",
    "#a6761d",
    "#666666",
    "#8dd3c7",
    "#bebada",
    "#fb8072",
    "#80b1d3",
    "#fdb462",
    "#b3de69",
    "#fccde5",
    "#d9d9d9",
    "#bc80bd",
    "#ccebc5",
    "#ffed6f",
    "#ffffb3",
    "#aadd88",
    "#889933",
    "#22bbcc",
    "#d9dbb5",
]


def rgb2hex(r, g, b):
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


# Generate some colors to add to the list
s = 0.7
for l in [0.70, 0.55]:
    for h in range(0, 101, 10):
        if h == 40:
            continue
        rgb = colorsys.hls_to_rgb(h / 100.0, l, s)
        COLORS.append(rgb2hex(*rgb))


class DAG:
    def __init__(self):
        self.nodes = OrderedDict()


class Node:
    def __init__(self):
        self.id = None
        self.label = None
        self.level = 0
        self.parents = []
        self.children = []
        self.mark = 0
        self.closure = set()

    def renderNode(self, renderer):
        pass

    def renderEdge(self, renderer, parent):
        renderer.renderEdge(parent.id, self.id)

    def __repr__(self):
        return "({}, {})".format(self.id, self.label)


class Job(Node):
    def __init__(self):
        Node.__init__(self)
        self.xform = None

    def renderNode(self, renderer):
        if renderer.label_type == "xform":
            label = self.xform
        elif renderer.label_type == "id":
            label = "%s" % self.id
        elif renderer.label_type == "xform-id":
            label = "{}\\n{}".format(self.xform, self.id)
        elif renderer.label_type == "label-xform":
            if len(self.label) > 0:
                label = "{}\\n{}".format(self.label, self.xform)
            else:
                label = self.xform
        elif renderer.label_type == "label-id":
            if len(self.label) > 0:
                label = "{}\\n{}".format(self.label, self.id)
            else:
                label = self.id
        else:
            label = self.label
        color = renderer.getcolor(self.xform)
        renderer.renderNode(self.id, label, color)


class File(Node):
    def __init__(self):
        Node.__init__(self)
        self.cdo_dependency = False
        self.cdo_cached     = False

    def renderNode(self, renderer):
        if not self.cdo_dependency:
            renderer.renderNode(self.id, self.label, fillcolor="#ffed6f", shape="rect")
        else:
            renderer.renderNode(self.id, self.label, fillcolor="#ffffff", shape="diamond")
#         if self.cdo_cached:
#             renderer.renderNode(self.id, self.label, fillcolor="#000000", shape="circle")
        
def parse_yamlfile(fname, include_files):
    """
    Parse a DAG from a YAML workflow file.
    """
    with open(fname) as f:
        wf = yaml.load(f)

    dag = DAG()

    for job in wf["jobs"]:
        # parse job
        j = Job()

        # compute job
        if job["type"] == "job":
            j.xform = job["name"]
        # subworkflow job
        else:
            j.xform = job["file"]

        j.id = j.label = job["id"]
        dag.nodes[j.id] = j

        if job.get("nodeLabel"):
            j.label = job.get("nodeLabel")
        else:
            j.label = ""

        # parse uses (files)
        if include_files:                
            for use in job["uses"]:
                if use["lfn"] in dag.nodes:
                    f = dag.nodes[use["lfn"]]
                else:
                    f = File()
                    f.id = f.label = use["lfn"]
                    if 'metadata' in use:
                        if 'cdo_dependency' in use['metadata']:
                            f.cdo_dependency = True
                        if 'cdo_cache' in use['metadata']:
                            f.cdo_cached = True
                            #print('Inserting a diamond for',f)
                    dag.nodes[f.id] = f

                link_type = use["type"]

                if link_type == "input":
                    j.parents.append(f)
                    f.children.append(j)
                elif link_type == "output" or link_type == "checkpoint":
                    j.children.append(f)
                    f.parents.append(j)
                elif link_type == "inout":
                    print(
                        "WARNING: inout file {} of {} creates a cycle.".format(
                            f.id, j.id
                        )
                    )
                    f.children.append(j)
                    f.parents.append(j)
                    j.parents.append(f)
                    j.children.append(f)
                elif link_type == "none":
                    pass
                else:
                    raise Exception("Unrecognized link value: {}".format(link_type))

    for dep in wf["jobDependencies"]:
        for child in dep["children"]:
            dag.nodes[dep["id"]].children.append(dag.nodes[child])
            dag.nodes[child].parents.append(dag.nodes[dep["id"]])

    return dag


def remove_xforms(dag, xforms):
    """
    Remove transformations in the DAG by name
    """
    nodes = dag.nodes
    if len(xforms) == 0:
        return

    to_delete = []
    for _id in nodes.keys():
        node = nodes[_id]
        if isinstance(node, Job) and node.xform in xforms:
            print("Removing %s" % node.id)
            for p in node.parents:
                p.children.remove(node)
            for c in node.children:
                c.parents.remove(node)
            to_delete.append(_id)

    for _id in to_delete:
        del nodes[_id]


def transitivereduction(dag):
    # Perform a transitive reduction of the DAG to remove redundant edges.

    # First, perform a topological sort of the workflow.
    roots = [n for n in dag.nodes.values() if len(n.parents) == 0]

    L = []

    def visit(n):
        if n.mark == 1:
            raise Exception(
                "Workflow is not a DAG: Node %s is part of a "
                "cycle. Try without -f or with -s." % n
            )

        if n.mark == 0:
            n.mark = 1
            for m in n.children:
                visit(m)
            n.mark = 2
            L.insert(0, n)

    # Visit all the roots to create the topo sort
    for r in roots:
        visit(r)

    # Number all the levels of the workflow, which are used
    # to sort the children of each node in topological order.
    for n in L:
        n.level = 0
        for p in n.parents:
            n.level = max(n.level, p.level + 1)

    # The topological sort has to be reversed so that the deepest
    # nodes are visited first
    L.reverse()

    # This compares nodes by level for sorting. Note that sorting
    # children has to be done after the topo sort above because
    # the levels haven't been set until all the roots have been
    # visited.
    def lvlcmp(a, b):
        return a.level - b.level

    # This algorithm is due to Goralcikova and Koubek. It is fast and
    # simple, but it takes a lot of memory for large workflows because
    # it computes and stores the transitive closure of each node.
    for v in L:
        # This is to keep track of how many times v has been visited
        # from one of its parents. When this counter reaches the
        # number of parents the node has, then we can remove the closure
        v.mark = 0

        v.closure = {v}

        # We need to sort the children in topological order, otherwise the
        # reduction won't work properly. Sorting by level should produce
        # a valid topological ordering.
        v.children.sort(key=cmp_to_key(lvlcmp))

        # Compute the transitive closure and identify redundant edges
        reduced = []
        for w in v.children:

            w.mark += 1

            if w in v.closure:
                # If it is already in the closure, then it is not needed
                # sys.stderr.write("Removing {} -> {}\n".format(v.label, w.label))
                pass
            else:
                v.closure = v.closure.union(w.closure)
                reduced.append(w)

            # Once w has been visited by all its parents we can clear
            # its closure.
            if len(w.parents) == w.mark:
                w.closure = None

        # Another optimization. If v has no parents, then
        # we don't need to save its closure at all.
        if len(v.parents) == 0:
            v.closure = None

        # Now remove the edges
        v.children = reduced

    return dag


class emit_dot:
    """Write a DOT-formatted diagram.
    Options:
        label_type: What attribute to use for labels
        outfile: The file name to write the diagam out to.
        width: The width of the diagram
        height: The height of the diagram
    """

    def __init__(
        self, dag, label_type="label", outfile="/dev/stdout", width=None, height=None, leftright=False
    ):
        self.label_type = label_type

        self.next_color = 0  # Keep track of next color
        self.colors = {}  # Keep track of transformation names to assign colors

        self.out = open(outfile, "w")
        # Render the header
        self.out.write("digraph dag {\n")
        if width and height:
            self.out.write('    size="{:0.1f},{:0.1f}"\n'.format(width, height))
        self.out.write("    ratio=fill\n")
        if leftright:
            self.out.write('    rankdir="LR"\n')
        self.out.write('    node [style=filled,color="#444444",fillcolor="#ffed6f"]\n')
        self.out.write("    edge [arrowhead=normal,arrowsize=1.0]\n\n")

        # Ensure that dot rendered in a deterministic manner
        nodes = sorted(dag.nodes.values(), key=lambda n: n.id)

        # Render nodes
        for n in nodes:
            n.renderNode(self)

        # Render edges
        for p in nodes:
            for c in p.children:
                c.renderEdge(self, p)

        self.out.write("}\n")
        self.out.close()

    def getcolor(self, item):
        "Get the color for xform"
        if item not in self.colors:
            self.colors[item] = COLORS[self.next_color]
            # We use the modulus just in case we run out of colors
            self.next_color = (self.next_color + 1) % len(COLORS)
        return self.colors[item]

    def renderNode(self, id, label, fillcolor, color="#000000", shape="ellipse"):
        self.out.write(
            '    "%s" [shape=%s,color="%s",fillcolor="%s",label="%s"]\n'
            % (id, shape, color, fillcolor, label)
        )

    def renderEdge(self, parentid, childid, color="#000000"):
        self.out.write(
            '    "{}" -> "{}" [color="{}"]\n'.format(parentid, childid, color)
        )


def main():
    labeloptions = ["label", "xform", "id", "xform-id", "label-xform", "label-id"]
    labeloptionsstring = ", ".join("'%s'" % l for l in labeloptions)
    usage = "%prog [options] FILE"
    description = """Parses FILE and generates a DOT-formatted
graphical representation of the DAG. FILE can be a Condor
DAGMan file, Pegasus YAML file, or Pegasus DAX file."""
    parser = OptionParser(usage=usage, description=description)
    parser.add_option(
        "-s",
        "--nosimplify",
        action="store_false",
        dest="simplify",
        default=True,
        help="Do not simplify the graph by removing redundant edges. [default: False]",
    )
    parser.add_option(
        "-l",
        "--label",
        action="store",
        dest="label",
        default="label",
        help="What attribute to use for labels. One of %s. "
        "For 'label', the transformation is used for jobs that have no node-label. "
        "[default: label]" % labeloptionsstring,
    )
    parser.add_option(
        "-o",
        "--output",
        action="store",
        dest="outfile",
        metavar="FILE",
        default="/dev/stdout",
        help="Write output to FILE [default: stdout]",
    )
    parser.add_option(
        "-r",
        "--remove",
        action="append",
        dest="remove",
        metavar="XFORM",
        default=[],
        help="Remove jobs from the workflow by transformation name. For subworkflows, use the workflow file name.",
    )
    parser.add_option(
        "-W",
        "--width",
        action="store",
        dest="width",
        type="float",
        default=None,
        help="Width of the digraph",
    )
    parser.add_option(
        "-H",
        "--height",
        action="store",
        dest="height",
        type="float",
        default=None,
        help="Height of the digraph",
    )
    parser.add_option(
        "-f",
        "--files",
        action="store_true",
        dest="files",
        default=False,
        help="Include files. This option is only valid for YAML and DAX files. [default: false]",
    )

    (options, args) = parser.parse_args()

    if options.width and options.height:
        pass
    elif options.width or options.height:
        parser.error("Either both --width and --height or neither")

    if options.label not in labeloptions:
        parser.error("--label must be one of %s" % labeloptionsstring)

    if len(args) < 1:
        parser.error("Please specify FILE")

    if len(args) > 1:
        parser.error("Invalid argument")

    dagfile = args[0]
    if dagfile.lower().endswith(".yml"):
        dag = parse_yamlfile(dagfile, options.files)
    else:
        raise RuntimeError(
            "Unrecognizable file format. Acceptable formats are '.dag', '.dax', '.xml', '.yml'"
        )

    remove_xforms(dag, options.remove)

    if options.simplify:
        dag = transitivereduction(dag)

    emit_dot(dag, options.label, options.outfile, options.width, options.height)


if __name__ == "__main__":
    main()
