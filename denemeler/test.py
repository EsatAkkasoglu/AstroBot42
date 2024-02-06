import asyncio

# Gravitational acceleration values in m/s^2
GRAVITY = {
    "Mercury": 3.7,
    "Venus": 8.87,
    "Earth": 9.807,
    "Mars": 3.721,
    "Jupiter": 24.79,
    "Saturn": 10.44,
    "Uranus": 8.69,
    "Neptune": 11.15,
    "The Moon": 1.625,
    "Io": 1.796,
    "Europa": 1.314,
    "Ganymede": 1.428,
    "Callisto": 1.235,
    "Sun": 274,
    "White Dwarf": 9.807*6122,  # Approximate value, can vary significantly
    "Neutron Star": 9.807*1e11  # Approximate value, can vary significantly
}

async def calculate_weight_on_celestial_bodies(earth_weight, celestial_bodies):
    """
    Calculate the weight on different celestial bodies given the weight on Earth.
    
    :param earth_weight: Weight on Earth in kilograms
    :param celestial_bodies: List of celestial bodies to calculate weight on
    :return: A dictionary with celestial bodies as keys and weight as values
    """
    weight_on_bodies = {}
    for body in celestial_bodies:
        if body in GRAVITY:
            weight_on_bodies[body] = earth_weight * GRAVITY[body] / GRAVITY["Earth"]
        else:
            weight_on_bodies[body] = "Unknown celestial body"
    return weight_on_bodies

# Test command
async def test_command():
    earth_weight = 70  # 70 kg as an example
    bodies_to_test = ["Mars", "Earth", "Neptune", "The Moon", "White Dwarf", "Neutron Star"]
    weights = await calculate_weight_on_celestial_bodies(earth_weight, bodies_to_test)
    for body, weight in weights.items():
        print(f"Weight on {body}: {weight:.2f} kg" if isinstance(weight, float) else f"{body}: {weight}")

# Run the test command
asyncio.run(test_command())