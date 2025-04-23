from flask import Flask, request, jsonify
from flask_cors import CORS
import base64
import io
import networkx as nx
import matplotlib.pyplot as plt

app = Flask(__name__)
CORS(app)

# Convert TAC to postfix
def tac_to_postfix(tac_lines):
    postfix = []
    for line in tac_lines:
        if '=' in line:
            lhs, rhs = line.split('=')
            lhs = lhs.strip()
            rhs = rhs.strip()
            tokens = rhs.split()
            postfix.extend(tokens)
            postfix.append(lhs)
    return postfix

# DAG generation with proper subexpression sharing
def build_dag(tac_lines):
    G = nx.DiGraph()
    expr_map = {}
    var_map = {}

    for line in tac_lines:
        if '=' not in line:
            continue

        lhs, rhs = line.split('=')
        lhs = lhs.strip()
        rhs = rhs.strip()
        tokens = rhs.split()

        if len(tokens) == 3:
            op1, operator, op2 = tokens

            op1_node = var_map.get(op1, op1)
            op2_node = var_map.get(op2, op2)
            key = (operator, op1_node, op2_node)

            if key in expr_map:
                node = expr_map[key]
            else:
                node = f"{operator}({op1_node},{op2_node})"
                G.add_node(node)
                G.add_edge(op1_node, node)
                G.add_edge(op2_node, node)
                expr_map[key] = node

            G.add_node(lhs)
            G.add_edge(node, lhs)
            var_map[lhs] = node

        elif len(tokens) == 1:
            src = tokens[0]
            src_node = var_map.get(src, src)
            G.add_node(lhs)
            G.add_edge(src_node, lhs)
            var_map[lhs] = src_node

    return G

# Draw DAG and return base64 string
def draw_dag(G):
    pos = nx.spring_layout(G, seed=42)
    plt.figure(figsize=(12, 7))
    nx.draw(G, pos, with_labels=True, node_color='lightblue', node_size=2000,
            font_size=10, font_weight='bold', arrowsize=20)
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    return img_base64

# Heuristic ordering as per algorithm
def heuristic_ordering(G):
    listed = set()
    sequence = []

    # Consider only non-leaf, non-input nodes (interior)
    unlisted_interior_nodes = [node for node in G.nodes()
                               if G.out_degree(node) > 0 and G.in_degree(node) > 0]

    while unlisted_interior_nodes:
        for n in unlisted_interior_nodes:
            if all(parent in listed for parent in G.predecessors(n)):
                break
        else:
            break  # No such node found (cyclic?)

        while True:
            sequence.append(n)
            listed.add(n)

            children = list(G.successors(n))
            child_found = False

            for m in children:
                if G.out_degree(m) == 0:
                    continue  # Skip leaves

                if all(parent in listed for parent in G.predecessors(m)):
                    n = m
                    child_found = True
                    break

            if not child_found:
                break

        unlisted_interior_nodes = [node for node in G.nodes()
                                   if G.out_degree(node) > 0 and G.in_degree(node) > 0 and node not in listed]

    return sequence

# LHS variable optimal sequence (basic topological filter)
def lhs_optimal_sequence(G, tac_lines):
    lhs_vars = [line.split('=')[0].strip() for line in tac_lines if '=' in line]
    topo_sorted = list(nx.topological_sort(G))
    return [node for node in topo_sorted if node in lhs_vars]

@app.route('/generate-dag', methods=['POST'])
def generate_dag():
    data = request.get_json()
    expression = data.get('expression', '')
    tac_lines = [line.strip() for line in expression.strip().split('\n') if line.strip()]

    postfix_expr = tac_to_postfix(tac_lines)
    G = build_dag(tac_lines)
    dag_img = draw_dag(G)

    heuristic_seq = heuristic_ordering(G)
    optimal_seq = list(reversed(heuristic_seq))

    response_data = {
        'dag_image': dag_img,
        'heuristic_sequence': heuristic_seq,
        'optimal_sequence': optimal_seq,
        'postfix': ' '.join(postfix_expr),
    }
    return jsonify(response_data)

if __name__ == '__main__':
    app.run(debug=True)
