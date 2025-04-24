from flask import Flask, request, jsonify
from flask_cors import CORS
import networkx as nx
import matplotlib.pyplot as plt
import io
import base64
import logging
import re


app = Flask(__name__)
CORS(app)

def parse_tac_to_dag(tac_code):
    G = nx.DiGraph()
    node_labels = {}
    node_operations = {}
    node_id_map = {}  # Maps variable names to node IDs
    lhs_variables = []
    tac_lines = tac_code.strip().split('\n')
    
    # identify all LHS variables
    for line in tac_lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # Match both binary operations and assignments
        match = re.match(r"(\w+)\s*=\s*(\w+)\s*([+\-*/])\s*(\w+)|(\w+)\s*=\s*(\w+)", line)

        if not match:
            logger.warning(f"Could not parse line: {line}")
            continue

        # Extract LHS variable
        if match.group(5) is not None: 
            lhs = match.group(5)
        else:  
            lhs = match.group(1)
        
        if lhs not in lhs_variables:
            lhs_variables.append(lhs)

    # create all nodes and connections
    for line in tac_lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        match = re.match(r"(\w+)\s*=\s*(\w+)\s*([+\-*/])\s*(\w+)|(\w+)\s*=\s*(\w+)", line)
        
        if not match:
            continue
        
        if match.group(5) is not None: 
            lhs, rhs = match.group(5), match.group(6)
            op = "="
            
            # Create nodes if they don't exist
            for var, is_lhs in [(lhs, True), (rhs, False)]:
                if var not in node_id_map:
                    G.add_node(var, label=var, is_lhs=is_lhs)
                    node_labels[var] = var
                    node_id_map[var] = var
            
            # Store operation for LHS node
            node_operations[lhs] = op
            
            # Add edge from RHS to LHS
            G.add_edge(rhs, lhs)
            
        else:  
            lhs, op1, op, op2 = match.group(1), match.group(2), match.group(3), match.group(4)
            
            # Create nodes for all variables if they don't exist
            for var, is_lhs in [(lhs, True), (op1, False), (op2, False)]:
                if var not in node_id_map:
                    G.add_node(var, label=var, is_lhs=is_lhs)
                    node_labels[var] = var
                    node_id_map[var] = var
            
            node_operations[lhs] = op
            
            G.add_edge(op1, lhs)
            G.add_edge(op2, lhs)

    return G, node_labels, node_operations, lhs_variables, tac_lines

def dag_to_base64(G, node_labels, node_operations):
    try:
        pos = nx.nx_agraph.graphviz_layout(G, prog='dot')
    except Exception:
        try:
            pos = nx.kamada_kawai_layout(G)
        except Exception:
            pos = nx.spring_layout(G, seed=42)

    plt.figure(figsize=(12, 10))
    
    op_nodes = [n for n in G.nodes() if n in node_operations]
    var_nodes = [n for n in G.nodes() if n not in node_operations]
    
    nx.draw_networkx_nodes(G, pos, nodelist=op_nodes, node_color='skyblue', node_size=2000, alpha=0.8)
    nx.draw_networkx_nodes(G, pos, nodelist=var_nodes, node_color='lightgreen', node_size=2000, alpha=0.8)
    
    nx.draw_networkx_edges(G, pos, arrows=True, arrowsize=20, width=1.5, edge_color='black', alpha=0.7)
    
    custom_labels = {}
    for node in G.nodes():
        if node in node_operations:
            # For nodes with operations, display both the variable and the operation
            custom_labels[node] = f"{node}\n{node_operations[node]}"
        else:
            custom_labels[node] = node
    
    nx.draw_networkx_labels(G, pos, labels=custom_labels, font_size=12, font_weight='bold')

    plt.axis('off')
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    img_str = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close('all')
    return img_str

def extract_optimal_sequence(G, tac_lines, lhs_variables):
    lhs_vars = [line.split('=')[0].strip() for line in tac_lines if '=' in line]
    listed = set()
    order = []

    def list_node(n):
        if n in listed:
            return
        listed.add(n)
        for pred in G.predecessors(n):
            list_node(pred)

    # For each node in topological order
    for node in nx.topological_sort(G):
        # If it's an LHS variable and not already listed
        if node in lhs_variables and node not in listed:
            list_node(node)
            order.append(node)

    return order

@app.route('/generate-dag', methods=['POST'])
def generate_dag():
    data = request.json
    tac_code = data.get('expression')

    if not tac_code:
        return jsonify({'error': 'TAC not provided'}), 400

    try:
        G, node_labels, node_operations, lhs_variables, tac_lines = parse_tac_to_dag(tac_code)

        if G.number_of_nodes() == 0:
            return jsonify({'error': 'Empty DAG. Check TAC.'}), 400

        dag_img = dag_to_base64(G, node_labels, node_operations)
        
        # Use original optimal sequence extraction logic
        optimal_seq_nodes = extract_optimal_sequence(G, tac_lines, lhs_variables)
        
        optimal_sequence = optimal_seq_nodes
        
        # Get the LHS variables in optimal order
        lhs_optimal_sequence = [node for node in optimal_seq_nodes if node in lhs_variables]
        
        # Extract edges with labels
        edges = [[u, v] for u, v in G.edges()]

        response_data = {
            'dag_image': dag_img,
            'optimal_sequence': optimal_sequence,
            'lhs_optimal_sequence': lhs_optimal_sequence,
            'edges': edges
        }

        return jsonify(response_data)

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"DAG Generation Exception: {str(e)}")
        logger.error(error_trace)
        return jsonify({'error': f'Error generating DAG: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Service is running'}), 200

if __name__ == '__main__':
    app.run(debug=True)
