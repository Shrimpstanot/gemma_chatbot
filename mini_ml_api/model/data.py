def generate_synthetic_data(n=100):
    import random

    weather_map = {"clear": 0, "rainy": 1, "foggy": 2, "snowy": 3}
    road_type_map = {"highway": 0, "urban": 1, "residential": 2, "rural": 3}
    day_map = {"weekday": 0, "weekend": 1}

    weather_keys = list(weather_map.keys())
    road_keys = list(road_type_map.keys())
    day_keys = list(day_map.keys())

    data = []

    for _ in range(n):
        traffic_level = round(random.uniform(0.1, 0.95), 2)
        distance = round(random.uniform(1.0, 10.0), 2)
        weather = random.choice(weather_keys)
        road_type = random.choice(road_keys)
        day = random.choice(day_keys)

        # Conditional realistic speed
        if traffic_level > 0.7:
            speed = random.uniform(20, 40)
        elif traffic_level < 0.3:
            speed = random.uniform(60, 90)
        else:
            speed = random.uniform(40, 70)

        eff_speed = speed * (1 - traffic_level)
        time = distance / (eff_speed + 1e-3)

        data.append({
            "distance": distance,
            "traffic_level": traffic_level,
            "speed": speed,
            "weather": weather_map[weather],
            "road_type": road_type_map[road_type],
            "day_of_week": day_map[day],
            "time": time
        })

    return data