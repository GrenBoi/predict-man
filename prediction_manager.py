from statbotics_manager import Statbotics_Manager
from predction_api_manager import PredictionAPI_Manager

import json
import redis

r = redis.Redis(host="192.168.100.2", port=6380, decode_responses=True)

class PredictionManager:
    def __init__(self):
        self.Statbotics_Manager = Statbotics_Manager()
        self.PredictionAPI_Manager = PredictionAPI_Manager()

    def average_prediction(self, match_key):
        """

        Takes in match_key from TBA
        average_prediction Function gets a match prediction from all the rediction softwares under it and averages them out.
        The average uses a weighted system based on the accuracy of the prediction softwares in past matches

        """
        # prediction red wins
        predictions = []
        total = 0.0
        weight_total = 0.0
        predictions.append(self.Statbotics_Manager.fetch_prediction(match_key))
        predictions.append(self.PredictionAPI_Manager.fetch_prediction(match_key))
        # for every prediction multiply by its accuracy so weighted average
        for prediction in predictions:
            # prediction tuple format: (winnerPredict, red is winner probability, totalAccuracy)
            if prediction is not None:
                total += float(prediction[1]) * float(prediction[2])
                weight_total += float(prediction[2])
        if weight_total == 0.0:
            return None
        return total / weight_total
    def add_match_rank_to_database(match_ranks):
        match_key = match_ranks["match_key"]
        rank_dicts = match_ranks["rank_dicts"]
        json_string = json.dumps(rank_dicts)
        #{b:{1710:0},r:{1710:0}}
        if not r.hexists("match_ranks"):
            r.hset(
                "per_match_rankings",
                mapping={
                    match_key: json_string,
                },)
            return
        r.hset("per_match_rankings", match_key, json_string)
    def average_prediction_from_teams(self, team_list):
        """

        Takes in a list of teams [red-1,red-2,red-3,blue-1,blue-2,blue-3] and outputs a prediction

        """
        response = self.PredictionAPI_Manager.fetch_from_prediction_api(team_list)
        print(response)
        data = response.json()
        
        return self.PredictionAPI_Manager.get_prediction_from_json(data)