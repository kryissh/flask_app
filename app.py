from flask import Flask, request, jsonify
import os
from celery import Celery
import heapq
import requests

app = Flask(__name__)

# Configure Celery
app.config['CELERY_BROKER_URL'] = os.environ.get('REDIS_URL')
app.config['CELERY_RESULT_BACKEND'] = os.environ.get('REDIS_URL')

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

@app.route('/')
def index():
    return "Hello, welcome to the Flask app!"

@app.route('/make_booking', methods=['POST'])
def make_booking():
    data = request.json
    pickup_node = data.get('pickup_node')
    destination_node = data.get('destination_node')
    seats_required = data.get('seats_required')
    task = async_make_booking.apply_async(args=[pickup_node, destination_node, seats_required])
    return jsonify({"status": "success", "task_id": task.id}), 202

@app.route('/async_make_booking', methods=['POST'])
def async_make_booking_endpoint():
    data = request.json
    pickup_node = data.get('pickup_node')
    destination_node = data.get('destination_node')
    seats_required = data.get('seats_required')

    if not all([pickup_node, destination_node, seats_required]):
        return jsonify({"error": "Missing required fields"}), 400

    task = async_make_booking.apply_async(args=[pickup_node, destination_node, seats_required])
    return jsonify({"status": "success", "task_id": task.id}), 202

@celery.task
def async_make_booking(pickup_node, destination_node, seats_required):
    # Simulate a long-running task
    import time
    time.sleep(10)
    return {"status": "success", "message": "Booking made!"}

@app.route('/task_status/<task_id>', methods=['GET'])
def task_status(task_id):
    task = async_make_booking.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {"state": task.state, "status": "Pending..."}
    elif task.state != 'FAILURE':
        response = {"state": task.state, "result": task.result}
    else:
        response = {"state": task.state, "status": str(task.info)}
    return jsonify(response)

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

class BookingSystem:
    def __init__(self, graph):
        self.vehicles = {
            "V1": Vehicle("V1"),
            "V2": Vehicle("V2")
        }
        self.graph = graph

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
                print(f"Booking successful! Vehicle {vehicle.vehicle_id} has been booked.")
                return vehicle.vehicle_id
            except ValueError as e:
                print(f"Booking failed: {str(e)}")
                return None
        else:
            print("No suitable vehicle found for the request.")
            return None

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
    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
