import redis
import statbotics
import requests

prediction_api_url = "https://match.api.apisb.me/prediction"
r = redis.Redis(host="192.168.100.2", port=6379, decode_responses=True)
sb = statbotics.Statbotics()


class PredictionAPI_Manager:
    def __init__(self):
        pass

    def fetch_prediction(self, match_key):
        """

        Takes in match_key from TBA
        fetch_prediction Function is used for average predictions. Gets probability of red winning for a match and returns it in a tuple
        Tuple Format: (winnerPredict, red is winner probability, totalAccuracy), if match does not exist, return None

        """

        if r.hexists(match_key, "prediction_api_predicted_winner"):
            win_probability = r.hget(
                match_key, "prediction_api_predicted_winner_probability"
            )
            if r.hget(match_key, "prediction_api_predicted_winner") == "blue":
                # changes red probability of win to blue for format
                win_probability = 1 - r.hget(
                    match_key, "prediction_api_predicted_winner_probability"
                )
            return (
                r.hget(match_key, "prediction_api_predicted_winner"),
                win_probability,
                r.hget("prediction_api_accuracy", "prediction_api_total_accuracy"),
            )
        else:
            return None

    def calculate_match_prediction(self, match_data):
        """

        Takes in Match Data from TBA
        calculate_match_prediction Function is used to put initial match prediction data into Redis.
        Is called from TBA by upcoming_match notification
        Calls predictionAPI to get a json file in this format:
        {
            blue_alliance_win_confidence :
            draw_confidence :
            red_alliance_win_confidence :
        }

        """
        teams = match_data["team_keys"]
        match_key = match_data["match_key"]
        payload = {
            "team-red-1": teams[0],
            "team-red-2": teams[1],
            "team-red-3": teams[2],
            "team-blue-1": teams[3],
            "team-blue-2": teams[4],
            "team-blue-3": teams[5],
        }
        response = requests.post(prediction_api_url, payload)
        self.input_match_prediction(response.json(), match_key)

    def input_match_prediction(self, return_json, match_key):
        """

        Takes in json from predictionApi and match_key from TBA
        input_match_prediction Function is used for adding the data from the predictionAPI to redis

        """

        prediction_json_data = self.get_prediction_from_json(
            return_json
        )  # api code to get prediction
        r.hset(match_key, "prediction_api_predicted_winner", prediction_json_data[0])
        r.hset(
            match_key,
            "prediction_api_predicted_winner_probability",
            prediction_json_data[1],
        )

    def update_accuracy(self, match_key):
        """

        Takes in match_key Data from TBA
        update_accuracy Function is used to put match predicion data into Redis and to update accuracy of Statbotics.
        Is called from TBA by match_score notification

        Example Format of info at this time(redis key = 2025wila_sf5m1):
        {
            'match_key': '2025wila_sf5m1',
            'statbotics_predicted_winner': 'blue',
            'statbotics_red_team_winning_prob': '0.4496',
            'prediction_api_predicted_winner': 'red',
            'prediction_api_predicted_winner_probability': '0.5671841',
            'actual_winner': 'red',
            'was_statbotics_correct': 'no',
            'was_prediction_api_correct': 'yes'
        }

        Accuracy Info Example(redis key = prediction_api_accuracy):
        {
         'correct_predictions_count': '8',
         'incorrect_predictions_count': '10',
         'prediction_api_total_accuracy': '0.4444444444444444'
        }

        """

        if (
            r.hget(match_key, "was_prediction_api_correct") is not None
            or r.hget(match_key, "match_key") is None
        ):
            return
        winner = sb.get_match(match_key, ["result"])["result"]["winner"]
        # update the match info to have is_statbotics correct section
        prediction_api_predicted_winner = r.hget(
            match_key, "prediction_api_predicted_winner"
        )
        if (prediction_api_predicted_winner == "red" and winner == "red") or (
            prediction_api_predicted_winner == "blue" and winner == "blue"
        ):
            was_prediction_api_correct = "yes"
        else:
            was_prediction_api_correct = "no"
        r.hset(match_key, "was_prediction_api_correct", was_prediction_api_correct)
        # update overall statbotics accuracy
        if r.hgetall("prediction_api_accuracy") == {}:
            r.hset(
                "prediction_api_accuracy",
                mapping={
                    "correct_predictions_count": 0,
                    "incorrect_predictions_count": 0,
                    "prediction_api_total_accuracy": 0.0,
                },
            )
        database_correct_predictions = int(
            r.hget("prediction_api_accuracy", "correct_predictions_count")
        )
        database_incorrect_predictions = int(
            r.hget("prediction_api_accuracy", "incorrect_predictions_count")
        )
        if was_prediction_api_correct == "yes":
            database_correct_predictions += 1
            r.hset(
                "prediction_api_accuracy",
                "correct_predictions_count",
                database_correct_predictions,
            )
        else:
            database_incorrect_predictions += 1
            r.hset(
                "prediction_api_accuracy",
                "incorrect_predictions_count",
                database_incorrect_predictions,
            )
        new_prediction_api_accuracy = database_correct_predictions / (
            database_incorrect_predictions + database_correct_predictions
        )
        r.hset(
            "prediction_api_accuracy",
            "prediction_api_total_accuracy",
            new_prediction_api_accuracy,
        )

    def get_prediction_from_json(self, input_prediction_json_data):
        """

        Takes in prediction json from predictionAPI
        Outputs who the prediction api thinks is going to win: "blue","red", or "draw"

        """

        if (
            input_prediction_json_data["red_alliance_win_confidence"]
            > input_prediction_json_data["blue_alliance_win_confidence"]
        ):
            if (
                input_prediction_json_data["draw_confidence"]
                > input_prediction_json_data["red_alliance_win_confidence"]
            ):
                return ("draw", input_prediction_json_data["draw_confidence"])
            else:
                return (
                    "red",
                    input_prediction_json_data["red_alliance_win_confidence"],
                )
        else:  # blue is more than red
            if (
                input_prediction_json_data["draw_confidence"]
                > input_prediction_json_data["blue_alliance_win_confidence"]
            ):
                return ("draw", input_prediction_json_data["draw_confidence"])
            else:
                return (
                    "blue",
                    input_prediction_json_data["blue_alliance_win_confidence"],
                )
