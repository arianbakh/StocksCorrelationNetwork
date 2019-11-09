import networkx as nx
import os
import sys
import warnings

from bisect import bisect_left
from sklearn.metrics import adjusted_mutual_info_score


warnings.filterwarnings("ignore", category=FutureWarning)  # suppress sklearn warnings


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
GRAPH_PATH = os.path.join(DATA_DIR, 'graph.gml')
MAX_NUMBER_OF_NODES = 100  # based on calculation limits
MAX_NUMBER_OF_BINS = 100  # based on 2018 paper


def _get_overlap(graph, id1, id2):
    first_date = max(graph.nodes[id1]['date_values'][0], graph.nodes[id2]['date_values'][0])
    last_date = min(graph.nodes[id1]['date_values'][-1], graph.nodes[id2]['date_values'][-1])
    if first_date < last_date:  # TODO minimum timedelta condition
        return first_date, last_date
    else:
        return None, None


def _get_correlation(graph, id1, id2):
    first_date, last_date = _get_overlap(graph, id1, id2)
    if not first_date or not last_date:
        return 0

    id1_start_index = bisect_left(graph.nodes[id1]['date_values'], first_date)
    id2_start_index = bisect_left(graph.nodes[id2]['date_values'], first_date)

    id1_values = []
    id2_values = []
    id1_index = id1_start_index
    id2_index = id2_start_index

    while id1_index < len(graph.nodes[id1]['date_values']) and \
            id2_index < len(graph.nodes[id2]['date_values']) and \
            graph.nodes[id1]['date_values'][id1_index] <= last_date and \
            graph.nodes[id2]['date_values'][id2_index] <= last_date:
        if graph.nodes[id1]['date_values'][id1_index] == graph.nodes[id2]['date_values'][id2_index]:
            id1_values.append(graph.nodes[id1]['opening_price_values'][id1_index])
            id2_values.append(graph.nodes[id2]['opening_price_values'][id2_index])
            id1_index += 1
            id2_index += 1
        elif graph.nodes[id1]['date_values'][id1_index] < graph.nodes[id2]['date_values'][id2_index]:
            id1_index += 1
        else:
            id2_index += 1

    return max(adjusted_mutual_info_score(id1_values[-MAX_NUMBER_OF_BINS:], id2_values[-MAX_NUMBER_OF_BINS:]), 0)


def _get_stock_info(stock_file_path):
    date_values = []
    opening_price_values = []
    with open(stock_file_path, 'r') as stock_file:
        lines = stock_file.readlines()
        for i, line in enumerate(lines):
            if i == 0:  # title line
                continue
            line_content = line.strip().split(',')
            line_date = line_content[0]
            opening_price = float(line_content[1])
            date_values.append(line_date)
            opening_price_values.append(opening_price)  # TODO what about other prices?
    return date_values, opening_price_values


def _create_graph():
    graph = nx.Graph()

    print('creating nodes...')
    for data_dir, stock_dir_names, _ in os.walk(DATA_DIR):
        for stock_dir_name in stock_dir_names:
            for stock_dir, _, stock_file_names in os.walk(os.path.join(DATA_DIR, stock_dir_name)):
                # TODO shuffle stock_file_names to make the selection more random
                selected_stock_file_names = stock_file_names[:MAX_NUMBER_OF_NODES]
                for i, stock_file_name in enumerate(selected_stock_file_names):
                    # progress bar
                    if (i + 1) % 100 == 0 or (i + 1) == len(selected_stock_file_names):
                        sys.stdout.write('\r[%d/%d]' % (i + 1, len(selected_stock_file_names)))
                        sys.stdout.flush()

                    date_values, opening_price_values = _get_stock_info(
                        os.path.join(stock_dir, stock_file_name)
                    )
                    if date_values:
                        graph.add_node(
                            stock_file_name,
                            date_values=date_values,
                            opening_price_values=opening_price_values
                        )
                print()  # newline

    print('creating edges...')
    max_counter = len(graph.nodes) ** 2
    for i, id1 in enumerate(graph.nodes()):
        for j, id2 in enumerate(graph.nodes()):
            # progress bar
            counter = (i + 1) * len(graph.nodes) + (j + 1)
            if counter % 100 == 0 or counter == max_counter:
                sys.stdout.write('\r[%d/%d]' % (counter, max_counter))
                sys.stdout.flush()

            if id1 < id2:  # to avoid redundancy
                correlation = _get_correlation(graph, id1, id2)
                graph.add_edge(id1, id2, weight=correlation)
    print()  # newline

    return graph


def _save_graph():
    pass  # TODO


def _load_or_create_graph():
    graph = _create_graph()
    return graph


def run():
    # TODO parallelize correlation calculation to speed things up
    graph = _load_or_create_graph()


if __name__ == '__main__':
    run()
