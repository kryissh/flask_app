from flask import Flask, request, jsonify
import heapq
import threading
import requests

app = Flask(__name__)

class Graph:
    def __init__(self, adjacency_list):
        self.adjacency_list = adjacency_list

    def dijkstra(self, start):
        distances = {node: float('inf') for node in self.adjacency_list}
        distances[start] = 0
        priority_queue = [(0, start)]
        predecessors = {node: None for node in self.adjacency_list}

        while priority_queue:
            current_distance, current_node = heapq.heappop(priority_queue)

            if current_distance > distances[current_node]:
                continue

            for neighbor, weight in self.adjacency_list[current_node]:
                distance = current_distance + weight

                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    predecessors[neighbor] = current_node
                    heapq.heappush(priority_queue, (distance, neighbor))

        return distances, predecessors

    def find_shortest_path(self, start, end):
        distances, predecessors = self.dijkstra(start)
        path = []
        current_node = end

        while current_node:
            path.insert(0, current_node)
            current_node = predecessors[current_node]

        if path[0] == start:
            return path, distances[end]
        else:
            return [], float('inf')

    def insert_path(self, overall_path, insert_index, start, end):
        path, _ = self.find_shortest_path(start, end)
        for node in path:
            if node not in overall_path:
                overall_path.insert(insert_index, node)
                insert_index += 1

    def ensure_continuity(self, nodes):
        continuous_path = []
        for i in range(len(nodes) - 1):
            start, end = nodes[i], nodes[i + 1]
            if start in self.adjacency_list and end in self.adjacency_list:
                path, _ = self.find_shortest_path(start, end)
                if path:
                    if not continuous_path:
                        continuous_path.extend(path)
                    else:
                        continuous_path.extend(path[1:])
                else:
                    print(f"No path found between {start} and {end}")
            else:
                print(f"Invalid nodes: {start}, {end}")
        return continuous_path

    def add_node_to_path(self, overall_path, new_node, is_starting_node):
        node_alphabet = new_node[0]

        if is_starting_node:
            section_start = None
            section_end = None
            for i, node in enumerate(overall_path):
                if node[0] == node_alphabet:
                    if section_start is None:
                        section_start = i
                    section_end = i

            if section_start is not None and section_end is not None:
                self.insert_path(overall_path, section_end + 1, overall_path[section_end], new_node)
            else:
                nearest_alphabet = None
                nearest_index = -1
                for i, node in enumerate(overall_path):
                    if node[0] < node_alphabet:
                        nearest_alphabet = node[0]
                        nearest_index = i
                    elif node[0] > node_alphabet:
                        break

                if nearest_alphabet is not None:
                    self.insert_path(overall_path, nearest_index + 1, overall_path[nearest_index], new_node)
                else:
                    self.insert_path(overall_path, len(overall_path), overall_path[-1], new_node)
        else:
            section_start = None
            section_end = None
            for i in range(len(overall_path) - 1, -1, -1):
                if overall_path[i] == new_node:
                    section_start = i
                    break

            if section_start is not None:
                for i, node in enumerate(overall_path[section_start:], start=section_start):
                    if node[0] == node_alphabet:
                        section_end = i

                if section_end is not None:
                    self.insert_path(overall_path, section_end + 1, overall_path[section_end], new_node)
                else:
                    nearest_alphabet = None
                    nearest_index = -1
                    for i, node in enumerate(overall_path[section_start:], start=section_start):
                        if node[0] < node_alphabet:
                            nearest_alphabet = node[0]
                            nearest_index = i
                        elif node[0] > node_alphabet:
                            break

                    if nearest_alphabet is not None:
                        self.insert_path(overall_path, nearest_index + 1, overall_path[nearest_index], new_node)
                    else:
                        self.insert_path(overall_path, len(overall_path), overall_path[-1], new_node)

class Vehicle:
    def __init__(self, vehicle_id):
        self.vehicle_id = vehicle_id
        self.capacity = 10
        self.current_seats = 10
        self.queue = []
        self.traversal_path = []
        self.pickup_drop_info = {}

    def can_accommodate(self, seats_required):
        return self.current_seats >= seats_required

    def book_seats(self, seats_required):
        if self.can_accommodate(seats_required):
            self.current_seats -= seats_required
        else:
            raise ValueError("Vehicle cannot accommodate the requested seats!")

    def release_seats(self, seats_to_release):
        self.current_seats += seats_to_release
        if self.current_seats > self.capacity:
            self.current_seats = self.capacity

    def add_to_queue(self, new_path):
        for node in new_path:
            if node not in self.queue:
                self.queue.append(node)

    def add_to_traversal_path(self, new_path):
        for node in new_path:
            if node not in self.traversal_path:
                self.traversal_path.append(node)

    def update_pickup_drop_info(self, pickup_node, destination_node, seats_required):
        if pickup_node not in self.pickup_drop_info:
            self.pickup_drop_info[pickup_node] = 0
        if destination_node not in self.pickup_drop_info:
            self.pickup_drop_info[destination_node] = 0
        self.pickup_drop_info[pickup_node] += seats_required
        self.pickup_drop_info[destination_node] -= seats_required

class BookingSystem:
    def __init__(self, graph):
        self.vehicles = {
            "V1": Vehicle("V1"),
            "V2": Vehicle("V2")
        }
        self.graph = graph

    def select_vehicle(self, available_vehicles, pickup_node):
        best_vehicle = None
        min_distance = float('inf')

        for vehicle in available_vehicles:
            if vehicle.queue:
                first_node = vehicle.queue[0]
                _, distance = self.graph.find_shortest_path(first_node, pickup_node)
                if distance < min_distance:
                    best_vehicle = vehicle
                    min_distance = distance
            else:
                best_vehicle = vehicle
                break

        return best_vehicle

    def update_vehicle_queue(self, vehicle, pickup_node, destination_node, seats_required):
        new_path, _ = self.graph.find_shortest_path(pickup_node, destination_node)
        vehicle.add_to_queue(new_path)
        vehicle.add_to_traversal_path(new_path)
        vehicle.traversal_path = self.graph.ensure_continuity(vehicle.traversal_path)
        vehicle.update_pickup_drop_info(pickup_node, destination_node, seats_required)
        self.send_queue_to_rpi(vehicle)  # Send updated queue to Raspberry Pi

    def make_booking(self, pickup_node, destination_node, seats_required):
        available_vehicles = [
            v for v in self.vehicles.values() if v.can_accommodate(seats_required)
        ]

        if not available_vehicles:
            print("No vehicle available with the required number of seats.")
            return None

        vehicle = self.select_vehicle(available_vehicles, pickup_node)

        if vehicle:
            try:
                vehicle.book_seats(seats_required)
                self.update_vehicle_queue(vehicle, pickup_node, destination_node, seats_required)
                print(f"Booking successful! Vehicle {vehicle.vehicle_id} has been booked.")
                return vehicle.vehicle_id
            except ValueError as e:
                print(f"Booking failed: {str(e)}")
                return None
        else:
            print("No suitable vehicle found for the request.")
            return None

    def send_queue_to_rpi(self, vehicle):
        rpi_ip = "169.254.133.74"  # Raspberry Pi IP address
        url = f"http://{rpi_ip}:5000/update_queue"
        data = {
            "vehicle_id": vehicle.vehicle_id,
            "queue": vehicle.queue
        }
        try:
            response = requests.post(url, json=data)
            if response.status_code == 200:
                print(f"Queue for Vehicle {vehicle.vehicle_id} sent to Raspberry Pi successfully.")
            else:
                print(f"Failed to send queue to Raspberry Pi. Status code: {response.status_code}")
        except Exception as e:
            print(f"An error occurred while sending queue to Raspberry Pi: {e}")

    def display_queues(self):
        for vehicle_id, vehicle in self.vehicles.items():
            print(f"Updated Queue for Vehicle {vehicle_id}: {vehicle.queue}")
            print(f"Traversal Path for Vehicle {vehicle_id}: {vehicle.traversal_path}")
            print(f"Pickup/Drop Info for Vehicle {vehicle_id}: {vehicle.pickup_drop_info}")

    def update_queue_from_wifi(self, vehicle_id, node):
        if vehicle_id in self.vehicles:
            vehicle = self.vehicles[vehicle_id]
            if vehicle.queue and vehicle.queue[0] == node:
                vehicle.queue.pop(0)
                print(f"Node {node} removed from Vehicle {vehicle_id}'s queue.")
                self.send_queue_to_rpi(vehicle)  # Send updated queue to Raspberry Pi
            else:
                print(f"Node {node} is not the first node in Vehicle {vehicle_id}'s queue. No action taken.")
        else:
            print(f"Vehicle {vehicle_id} not found.")

def fetch_input_from_rpi():
    rpi_ip = "169.254.133.74"  # Raspberry Pi IP address
    url = f"http://{rpi_ip}:5000/get_input"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data['pickup_node'], data['destination_node'], data['seats_required']
        else:
            print(f"Failed to fetch input from Raspberry Pi. Status code: {response.status_code}")
            return None, None, None
    except Exception as e:
        print(f"An error occurred while fetching input from Raspberry Pi: {e}")
        return None, None, None

graph_data = {
    'A1': [('A2', 2)],
    'A2': [('A1', 2), ('A3', 2)],
    'A3': [('A2', 2), ('B3', 3)],
    'B1': [('B2', 2)],
    'B2': [('B1', 2), ('B3', 2)],
    'B3': [('B2', 2), ('A3', 3), ('C3', 3)],
    'C1': [('C2', 2)],
    'C2': [('C1', 2), ('C3', 2)],
    'C3': [('C2', 2), ('B3', 3)]
}

graph = Graph(graph_data)
booking_system = BookingSystem(graph)

@app.route('/receive_data', methods=['POST'])
def receive_data():
    data = request.json
    vehicle_id = data.get('vehicle_id')
    node = data.get('node')
    booking_system.update_queue_from_wifi(vehicle_id, node)
    return jsonify({"status": "success"}), 200

def run_flask_app():
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    threading.Thread(target=run_flask_app).start()

    while True:
        pickup_node, destination_node, seats_required = fetch_input_from_rpi()
        if pickup_node and destination_node and seats_required:
            vehicle_id = booking_system.make_booking(pickup_node, destination_node, seats_required)

            if vehicle_id:
                print(f"Booking completed for Vehicle {vehicle_id}.")
            booking_system.display_queues()
        else:
            print("Failed to get input from Raspberry Pi.")

        cont = input("Do you want to fetch another booking? (yes/no): ").strip().lower()
        if cont != 'yes':
            break