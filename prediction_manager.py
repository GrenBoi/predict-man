from statbotics_manager import Statbotics_Manager
from predction_api_manager import PredictionAPI_Manager


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
