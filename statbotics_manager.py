import redis
import statbotics
import json

r = redis.Redis(host="192.168.100.2", port=6380, decode_responses=True)
sb = statbotics.Statbotics()


class Statbotics_Manager:
    def __init__(self):
        pass

    def get_EPA(self, team):
        """Get EPA of team"""
        try:
            data = sb.get_team(team)
            print(data["norm_epa"]["current"])
        except UserWarning:
            print("not found")

    def fetch_prediction(self, match_key):
        """
        Takes in match_key from TBA
        fetch_prediction Function is used for average predictions. Gets probability of red winning for a match and returns it in a tuple
        Tuple Format: (winnerPredict, red is winner probability, totalAccuracy), if match does not exist, return None

        """
        if r.hexists(match_key, "statbotics_red_team_winning_prob"):
            win_probability = r.hget(match_key, "statbotics_red_team_winning_prob")
            return (
                r.hget(match_key, "statbotics_predicted_winner"),
                win_probability,
                r.hget("statbotics_accuracy", "statbotics_total_accuracy"),
            )
        else:
            return None

    def calculate_match_prediction(self, match_data):
        """

        Takes in match_key from TBA
        calculate_match_prediction Function is used to put initial match prediction data into Redis.
        Is called from TBA by upcoming_match notification

        Example Format of Info at this time:
        Example Format of info:
        {
            'match_key': '2025wila_sf5m1',
            'statbotics_predicted_winner': 'blue',
            'statbotics_red_team_winning_prob': '0.4496',
            'prediction_api_predicted_winner': 'red',
            'prediction_api_predicted_winner_probability': '0.5671841',
        }

        """
        match_key = match_data["match_key"]
        if r.exists(match_key) is True:
            return
        probability_red_wins = float(
            sb.get_match(match_key, ["pred"])["pred"]["red_win_prob"]
        )
        predicted_winner = ""
        # get winning probability
        if probability_red_wins >= 0.5:
            predicted_winner = "red"
        else:
            predicted_winner = "blue"
        r.hset(
            match_key,
            mapping={
                "match_key": match_key,
                "statbotics_predicted_winner": predicted_winner,
                "statbotics_red_team_winning_prob": probability_red_wins,
            },
        )

    def update_accuracy(self, match_data):
        """

        Takes in Match Data from TBA
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
        match_key = match_data["match_key"]
        # if the acuracy was already checked, return early as accuracy should not be checked again
        if (
            r.hexists(match_key, "was_statbotics_correct")
            or not r.hexists(match_key, "match_key")
        ):
            return
        # find and update winner
        statbotics_match_data = sb.get_match(match_key)
        winner = statbotics_match_data["result"]["winner"]

        #If there is an error with TBA, some match scores will have a None value so we attempt to catch that here
        probability_red_wins = r.hget(match_key, "statbotics_red_team_winning_prob")
        if winner is None or probability_red_wins is None:
            return 
        r.hset(match_key, "actual_winner", winner)
        # update the match info to have is_statbotics correct section
        if (float(probability_red_wins) >= 0.5 and winner == "red") or (
            float(probability_red_wins) <= 0.5 and winner == "blue"
        ):
            was_statbotics_correct = "yes"
        else:
            was_statbotics_correct = "no"
        r.hset(match_key, "was_statbotics_correct", was_statbotics_correct)
        # update overall statbotics accuracy
        if r.hgetall("statbotics_accuracy") == {}:
            r.hset(
                "statbotics_accuracy",
                mapping={
                    "correct_predictions_count": 0,
                    "incorrect_predictions_count": 0,
                    "statbotics_total_accuracy": 0.0,
                },
            )
        database_correct_predictions = int(
            r.hget("statbotics_accuracy", "correct_predictions_count")
        )
        database_incorrect_predictions = int(
            r.hget("statbotics_accuracy", "incorrect_predictions_count")
        )
        if was_statbotics_correct == "yes":
            database_correct_predictions += 1
            r.hset(
                "statbotics_accuracy",
                "correct_predictions_count",
                database_correct_predictions,
            )
        else:
            database_incorrect_predictions += 1
            r.hset(
                "statbotics_accuracy",
                "incorrect_predictions_count",
                database_incorrect_predictions,
            )
        new_statbotics_total_accuracy = database_correct_predictions / (
            database_incorrect_predictions + database_correct_predictions
        )
        r.hset(
            "statbotics_accuracy",
            "statbotics_total_accuracy",
            new_statbotics_total_accuracy,
        )

        # add all data from statbotics for that match
        self.add_complete_data(match_key, statbotics_match_data)

    def add_complete_data(self, match_key, statbotics_match_data):
        match_key_score = match_key+":score"
        r.hset(match_key, "match_key_score", match_key_score)
        json_string = json.dumps(statbotics_match_data)
        r.set(match_key_score, json_string)